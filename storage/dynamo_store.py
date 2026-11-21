import json
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


def _table_name() -> str:
    return os.getenv("DYNAMODB_TABLE", "capp_process_plans")


def _region() -> str:
    return os.getenv("AWS_REGION", "us-east-1")


def _resource():
    return boto3.resource("dynamodb", region_name=_region())


def _table():
    return _resource().Table(_table_name())


def _to_epoch(value) -> int:
    """Coerce created_at (int, float, Decimal, numeric string or ISO-8601
    string) to int epoch seconds. Returns 0 if it cannot be parsed."""
    if isinstance(value, (int, float, Decimal)):
        return int(value)
    if isinstance(value, str):
        v = value.strip()
        try:
            return int(float(v))
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            return 0
    return 0


def _from_decimal(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, list):
        return [_from_decimal(v) for v in value]
    if isinstance(value, dict):
        return {k: _from_decimal(v) for k, v in value.items()}
    return value


def _to_decimal(item: dict) -> dict:
    return json.loads(json.dumps(item, default=str), parse_float=Decimal)


def create_table_if_missing():
    resource = _resource()
    name = _table_name()
    try:
        resource.meta.client.describe_table(TableName=name)
        print(f"Table already exists: {name}")
        return resource.Table(name)
    except ClientError as error:
        if error.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
    table = resource.create_table(
        TableName=name,
        KeySchema=[{"AttributeName": "plan_id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "plan_id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    print(f"Table created: {name}")
    return table


def save_plan(prompt: str, result: dict) -> str:
    features = []
    for feature in result.get("features_identified", []) or []:
        name = feature.get("feature_name", "") if isinstance(feature, dict) else str(feature)
        if name:
            features.append(name)

    plan = result.get("process_plan", []) or []
    operations_summary = " > ".join(
        f"{i}. {str(step.get('operation', '')).replace('_', ' ').title()}"
        for i, step in enumerate(plan, start=1)
    )
    retrieved_rules = [
        str(rule)[:300] for rule in (result.get("retrieved_rules_used") or [])[:10]
    ]

    plan_id = str(uuid.uuid4())
    item = {
        "plan_id": plan_id,
        "created_at": int(time.time()),
        "prompt": prompt,
        "model_id": os.getenv("BEDROCK_MODEL_ID") or "unknown",
        "part_type": str(result.get("part_type") or "unknown"),
        "material": str(result.get("material") or "unknown"),
        "tolerance": str(result.get("tolerance") or "unknown"),
        "surface_finish_Ra": result.get("surface_finish_Ra", 0) or 0,
        "key_dimensions": str(result.get("key_dimensions") or ""),
        "total_operations": int(result.get("total_operations", len(plan))),
        "features": features,
        "operations_summary": operations_summary,
        "process_plan_json": json.dumps(plan, default=str),
        "retrieved_rules": retrieved_rules,
        "planning_notes": str(result.get("planning_notes") or ""),
    }
    _table().put_item(Item=_to_decimal(item))
    return plan_id


def list_plans(limit: int = 200) -> list:
    table = _table()
    kwargs = {
        "ProjectionExpression": "#pid, #ca, #pr, #pt, #mt, #to",
        "ExpressionAttributeNames": {
            "#pid": "plan_id", "#ca": "created_at", "#pr": "prompt",
            "#pt": "part_type", "#mt": "material", "#to": "total_operations",
        },
    }
    items = []
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    items = [_from_decimal(item) for item in items]
    for item in items:
        item["created_at"] = _to_epoch(item.get("created_at"))   # normalise BEFORE sorting
    items.sort(key=lambda item: item["created_at"], reverse=True)
    return items[:limit]


def get_plan(plan_id: str):
    item = _table().get_item(Key={"plan_id": plan_id}).get("Item")
    if not item:
        return None
    item = _from_decimal(item)
    item["created_at"] = _to_epoch(item.get("created_at"))
    return item


def delete_plan(plan_id: str) -> None:
    _table().delete_item(Key={"plan_id": plan_id})


def rebuild_result(item: dict) -> dict:
    raw_plan = item.get("process_plan_json", "[]")
    try:
        process_plan = json.loads(raw_plan) if isinstance(raw_plan, str) else raw_plan
    except Exception:
        process_plan = []
    features = item.get("features", [])
    if features and isinstance(features[0], dict):
        features = [f.get("feature_name", "") for f in features]
    return {
        "part_description":     item.get("prompt", ""),
        "part_type":            item.get("part_type", "unknown"),
        "material":             item.get("material", "unknown"),
        "tolerance":            item.get("tolerance", "unknown"),
        "surface_finish_Ra":    item.get("surface_finish_Ra", ""),
        "key_dimensions":       item.get("key_dimensions", ""),
        "features_identified":  features,
        "retrieved_rules_used": item.get("retrieved_rules", []),
        "process_plan":         process_plan,
        "total_operations":     item.get("total_operations", len(process_plan)),
        "planning_notes":       item.get("planning_notes", ""),
    }
