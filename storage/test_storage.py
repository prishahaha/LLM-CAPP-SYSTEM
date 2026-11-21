from dotenv import load_dotenv

from storage.dynamo_store import (
    delete_plan,
    get_plan,
    rebuild_result,
    save_plan
)


def main():
    load_dotenv()
    result = {
        "part_type": "shaft",
        "material": "mild_steel",
        "tolerance": "H7",
        "surface_finish_Ra": 1.6,
        "features_identified": ["round_external_cylinder", "through_hole"],
        "retrieved_rules_used": [
            "Facing should precede turning operations."
        ],
        "key_dimensions": "80 mm diameter x 200 mm length",
        "total_operations": 3,
        "planning_notes": "Storage test plan",
        "process_plan": [
            {"step": 1, "operation": "facing", "machine": "lathe"},
            {"step": 2, "operation": "rough_turning", "machine": "lathe"},
            {"step": 3, "operation": "centre_drilling", "machine": "lathe"}
        ]
    }

    plan_id = save_plan("Dummy storage test part", result)
    try:
        saved = get_plan(plan_id)
        if saved is None:
            raise AssertionError(f"Saved plan {plan_id} could not be read")
        if not isinstance(saved.get("created_at"), int):
            raise AssertionError("created_at should be an integer epoch")
        rebuilt = rebuild_result(saved)
        if not isinstance(rebuilt.get("process_plan"), list):
            raise AssertionError("rebuild_result should return a process_plan list")
        print(saved["operations_summary"])
    finally:
        delete_plan(plan_id)

    print("Storage test passed")


if __name__ == "__main__":
    main()
