import os
import sys

from datahub.sdk.main_client import DataHubClient
from dotenv import load_dotenv


# Load variables from the private .env file.
load_dotenv()


def get_datahub_client() -> DataHubClient:
    """Create an authenticated connection to the local DataHub instance."""

    server = os.getenv(
        "DATAHUB_GMS_URL",
        "http://localhost:8080",
    ).strip()

    token = os.getenv("DATAHUB_GMS_TOKEN", "").strip()

    if not token:
        raise RuntimeError(
            "DATAHUB_GMS_TOKEN is missing. "
            "Add your DataHub personal access token to the .env file."
        )

    return DataHubClient(
        server=server,
        token=token,
    )


def test_connection() -> None:
    """Verify that DataPulse AI can connect to DataHub."""

    client = get_datahub_client()
    client.test_connection()

    print()
    print("==========================================")
    print("DataPulse AI -> DataHub Connection")
    print("==========================================")
    print("Status: SUCCESS")
    print("DataHub GMS: http://localhost:8080")
    print("Authentication: Working")
    print("==========================================")


if __name__ == "__main__":
    try:
        test_connection()
    except Exception as exc:
        print()
        print("==========================================")
        print("DataPulse AI -> DataHub Connection")
        print("==========================================")
        print("Status: FAILED")
        print(f"Error: {exc}")
        print("==========================================")
        sys.exit(1)