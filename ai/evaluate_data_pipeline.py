# evaluate_pipeline.py
import json
from datetime import datetime
from text_to_sql import generate_sql_mock, run_query, is_safe

benchmark_questions = [
    "Top 10 cities by GMV",
    "Which cuisine has the most orders?",
    "Average delivery time by city, worst first"
]

results = []
for q in benchmark_questions:
    sql = generate_sql_mock(q)
    safe = is_safe(sql)
    status = "SUCCESS" if safe else "BLOCKED"
    
    row_count = 0
    if safe:
        try:
            df = run_query(sql)
            row_count = len(df)
        except Exception as e:
            status = f"FAILED: {e}"

    results.append({
        "timestamp": datetime.utcnow().isoformat(),
        "question": q,
        "generated_sql": sql,
        "is_safe": safe,
        "status": status,
        "returned_rows": row_count
    })

with open("ai_pipeline_eval.json", "w") as f:
    json.dump(results, f, indent=2)