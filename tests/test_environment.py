from dotenv import load_dotenv
import os

load_dotenv()

def test_environment():
    # Check 1 — AWS credentials present
    assert os.getenv("AWS_ACCESS_KEY_ID"), "AWS_ACCESS_KEY_ID missing from .env"
    assert os.getenv("AWS_SECRET_ACCESS_KEY"), "AWS_SECRET_ACCESS_KEY missing from .env"
    print("✅ AWS credentials found in .env")

    # Check 2 — packages importable
    try:
        from langchain_aws import ChatBedrockConverse
        import boto3
        print("✅ langchain-aws and boto3 imported successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return

    # Check 3 — Bedrock connection works
    try:
        llm = ChatBedrockConverse(
            model_id=os.getenv("BEDROCK_MODEL_ID",
                               "meta.llama3-1-8b-instruct-v1:0"),
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        response = llm.invoke("Respond with exactly one word: OK")
        print(f"✅ Bedrock responded: {response.content.strip()}")
        print("✅ All systems ready")
    except Exception as e:
        print(f"❌ Bedrock connection failed: {e}")
        print("Check that your .env has correct keys and model access")
        print("is enabled in AWS Console → Bedrock → Model Access")

if __name__ == "__main__":
    test_environment()
