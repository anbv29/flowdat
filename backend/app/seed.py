import json
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import EvaluationCase

BENCHMARK_PATH = Path(__file__).parents[1] / "data" / "evaluation_cases.json"


def seed_evaluation_cases() -> int:
    cases = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    with SessionLocal() as db:
        existing = {item.name: item for item in db.scalars(select(EvaluationCase)).all()}
        for payload in cases:
            case = existing.get(payload["name"])
            if case:
                case.question = payload["question"]
                case.category = payload["category"]
                case.expected = payload["expected"]
                case.active = True
            else:
                db.add(EvaluationCase(**payload, active=True))
        db.commit()
    return len(cases)


def main() -> None:
    count = seed_evaluation_cases()
    print(f"Seeded {count} evaluation cases.")


if __name__ == "__main__":
    main()
