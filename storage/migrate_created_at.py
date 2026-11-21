from dotenv import load_dotenv
from storage.dynamo_store import _table, _to_epoch

load_dotenv()


def main():
    table = _table()
    migrated = skipped = 0
    kwargs = {}
    while True:
        response = table.scan(**kwargs)
        for item in response.get("Items", []):
            if isinstance(item.get("created_at"), str):
                item["created_at"] = _to_epoch(item["created_at"])
                table.put_item(Item=item)
                migrated += 1
            else:
                skipped += 1
        if not response.get("LastEvaluatedKey"):
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    print(f"Migrated {migrated} items, skipped {skipped} already numeric")

    bad = 0
    kwargs = {}
    while True:
        response = table.scan(**kwargs)
        for item in response.get("Items", []):
            value = item.get("created_at")
            print(f"  {item['plan_id'][:8]}  created_at={value}  type={type(value).__name__}")
            if isinstance(value, str):
                bad += 1
        if not response.get("LastEvaluatedKey"):
            break
        kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
    print("All created_at values are numeric" if bad == 0 else f"{bad} rows still strings")


if __name__ == "__main__":
    main()
