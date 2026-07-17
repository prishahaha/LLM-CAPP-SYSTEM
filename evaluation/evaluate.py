import json, os, time, sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv
from dataset.operation_rules import (
    FEATURE_TO_OPERATIONS,
    MACHINE_ASSIGNMENT,
    TOOL_ASSIGNMENT,
    DEFAULT_TOOL,
    SEQUENCING_PRIORITY
)
from agent.process_planning_agent import generate_process_plan

load_dotenv()
os.makedirs("results/figures", exist_ok=True)


def rule_based_capp(part: dict) -> dict:
    """
    Pure lookup — no LLM. Maps features directly to operations
    using operation_rules.py dictionaries.
    """
    features = [f["feature_name"] for f in part.get("features_list", [])]
    material = part.get("material", "mild_steel")
    tolerance = part.get("tolerance", "IT9")
    Ra = part.get("surface_finish_Ra", 3.2)

    operations = []

    # Always start with facing
    operations.append({
        "step": 1,
        "operation": "facing",
        "machine": MACHINE_ASSIGNMENT.get("facing", "CNC_Turning_Centre"),
        "tool": TOOL_ASSIGNMENT.get(("rough_turning", material), DEFAULT_TOOL)
    })

    # Map each feature to operations
    for feature in features:
        rule = FEATURE_TO_OPERATIONS.get(feature)
        if rule is None:
            continue

        if isinstance(rule, dict):
            ops = list(rule.get("base", rule.get("base_operations", [])))
            if tolerance in ["H7"] and "if_tolerance_H7" in rule:
                ops += rule["if_tolerance_H7"]
            if tolerance in ["h6"] and "if_tolerance_h6" in rule:
                ops += rule["if_tolerance_h6"]
            if Ra <= 1.6 and "if_Ra_lte_1_6" in rule:
                ops += rule["if_Ra_lte_1_6"]
        else:
            ops = list(rule)

        for op in ops:
            operations.append({
                "step": 0,
                "operation": op,
                "machine": MACHINE_ASSIGNMENT.get(op, "General_Machine"),
                "tool": TOOL_ASSIGNMENT.get((op, material), DEFAULT_TOOL)
            })

    # Always end with chamfering
    operations.append({
        "step": 0,
        "operation": "chamfering",
        "machine": MACHINE_ASSIGNMENT.get("chamfering", "VMC_Vertical_Machining_Centre"),
        "tool": DEFAULT_TOOL
    })

    # Remove duplicates keeping first occurrence
    seen_ops = []
    unique_operations = []
    for op in operations:
        if op["operation"] not in seen_ops:
            seen_ops.append(op["operation"])
            unique_operations.append(op)

    # Sort by sequencing priority
    def sort_key(op):
        return SEQUENCING_PRIORITY.get(op["operation"], 99)

    unique_operations.sort(key=sort_key)

    # Renumber steps
    for i, op in enumerate(unique_operations):
        op["step"] = i + 1

    return {
        "features_identified": features,
        "process_plan": unique_operations,
        "total_operations": len(unique_operations)
    }


def normalise_op(op: str) -> str:
    """Lowercase and remove underscores for fuzzy matching."""
    return op.lower().replace("_", " ").strip()

def calculate_metrics(ground_truth: dict,
                       predicted: dict) -> dict:
    """
    Calculate all 5 evaluation metrics for one part.
    ground_truth: entry from synthetic_parts.json
    predicted: output from rule_based_capp() or generate_process_plan()
    """

    # Ground truth values
    gt_features = [f["feature_name"] if isinstance(f, dict)
                   else f for f in ground_truth.get("features_list", [])]
    gt_ops = [normalise_op(s["operation"])
              for s in ground_truth.get("process_plan", [])]
    gt_machines = [s.get("machine", "").lower()
                   for s in ground_truth.get("process_plan", [])]

    # Predicted values
    pred_features = predicted.get("features_identified", [])
    if pred_features and isinstance(pred_features[0], dict):
        pred_features = [f.get("feature_name", "") for f in pred_features]
    pred_ops = [normalise_op(s["operation"])
                for s in predicted.get("process_plan", [])]
    pred_machines = [s.get("machine", "").lower()
                     for s in predicted.get("process_plan", [])]

    # METRIC 1 — Feature Recognition Rate
    if gt_features:
        matched_features = sum(
            1 for f in gt_features
            if any(normalise_op(f) in normalise_op(pf) or
                   normalise_op(pf) in normalise_op(f)
                   for pf in pred_features)
        )
        feature_recognition = matched_features / len(gt_features) * 100
    else:
        feature_recognition = 0.0

    # METRIC 2 — Operation Accuracy
    if gt_ops:
        matched_ops = sum(
            1 for op in gt_ops
            if any(op in pop or pop in op for pop in pred_ops)
        )
        operation_accuracy = matched_ops / len(gt_ops) * 100
    else:
        operation_accuracy = 0.0

    # METRIC 3 — Sequence Correctness (binary)
    sequence_correct = 1
    rough_ops = {"rough turning", "rough boring", "roughing"}
    finish_ops = {"finish turning", "finishing", "cylindrical grinding",
                  "internal grinding"}

    rough_indices = [i for i, op in enumerate(pred_ops)
                     if any(r in op for r in rough_ops)]
    finish_indices = [i for i, op in enumerate(pred_ops)
                      if any(f in op for f in finish_ops)]

    if rough_indices and finish_indices:
        if max(rough_indices) > min(finish_indices):
            sequence_correct = 0

    chamfer_ops = [i for i, op in enumerate(pred_ops)
                   if "chamfer" in op or "deburr" in op]
    if chamfer_ops and len(pred_ops) > 2:
        if min(chamfer_ops) < len(pred_ops) - 3:
            sequence_correct = 0

    # METRIC 4 — Operation Completeness
    if gt_ops:
        completeness = min(len(pred_ops) / len(gt_ops), 1.0) * 100
    else:
        completeness = 0.0

    # METRIC 5 — Machine Selection Accuracy
    if gt_machines and pred_machines:
        machine_keywords = {
            "turn": "turn", "lathe": "turn",
            "mill": "mill", "vmc": "mill", "machining centre": "mill",
            "grind": "grind", "drill": "drill", "tap": "tap"
        }
        def machine_type(m):
            for kw, mtype in machine_keywords.items():
                if kw in m:
                    return mtype
            return "other"

        gt_types = [machine_type(m) for m in gt_machines]
        pred_types = [machine_type(m) for m in pred_machines]
        matches = sum(1 for mt in gt_types
                      if mt in pred_types and mt != "other")
        machine_accuracy = matches / len(gt_types) * 100 if gt_types else 0.0
    else:
        machine_accuracy = 0.0

    return {
        "feature_recognition_rate": round(feature_recognition, 2),
        "operation_accuracy": round(operation_accuracy, 2),
        "sequence_correctness": sequence_correct,
        "operation_completeness": round(completeness, 2),
        "machine_selection_accuracy": round(machine_accuracy, 2)
    }


def run_evaluation(test_size: int = 20, full_run: bool = False):
    """
    Runs evaluation on test parts from synthetic_parts.json.
    Default: 20 parts for quick test.
    Set full_run=True for all 100 parts.
    """
    dataset_path = os.getenv("DATASET_PATH", "dataset/synthetic_parts.json")
    with open(dataset_path, "r") as f:
        dataset = json.load(f)

    # Use last entries as unseen test set (not used in few-shot)
    test_parts = dataset[500:] if full_run else dataset[580:]
    actual_size = min(test_size, len(test_parts))
    test_parts = test_parts[:actual_size]

    print(f"Running evaluation on {actual_size} test parts...")
    print(f"Rule-based CAPP vs LLM Agent (AWS Bedrock)\n")

    rule_results = []
    llm_results  = []
    failed_parts = 0

    for i, part in enumerate(test_parts):
        print(f"Part {i+1}/{actual_size}: {part['part_id']} "
              f"({part['part_type']}, {part['material']})")

        # Rule-based evaluation (always fast — no API call)
        rule_pred = rule_based_capp(part)
        rule_metrics = calculate_metrics(part, rule_pred)
        rule_metrics["part_id"] = part["part_id"]
        rule_metrics["part_type"] = part["part_type"]
        rule_results.append(rule_metrics)

        # LLM agent evaluation
        try:
            llm_pred = generate_process_plan(part["part_description"])
            llm_metrics = calculate_metrics(part, llm_pred)
            llm_metrics["part_id"] = part["part_id"]
            llm_metrics["part_type"] = part["part_type"]
            llm_results.append(llm_metrics)
            time.sleep(1)
        except Exception as e:
            print(f"  LLM failed for {part['part_id']}: {e}")
            failed_parts += 1
            llm_results.append({
                "part_id": part["part_id"],
                "part_type": part["part_type"],
                "feature_recognition_rate": 0,
                "operation_accuracy": 0,
                "sequence_correctness": 0,
                "operation_completeness": 0,
                "machine_selection_accuracy": 0
            })

    print(f"\nEvaluation complete. Failed LLM calls: {failed_parts}/{actual_size}")
    return rule_results, llm_results


def save_results(rule_results: list, llm_results: list):
    metrics = [
        "feature_recognition_rate",
        "operation_accuracy",
        "sequence_correctness",
        "operation_completeness",
        "machine_selection_accuracy"
    ]
    metric_labels = [
        "Feature Recognition",
        "Operation Accuracy",
        "Sequence Correctness",
        "Operation Completeness",
        "Machine Selection"
    ]

    # Calculate averages
    rule_avgs = {m: round(sum(r[m] for r in rule_results) /
                          len(rule_results), 2) for m in metrics}
    llm_avgs  = {m: round(sum(r[m] for r in llm_results)  /
                          len(llm_results),  2) for m in metrics}

    # Comparison table
    rows = []
    for m, label in zip(metrics, metric_labels):
        rule_val = rule_avgs[m]
        llm_val  = llm_avgs[m]
        improvement = round(llm_val - rule_val, 2)
        rows.append({
            "Metric": label,
            "Rule-Based CAPP": rule_val,
            "LLM Agent (Ours)": llm_val,
            "Improvement": improvement
        })

    df = pd.DataFrame(rows)
    df.to_csv("results/comparison_table.csv", index=False)

    # Print table
    print("\n" + "="*65)
    print("COMPARISON TABLE")
    print("="*65)
    print(f"{'Metric':<25} {'Rule-Based':>12} {'LLM Agent':>12} {'Diff':>8}")
    print("-"*65)
    for _, row in df.iterrows():
        print(f"{row['Metric']:<25} {row['Rule-Based CAPP']:>12} "
              f"{row['LLM Agent (Ours)']:>12} {row['Improvement']:>+8}")
    print("="*65)

    # Save full results JSON
    full_results = {
        "rule_based": rule_results,
        "llm_agent": llm_results,
        "summary": {
            "rule_based_averages": rule_avgs,
            "llm_agent_averages": llm_avgs,
            "total_parts_evaluated": len(rule_results),
            "model_used": os.getenv("BEDROCK_MODEL_ID")
        }
    }
    with open("results/evaluation_results.json", "w") as f:
        json.dump(full_results, f, indent=2)

    # CHART 1 — Grouped bar chart
    x = range(len(metrics))
    width = 0.35
    fig, ax = plt.subplots(figsize=(12, 6))
    bars1 = ax.bar([i - width/2 for i in x],
                   [rule_avgs[m] for m in metrics],
                   width, label="Rule-Based CAPP", color="#4C72B0")
    bars2 = ax.bar([i + width/2 for i in x],
                   [llm_avgs[m] for m in metrics],
                   width, label="LLM Agent (Ours)", color="#DD8452")
    ax.set_xlabel("Metric")
    ax.set_ylabel("Score (%)")
    ax.set_title("Rule-Based CAPP vs LLM Agent — Evaluation Results")
    ax.set_xticks(list(x))
    ax.set_xticklabels(metric_labels, rotation=15, ha="right")
    ax.set_ylim(0, 110)
    ax.legend()
    ax.bar_label(bars1, padding=2, fmt="%.1f")
    ax.bar_label(bars2, padding=2, fmt="%.1f")
    plt.tight_layout()
    plt.savefig("results/figures/bar_chart_comparison.png", dpi=150)
    plt.close()
    print("Saved: results/figures/bar_chart_comparison.png")

    # CHART 2 — Box plot of Operation Accuracy distribution
    rule_op_acc = [r["operation_accuracy"] for r in rule_results]
    llm_op_acc  = [r["operation_accuracy"] for r in llm_results]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.boxplot([rule_op_acc, llm_op_acc],
               tick_labels=["Rule-Based CAPP", "LLM Agent (Ours)"],
               patch_artist=True,
               boxprops=dict(facecolor="#4C72B0", alpha=0.7))
    ax.set_ylabel("Operation Accuracy (%)")
    ax.set_title("Operation Accuracy Distribution Across Test Parts")
    plt.tight_layout()
    plt.savefig("results/figures/accuracy_distribution.png", dpi=150)
    plt.close()
    print("Saved: results/figures/accuracy_distribution.png")

    # CHART 3 — Accuracy by part type heatmap
    part_types = list(set(r["part_type"] for r in rule_results))
    heatmap_data = []
    for pt in part_types:
        rule_pt = [r["operation_accuracy"] for r in rule_results
                   if r["part_type"] == pt]
        llm_pt  = [r["operation_accuracy"] for r in llm_results
                   if r["part_type"] == pt]
        heatmap_data.append({
            "Part Type": pt,
            "Rule-Based": round(sum(rule_pt)/len(rule_pt), 1) if rule_pt else 0,
            "LLM Agent":  round(sum(llm_pt) /len(llm_pt),  1) if llm_pt  else 0
        })
    hm_df = pd.DataFrame(heatmap_data).set_index("Part Type")
    fig, ax = plt.subplots(figsize=(8, max(4, len(part_types))))
    sns.heatmap(hm_df, annot=True, fmt=".1f", cmap="YlOrRd",
                ax=ax, vmin=0, vmax=100)
    ax.set_title("Operation Accuracy by Part Type (%)")
    plt.tight_layout()
    plt.savefig("results/figures/feature_recognition_heatmap.png", dpi=150)
    plt.close()
    print("Saved: results/figures/feature_recognition_heatmap.png")

    # Summary report
    best_metric = max(rows, key=lambda r: r["Improvement"])
    report = f"""
CAPP-BENCH EVALUATION SUMMARY
==============================
Total parts evaluated : {len(rule_results)}
LLM model used        : {os.getenv('BEDROCK_MODEL_ID')}
Dataset               : dataset/synthetic_parts.json (entries 580-599)

AVERAGE SCORES:
  Feature Recognition  : Rule={rule_avgs['feature_recognition_rate']}%  LLM={llm_avgs['feature_recognition_rate']}%
  Operation Accuracy   : Rule={rule_avgs['operation_accuracy']}%  LLM={llm_avgs['operation_accuracy']}%
  Sequence Correctness : Rule={rule_avgs['sequence_correctness']*100}%  LLM={llm_avgs['sequence_correctness']*100}%
  Completeness         : Rule={rule_avgs['operation_completeness']}%  LLM={llm_avgs['operation_completeness']}%
  Machine Selection    : Rule={rule_avgs['machine_selection_accuracy']}%  LLM={llm_avgs['machine_selection_accuracy']}%

BEST IMPROVEMENT: {best_metric['Metric']} (+{best_metric['Improvement']}%)

FILES SAVED:
  results/evaluation_results.json
  results/comparison_table.csv
  results/figures/bar_chart_comparison.png
  results/figures/accuracy_distribution.png
  results/figures/feature_recognition_heatmap.png
"""
    with open("results/summary_report.txt", "w") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    # Default: 20 parts quick test
    # Change to full_run=True for full 100-part evaluation
    full_run = "--full" in sys.argv
    test_size = 100 if full_run else 20

    rule_results, llm_results = run_evaluation(
        test_size=test_size,
        full_run=full_run
    )
    save_results(rule_results, llm_results)
