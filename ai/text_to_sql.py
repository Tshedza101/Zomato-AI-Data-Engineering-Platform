import os
import re
import json
import pandas as pd
import streamlit as st
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

MODEL = "mock-gpt-4o-mini"

FORBIDDEN_WORDS = ['drop', 'delete', 'truncate', 'alter', 'update', 'insert', 'create', 'replace', 'grant', 'revoke']

EXAMPLE_QUESTIONS = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Average delivery time by city, worst first",
    "Cancel rate by payment method"
]

SCHEMA = """
Tables available (Snowflake). Use bare table names, no database or schema prefix.
 
FACT_ORDERS(order_id, order_date, customer_id, restuarant_id, city, cuisine,
           payment_method, order_status, is_delivered, sales_amount, discount,
           delivery_fee, gst, customer_rating, delivery_time_min)
DIM_RESTUARANT(restuarant_id, restuarant_name, city, cuisine, rating, cost_for_two)
DIM_CUSTOMER(customer_id, customer_name, age, age_segment, gender, city)
MART_DAILY_CITY_REVENUE(order_date, city, orders, cancel_rate, gmv, aov)
MART_RESTUARANT_PERFORMANCE(restuarant_id, restuarant_name, city, cuisine,
                            orders, revenue, avg_customer_rating, cancel_rate)
MART_DELIVERY_SLA(city, order_hour, delivered_orders, p50_delivery_min, late_rate)

Note: gmv means delivered revenue. Prefer the MART_ tables when they fit the question.
"""

@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "ZOMATO_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "ZOMATO"),
        schema="MARTS",
        role=os.getenv("SNOWFLAKE_ROLE", "DBT_ROLE")
    )

def generate_sql_mock(question):
    """
    Mock Text-to-SQL rule generator mapping natural language questions 
    to valid SELECT statements against the MARTS schema.
    """
    q_lower = question.lower()

    if "city" in q_lower and ("gmv" in q_lower or "revenue" in q_lower):
        sql = """
        SELECT city, SUM(gmv) AS total_gmv 
        FROM MART_DAILY_CITY_REVENUE 
        GROUP BY city 
        ORDER BY total_gmv DESC 
        LIMIT 10
        """
    elif "cuisine" in q_lower and "order" in q_lower:
        sql = """
        SELECT cuisine, COUNT(order_id) AS total_orders 
        FROM FACT_ORDERS 
        GROUP BY cuisine 
        ORDER BY total_orders DESC 
        LIMIT 10
        """
    elif "delivery time" in q_lower or "worst" in q_lower:
        sql = """
        SELECT city, AVG(delivery_time_min) AS avg_delivery_time 
        FROM FACT_ORDERS 
        GROUP BY city 
        ORDER BY avg_delivery_time DESC 
        LIMIT 10
        """
    elif "cancel rate" in q_lower and "payment" in q_lower:
        sql = """
        SELECT payment_method, 
               AVG(CASE WHEN order_status = 'CANCELLED' THEN 1.0 ELSE 0.0 END) AS cancel_rate 
        FROM FACT_ORDERS 
        GROUP BY payment_method 
        ORDER BY cancel_rate DESC 
        LIMIT 10
        """
    elif "restuarant" in q_lower or "restaurant" in q_lower:
        sql = """
        SELECT restuarant_name, revenue 
        FROM MART_RESTUARANT_PERFORMANCE 
        ORDER BY revenue DESC 
        LIMIT 10
        """
    else:
        # Fallback default query for unmapped general questions
        sql = """
        SELECT city, SUM(orders) AS total_orders 
        FROM MART_DAILY_CITY_REVENUE
        GROUP BY city 
        ORDER BY total_orders DESC 
        LIMIT 10
        """

    # Cleanup extra formatting
    sql = sql.replace("ZOMATO.MARTS.", "").replace("ZOMATO.", "")
    return re.sub(r'\s+', ' ', sql).strip().rstrip(";")

def is_safe(sql):
    lowered = sql.lower()

    if not lowered.startswith("select") and not lowered.startswith("with"):
        return False

    for word in FORBIDDEN_WORDS:
        # Match whole forbidden words to prevent accidental triggers
        if re.search(r'\b' + re.escape(word) + r'\b', lowered):
            return False

    return True

def clean_sql_string(sql_input: str) -> str:
    """Strips UUID query IDs, raw prefixes, and common table typos before execution."""
    # Remove leading 36-char Snowflake Query ID UUIDs if concatenated into string
    cleaned = re.sub(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '', sql_input.strip())
    # Fix table name typo if present
    cleaned = cleaned.replace("MART_DAILY_CITY_REVENUNE", "MART_DAILY_CITY_REVENUE")
    return cleaned.strip()

def run_query(sql):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Sanitize input SQL before passing to execution cursor
    clean_sql = clean_sql_string(sql)
    
    return cursor.execute(clean_sql).fetch_pandas_all()

# --- STREAMLIT UI ---
st.title("Chat with your Zomato Data (Text-to-SQL Engine)")
st.caption(f"Ask in English | SQL Engine: {MODEL} | Database: Snowflake (MARTS schema)")

with st.sidebar:
    st.header("Example Questions")
    for q in EXAMPLE_QUESTIONS:
        st.markdown(f" - {q}")

question = st.text_input(
    "Enter your question here:", 
    placeholder="e.g. Top 10 cities by GMV"
)

if question:
    sql = generate_sql_mock(question)
    
    st.markdown("**Generated Snowflake SQL:**")
    st.code(sql, language="sql")

    if not is_safe(sql):
        st.error("The generated SQL contains non-SELECT operations and was blocked by safety guardrails.")
    else:
        try:
            df = run_query(sql)
            st.success(f"{len(df)} rows returned from Snowflake")
            st.dataframe(df, hide_index=True)

            # Auto-render charts for 2-column tabular metrics
            if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                st.bar_chart(df, x=df.columns[0], y=df.columns[1])

        except Exception as e:
            st.error(f"Error executing Snowflake query: {e}")