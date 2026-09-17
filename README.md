# Zomato AI Data & Analytics Platform 

An end-to-end batch data engineering and GenAI platform that transforms raw food delivery data into analytics-ready data marts and natural-language query engines using **Apache Airflow, Snowflake, dbt Core, and Streamlit**.

The platform ingests transactional food delivery datasets into Snowflake, transforms them through medallion layers (RAW/Bronze → STAGING/Silver → MARTS/Gold) using **dbt**, and orchestrates execution via an **Apache Airflow** DAG (`zomato_batch`). The system is augmented with an AI execution lane incorporating a read-only **Text-to-SQL engine** with execution guardrails and a local, offline-first **Retrieval-Augmented Generation (RAG)** search module over customer reviews.

---

## 🏗 Architecture & Data Flow

```text
[Local Transactional CSVs]
         │
         ▼
  Snowflake RAW (Bronze Layer)
  ├── RAW.USERS | RAW.RESTUARANTS | RAW.FOOD | RAW.MENU | RAW.ORDERS | RAW.ORDER_ITEMS | RAW.REVIEWS
         │
         ▼
  Apache Airflow (zomato_batch DAG)
  │
  ├── 1. reload_raw
  │      └── Triggers raw database stage reloads
  │
  ├── 2. dbt_build_core ➔ Snowflake STAGING (Silver Layer)
  │      ├── stg_users.sql | stg_restuarants.sql | stg_food.sql | stg_menu.sql
  │      └── stg_orders.sql | stg_order_item.sql | stg_reviews.sql
  │      │
  │      └──➔ Snowflake MARTS (Gold Core Star-Schema)
  │           ├── Dimensions: dim_customers | dim_restuarants | dim_food | dim_date
  │           └── Incremental Facts: fact_orders | fact_order_items
  │
  ├── 3. enrich_reviews ➔ Snowflake AI Schema
  │      └── Python sentiment analysis & vector embeddings generation
  │
  └── 4. dbt_build_ai ➔ Snowflake MARTS (Gold Analytics Marts)
         ├── mart_daily_city_revenue.sql
         ├── mart_delivery_sla.sql
         ├── mart_restuarant_performance.sql
         └── mart_review_insights.sql
         │
         ▼
  Streamlit Interactive Platform
  ├── Text-to-SQL Engine (Snowflake Queries via DBT_ROLE)
  └── Offline RAG Chat (Local Parquet Caching + Similarity Retrieval)



## 📁 Repository Structure

```text
.
├── ai/                             # GenAI & LLM Services
│   ├── .env                        # Environment credentials for AI services
│   ├── enrich_reviews.py           # LLM sentiment enrichment script
│   ├── evaluate_data_pipeline.py  # Pipeline & evaluation utilities
│   ├── rag_cache_audit.txt         # Embedding cache audit log
│   ├── rag_chat.py                 # RAG Streamlit app ("chat with reviews")
│   ├── review_embeddings.parquet   # Local vector cache for offline semantic search
│   ├── test_ai_components.py      # Unit/integration tests for AI modules
│   ├── test_execution_report.txt   # Test execution audit output
│   └── text_to_sql.py              # Text-to-SQL Streamlit app with safety guardrails
├── airflow/                        # Pipeline Orchestration
│   ├── dags/                       # Airflow DAG definitions (`zomato_batch.py`)
│   ├── logs/                       # Task execution logs
│   ├── .env                        # Airflow environment variables
│   ├── Dockerfile                  # Airflow container setup with dbt & dependencies
│   └── docker-compose.yaml         # Multi-container service definitions
├── docs/                           # Architecture diagrams & documentation assets
├── logs/                           # System and dbt run logs
│   └── dbt.log
├── snowflake/                      # Database Initialization & DDL
│   ├── 01_setup.sql                # Databases, schemas, warehouses, and DBT_ROLE
│   ├── 02_stage_and_formats.sql    # File formats & Snowflake staging objects
│   ├── 03_raw_tables.sql           # DDL for Bronze landing tables
│   └── 04_load_into.sql            # COPY INTO commands for data ingestion
└── zomato/                         # dbt Transformation Layer
    ├── macros/
    │   └── generate_schema_name.sql # Custom schema routing macro
    ├── models/
    │   ├── marts/                  # Gold Layer: Star Schema & Analytics Marts
    │   └── staging/                # Silver Layer: Staging views
    ├── .gitignore
    ├── dbt_project.yml             # dbt configurations
    └── profiles.yml                # Snowflake connection profiles


🛠 Tech Stack
Data Warehouse: Snowflake (ZOMATO database with RAW, STAGING, MARTS, AI schemas)

Data Transformation: dbt Core (dbt-snowflake)

Orchestration: Apache Airflow 3 (Dockerized DAG: zomato_batch)

AI & LLM Lane: OpenAI (gpt-4o-mini, embeddings), Streamlit, NumPy, Pandas

Governance & Security: Role-Based Access Control (DBT_ROLE), Read-Only AST Guardrails (is_safe())


Layer,Environment,Description
Source / Ingestion,Local Files,"Processed transactional CSV logs (orders, users, restaurants, food, menu, reviews)."
Bronze (Raw),Snowflake ZOMATO.RAW,Staged raw landing tables populated via automated ingestion routines.
Silver (Staging),Snowflake ZOMATO.STAGING,"dbt staging views (stg_users, stg_restuarants, stg_orders, etc.) — clean, type-cast, rename, and standardize source fields."
Gold (Marts),Snowflake ZOMATO.MARTS,"Dimensional models (dim_customers, dim_restuarants, dim_food, dim_date), incremental facts (fact_orders, fact_order_items), and business marts."
AI Analytics,Snowflake ZOMATO.AI,Sentiment-enriched review outputs and downstream AI marts (mart_review_insights).


🤖 AI Lane & Guardrails
1. Text-to-SQL Engine (text_to_sql.py)
Translates natural language questions into valid Snowflake SQL queries targeting MARTS tables.

Enforces strict read-only execution guardrails via is_safe() function, blocking destructive statements (DROP, DELETE, TRUNCATE, UPDATE, ALTER, INSERT).

Integrates a regex input sanitizer (clean_sql_string) to prevent ID leaks or syntax collisions before sending queries to Snowflake.

2. Local Offline RAG Engine (rag_chat.py)
Offline-first semantic vector retrieval across customer reviews using Pandas, NumPy similarity metrics, and local Parquet embedding caches (review_embeddings.parquet).

Operates without requiring cloud vector database infrastructure during development.

⚙️ Airflow DAG Orchestration (zomato_batch)
The production pipeline is governed by a linear dependency Airflow DAG:

reload_raw: Triggers raw database stage reloads (snowflake/04_load_into.sql).

dbt_build_core: Runs dbt staging and core relational models (stg_*, dim_*, fact_*).

enrich_reviews: Executes Python enrichment scripts (ai/enrich_reviews.py) for review processing.

dbt_build_ai: Builds final analytical data marts (mart_*).

