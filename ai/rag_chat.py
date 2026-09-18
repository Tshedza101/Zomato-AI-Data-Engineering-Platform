import os
import numpy as np
import pandas as pd
import streamlit as st
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "mock-text-embedding-3-small"
CHAT_MODEL = "mock-gpt-4o-mini"
NEW_REVIEWS = 500
TOP_K = 5
CACHE_FILE = "review_embeddings.parquet"
VECTOR_DIM = 1536  # Standard dimension size matching text-embedding-3-small

def read_reviews_from_snowflake():
    """Connect to Snowflake and fetch sample reviews for local vector caching."""
    conn = snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    query = f"""
        SELECT REVIEW_ID, CITY, RATING, COMMENT
        FROM ZOMATO.STAGING.STG_REVIEWS
        WHERE COMMENT IS NOT NULL
        LIMIT {NEW_REVIEWS}
    """
    df = conn.cursor().execute(query).fetch_pandas_all()
    conn.close()

    df.columns = [col.lower() for col in df.columns]
    return df

def mock_embed(texts):
    """Generate synthetic embedding vectors without using API credits."""
    np.random.seed(42)  # Fixed seed for consistent local testing
    return [np.random.rand(VECTOR_DIM).tolist() for _ in texts]

@st.cache_data()
def load_reviews():
    if os.path.exists(CACHE_FILE):
        return pd.read_parquet(CACHE_FILE)

    df = read_reviews_from_snowflake()
    df['embedding'] = mock_embed(df['comment'].tolist())
    df.to_parquet(CACHE_FILE)
    return df

def cosine_similarity(vec_a, vec_b):
    """Calculate standard vector similarity score."""
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))

def find_similar_reviews(question, df):
    """Retrieve top K similar reviews using vector cosine similarity."""
    question_vector = mock_embed([question])[0]

    scores = []
    for review_vector in df['embedding']:
        scores.append(cosine_similarity(question_vector, review_vector))

    df = df.copy()
    df['score'] = scores
    return df.nlargest(TOP_K, 'score')

def ask_llm_mock(question, top_reviews):
    """Generate a mock summary answer based on retrieved review contents."""
    sample_cities = top_reviews['city'].unique().tolist()
    city_str = ", ".join([str(c) for c in sample_cities[:3]])
    
    return (
        f"[MOCK RESPONSE] Based on vector analysis of key reviews from {city_str}, "
        f"customers frequently mention packaging stability and delivery timing issues. "
        f"Top review context sampled: '{top_reviews['comment'].iloc[0]}'"
    )

# --- STREAMLIT UI ---
st.title("Chat with your Zomato Reviews (RAG Pipeline)")
st.caption(f"Searching {NEW_REVIEWS} reviews | Engine: {CHAT_MODEL}")

review_df = load_reviews()

question = st.text_input(
    "Ask a question about your reviews:",
    placeholder="e.g. What are the most common complaints about delivery?"
)

if question:
    top_reviews = find_similar_reviews(question, review_df)
    answer = ask_llm_mock(question, top_reviews)

    st.markdown("**Answer:**")
    st.write(answer)

    with st.expander("Reviews used to build this answer"):
        st.dataframe(top_reviews[['city', 'rating', 'comment', 'score']], hide_index=True)