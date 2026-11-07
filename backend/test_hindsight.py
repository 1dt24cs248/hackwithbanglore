import os

from hindsight_client import Hindsight

from app.config import Settings

SYNTHETIC_MEMORY = (
    "Synthetic incident INC-TEST-001: "
    "Payment API returned HTTP 503 after deployment. "
    "Database connection usage reached 98 percent. "
    "The verified root cause was excessive worker concurrency "
    "exhausting the database connection pool. "
    "Reducing worker concurrency from 24 to 8 resolved the incident."
)


def main() -> None:
    settings = Settings.load()
    base_url, api_key = settings.require_hindsight()
    bank_id = settings.hindsight_bank_id
    client = Hindsight(base_url=base_url, api_key=api_key)

    try:
        if os.getenv("HINDSIGHT_SMOKE_TEST_RETAIN", "false").strip().lower() == "true":
            print("1. Retaining the synthetic smoke-test memory...")
            client.retain(
                bank_id=bank_id,
                content=SYNTHETIC_MEMORY,
                context="IncidentIQ synthetic integration test",
                tags=["incident", "synthetic-test"],
            )
            print("Retention request completed.")
        else:
            print("1. Retention skipped; set HINDSIGHT_SMOKE_TEST_RETAIN=true to write.")

        print("2. Testing memory recall...")
        client.recall(
            bank_id=bank_id,
            query=(
                "Previous payment API HTTP 503 incidents caused by "
                "database connection exhaustion after deployment"
            ),
            budget="low",
        )
        print("Recall request completed.")
        print("Hindsight integration test completed.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
