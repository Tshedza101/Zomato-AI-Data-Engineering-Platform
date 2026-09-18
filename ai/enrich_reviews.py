import os
import json
import random
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

MODEL = "mock-gpt-4o-mini"
SAMPLE_N = int(os.getenv("SAMPLE_N", 5))
TOPICS = ["food quality", "delivery", "pricing", "service", "packaging", "other"]

def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

def create_output_table(cursor):
    cursor.execute("CREATE SCHEMA IF NOT EXISTS ZOMATO.AI")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ZOMATO.AI.REVIEW_ENRICHED (
            REVIEW_ID STRING,
            SENTIMENT_LABEL STRING,
            SENTIMENT_SCORE FLOAT,
            TOPIC STRING,
            KEY_ISSUE STRING,
            MODEL STRING,
            ENRICHED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
        )
    """)

def get_reviews_to_enrich(cursor):
    cursor.execute(f"""
        SELECT REVIEW_ID, COMMENT
        FROM ZOMATO.RAW.REVIEWS
        WHERE REVIEW_ID NOT IN (SELECT REVIEW_ID FROM ZOMATO.AI.REVIEW_ENRICHED)
        LIMIT {SAMPLE_N}
    """)
    return cursor.fetchall()

def classify_review_mock(comment):
    """Rule-based mock classifier mimicking GPT output structure."""
    text_lower = comment.lower() if comment else ""

    # Sentiment logic
    if any(w in text_lower for w in ["great", "polite", "helpful", "good", "delicious"]):
        sentiment_label = "positive"
        sentiment_score = round(random.uniform(0.6, 0.95), 2)
    elif any(w in text_lower for w in ["expensive", "far too", "bad", "late", "cold"]):
        sentiment_label = "negative"
        sentiment_score = round(random.uniform(-0.95, -0.5), 2)
    else:
        sentiment_label = "neutral"
        sentiment_score = round(random.uniform(-0.1, 0.1), 2)

    # Topic selection
    if "packaging" in text_lower:
        topic = "packaging"
    elif any(w in text_lower for w in ["delivery", "delivered", "time"]):
        topic = "delivery"
    elif "expensive" in text_lower or "price" in text_lower:
        topic = "pricing"
    elif "polite" in text_lower or "service" in text_lower:
        topic = "service"
    else:
        topic = "other"

    # Key issue definition
    key_issue = None
    if sentiment_label == "negative":
        key_issue = comment[:30] if len(comment) <= 30 else comment[:27] + "..."

    return {
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "topic": topic,
        "key_issue": key_issue
    }

def save_results(cursor, results):
    """Insert all enriched rows into Snowflake."""
    if not results:
        return
    print(f"Saving {len(results)} enriched reviews to Snowflake...")
    cursor.executemany(
        """
        INSERT INTO ZOMATO.AI.REVIEW_ENRICHED
            (REVIEW_ID, SENTIMENT_LABEL, SENTIMENT_SCORE, TOPIC, KEY_ISSUE, MODEL)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        results,
    )

def main():
    conn = get_connection()
    cursor = conn.cursor()
    create_output_table(cursor)
    reviews = get_reviews_to_enrich(cursor)

    if len(reviews) == 0:
        print("No new reviews to enrich.")
        cursor.close()
        conn.close()
        return

    print(f"Enriching {len(reviews)} reviews via Mock Engine...")

    results = []
    for review_id, comment in reviews:
        print(f"Classifying review {review_id}: {comment}")
        try:
            labels = classify_review_mock(comment)
            print(f"Labels for review {review_id}: {labels}")
            results.append((
                review_id,
                labels["sentiment_label"],
                labels["sentiment_score"],
                labels["topic"],
                labels["key_issue"],
                MODEL
            ))
        except Exception as e:
            print(f"Error occurred while classifying review {review_id}: {e}")

    save_results(cursor, results)
    conn.commit()
    print(f"Saved {len(results)} enriched reviews to Snowflake.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()