import json
from agent.process_planning_agent import generate_process_plan

TEST_PARTS = [
    {
        "id": "TEST_001",
        "description": "Mild steel stepped shaft, 60mm max diameter, 180mm length, one M8 blind threaded hole, one rectangular keyway 16x6mm, h6 tolerance on main journals, Ra 1.6 surface finish"
    },
    {
        "id": "TEST_002",
        "description": "EN24 alloy steel flanged coupling, 120mm OD, 50mm bore diameter, H7 tolerance on bore, six M10 through bolt holes on 100mm PCD, Ra 3.2 on mating faces"
    },
    {
        "id": "TEST_003",
        "description": "Aluminium 6061 rectangular bracket, 150x100x25mm, four countersunk M6 holes, one central rectangular pocket 80x20x15mm deep, Ra 6.3 surface finish"
    }
]

if __name__ == "__main__":
    for part in TEST_PARTS:
        print(f"\n{'='*60}")
        print(f"Testing: {part['id']}")
        print(f"Part: {part['description'][:80]}...")
        print("="*60)
        try:
            result = generate_process_plan(part["description"])
            print(f"Part type:   {result['part_type']}")
            print(f"Material:    {result['material']}")
            print(f"Tolerance:   {result['tolerance']}")
            print(f"Features:    {result['features_identified']}")
            print(f"Operations:  {result['total_operations']}")
            print("\nProcess Plan:")
            for step in result["process_plan"]:
                print(f"  Step {step['step']:2d}: {step['operation']:<25} | {step['machine']}")
            print(f"\nNotes: {result['planning_notes']}")

            out_path = f"results/{part['id']}_plan.json"
            import os; os.makedirs("results", exist_ok=True)
            with open(out_path, "w") as f:
                json.dump(result, f, indent=2)
            print(f"Saved to {out_path}")

        except Exception as e:
            print(f"FAILED: {e}")
