import os

from dotenv import load_dotenv

from storage.dynamo_store import create_table_if_missing


def main():
    load_dotenv()
    try:
        create_table_if_missing()
    except Exception as error:
        if getattr(error, "response", {}).get("Error", {}).get("Code") == "AccessDeniedException":
            print(
                "Access denied. Attach the DynamoDB inline policy to the IAM user "
                "and try again."
            )
            raise
        raise

    table_name = os.getenv("DYNAMODB_TABLE", "capp_process_plans")
    region = os.getenv("AWS_REGION", "us-east-1")
    print(f"Table ready: {table_name} in {region}")


if __name__ == "__main__":
    main()
