import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi.testclient import TestClient
from main import app
from src.llm.client import get_llm_config

CASES_PATH = Path(__file__).resolve().parent / "cases.json"


def run_evaluation():
    config = get_llm_config()
    print("=" * 60)
    print("RUNNING LLM EVALUATION SUITE")
    print(f"Provider URL : {config['base_url']}")
    print(f"Model        : {config['model']}")
    print(f"Prompt Ver   : {config['prompt_version']}")
    print(f"Stub Mode    : {config['stub']}")
    print("=" * 60)

    with open(CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    client = TestClient(app)
    total = len(cases)
    matched_category = 0
    matched_urgency = 0
    results = []

    start_all = time.time()

    for idx, case in enumerate(cases, 1):
        case_id = case.get("id", idx)
        text = case["input"]
        exp_cat = case["expected_category"]
        exp_urg = case["expected_urgency"]
        desc = case.get("description", "")

        t0 = time.time()
        try:
            resp = client.post("/triage", json={"text": text})
            duration = time.time() - t0
            if resp.status_code == 200:
                data = resp.json()
                got_cat = data.get("category")
                got_urg = data.get("urgency")
                conf = data.get("confidence", 0.0)
                reason = data.get("reason", "")

                cat_ok = (got_cat == exp_cat)
                urg_ok = (got_urg == exp_urg)

                if cat_ok:
                    matched_category += 1
                if urg_ok:
                    matched_urgency += 1

                status_icon = "PASS" if (cat_ok and urg_ok) else ("PARTIAL" if cat_ok else "FAIL")
                print(f"[{status_icon}] Case #{case_id}: {desc}")
                print(f"       Expected: category={exp_cat}, urgency={exp_urg}")
                print(f"       Got     : category={got_cat}, urgency={got_urg}, conf={conf:.2f} ({duration:.2f}s)")
                print(f"       Reason  : {reason}\n")

                results.append({
                    "id": case_id,
                    "description": desc,
                    "status": status_icon,
                    "expected": {"category": exp_cat, "urgency": exp_urg},
                    "got": {"category": got_cat, "urgency": got_urg, "confidence": conf, "reason": reason},
                    "duration_seconds": round(duration, 3)
                })
            else:
                print(f"[ERROR] Case #{case_id} failed with HTTP {resp.status_code}: {resp.text}\n")
                results.append({
                    "id": case_id,
                    "status": "ERROR",
                    "http_status": resp.status_code,
                    "response": resp.text
                })
        except Exception as e:
            print(f"[EXCEPTION] Case #{case_id} raised exception: {e}\n")
            results.append({
                "id": case_id,
                "status": "EXCEPTION",
                "error": str(e)
            })

    total_time = time.time() - start_all
    cat_accuracy = (matched_category / total) * 100.0
    urg_accuracy = (matched_urgency / total) * 100.0

    print("=" * 60)
    print("EVALUATION SUMMARY")
    print(f"Total Test Cases   : {total}")
    print(f"Category Accuracy  : {matched_category}/{total} ({cat_accuracy:.1f}%)")
    print(f"Urgency Accuracy   : {matched_urgency}/{total} ({urg_accuracy:.1f}%)")
    print(f"Total Time Taken   : {total_time:.2f} seconds")
    print("=" * 60)

    return {
        "total": total,
        "matched_category": matched_category,
        "matched_urgency": matched_urgency,
        "category_accuracy": cat_accuracy,
        "urgency_accuracy": urg_accuracy,
        "total_time_seconds": total_time,
        "results": results
    }


if __name__ == "__main__":
    run_evaluation()
