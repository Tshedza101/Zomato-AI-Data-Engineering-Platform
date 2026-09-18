# test_ai_components.py
import pytest
from text_to_sql import is_safe, generate_sql_mock
from rag_chat import find_similar_reviews, load_reviews

def test_sql_guardrails():
    """Verify non-SELECT statements are blocked."""
    assert is_safe("SELECT * FROM MARTS.FACT_ORDERS") == True
    assert is_safe("DROP TABLE MARTS.FACT_ORDERS") == False
    assert is_safe("DELETE FROM MARTS.FACT_ORDERS WHERE 1=1") == False

def test_sql_generation():
    """Verify prompt maps to correct Snowflake query structure."""
    sql = generate_sql_mock("Top 10 cities by GMV")
    assert "SELECT" in sql.upper()
    assert "MART_DAILY_CITY_REVENUE" in sql.upper()

def test_rag_vector_retrieval():
    """Verify vector search returns non-empty Top-K dataframes."""
    df = load_reviews()
    results = find_similar_reviews("packaging quality", df)
    assert len(results) == 5
    assert "score" in results.columns