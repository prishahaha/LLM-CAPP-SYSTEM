"""
CAPP-Bench-600 dataset generator.

Builds a 600-part synthetic benchmark of machined-part process plans by
combining:
  - a published machining-feature vocabulary (FeatureNet, Zhang et al. 2018 +
    MFCAD++ supplementary classes) -- see feature_vocabulary.py
  - a part-type taxonomy (MechCAD-derived)               -- see part_vocabulary.py
  - a rule-based operation/machine/tool/parameter engine informed by the
    Machining Data Handbook and ISO 286-1                -- see operation_rules.py

Part dimensions, material, tolerance grade, feature selection, and instance
parameters (hole diameters, thread sizes, etc.) are sampled with a fixed
random seed for reproducibility. This is a synthetic benchmark: see the
provenance notes in operation_rules.py and part_vocabulary.py before citing
specific rule values in a publication.

Run: python dataset/generate_dataset.py
Outputs:
  dataset/capp_dataset.json      - the 600 generated part/process-plan records
  dataset/dataset_metadata.json  - dataset-level source/citation metadata
  dataset/validation_report.txt  - CHECK 1-5 validation output
"""

from __future__ import annotations

import json
import os
import random
from datetime import date

from feature_vocabulary import FEATURE_VOCABULARY, FEATURE_NAME_TO_ID, feature_source
from part_vocabulary import MECHCAD_PART_CLASSES
from operation_rules import (
    MATERIALS,
    STEEL_FAMILY,
    OPERATION_PRIORITY,
    OPERATION_DISPLAY_NAME,
    get_operations_for_feature,
    get_machine,
    get_tool,
    get_drilling_tool,
    get_cutting_params,
    ra_bucket,
    PART_FEATURE_COMPATIBILITY,
    ROTATIONAL_PART_TYPES,
)

RNG_SEED = 42
N_PARTS = 600
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

random.seed(RNG_SEED)

# ---------------------------------------------------------------------------
# STEP 1 support data
# ---------------------------------------------------------------------------
MATERIAL_DISPLAY = {
    "mild_steel": "Mild steel",
    "EN24_alloy_steel": "EN24 alloy steel",
    "cast_iron": "Cast iron",
    "aluminium_6061": "Aluminium 6061",
    "stainless_steel_316": "Stainless steel 316",
}

PART_TYPE_DISPLAY = {
    "shaft": "shaft",
    "flange": "flange",
    "bracket": "bracket",
    "coupling": "coupling",
    "gear": "gear blank",
    "bearing_housing": "bearing housing",
    "pulley": "pulley",
    "cover_plate": "cover plate",
    "bushing": "bushing",
    "connecting_rod": "connecting rod",
}

DIMENSION_RANGES = {
    "shaft": {"diameter_mm": (20, 150), "length_mm": (80, 500)},
    "flange": {"OD_mm": (80, 400), "thickness_mm": (15, 60), "bore_mm": (20, 150)},
    "bracket": {"length_mm": (80, 300), "width_mm": (50, 200), "height_mm": (30, 150)},
    "coupling": {"OD_mm": (40, 200), "length_mm": (60, 250), "bore_mm": (20, 100)},
    "gear": {"OD_mm": (50, 300), "face_width_mm": (20, 80), "bore_mm": (20, 80)},
    "bearing_housing": {"OD_mm": (60, 250), "bore_mm": (20, 120), "length_mm": (40, 150)},
    "pulley": {"OD_mm": (80, 500), "face_width_mm": (30, 100), "bore_mm": (20, 80)},
    "cover_plate": {"length_mm": (80, 400), "width_mm": (60, 300), "thickness_mm": (8, 30)},
    "bushing": {"OD_mm": (30, 150), "ID_mm": (20, 100), "length_mm": (20, 100)},
    "connecting_rod": {"length_mm": (100, 400), "big_end_bore_mm": (30, 80), "small_end_bore_mm": (15, 40)},
}

TOLERANCE_WEIGHTS = [("tight", 0.30), ("standard", 0.30), ("general", 0.40)]
THREAD_SIZES_MM = [6, 8, 10, 12, 14, 16, 18, 20, 24]

OPERATION_PURPOSE = {
    "facing_centering": "Establish datum face and centre holes for between-centres turning",
    "centre_drilling": "Create an accurate starting point for drilling",
    "drilling": "Remove bulk material to create the hole",
    "boring": "Enlarge and true the drilled hole to size",
    "reaming": "Achieve precision bore diameter and tolerance",
    "rough_turning": "Remove bulk stock from the outside diameter",
    "semi_finish_turning": "Reduce stock allowance ahead of finishing",
    "finish_turning": "Achieve final diameter and surface finish on the OD",
    "face_milling": "Machine a flat reference face",
    "end_milling_rough": "Rough out pocket material",
    "end_milling_finish": "Finish pocket walls and floor to size",
    "end_milling": "Machine the feature profile to size",
    "milling": "Machine the passage/feature to size",
    "slot_milling": "Cut the slot to width and depth in a single pass",
    "shoulder_milling": "Machine the stepped shoulder feature",
    "angle_milling": "Machine the angled/slanted step feature",
    "taper_turning": "Turn the tapered section",
    "tapping": "Cut the internal thread form",
    "thread_turning": "Cut the external thread form on the lathe",
    "thread_rolling": "Form the external thread by cold rolling",
    "internal_thread_milling": "Mill the large-diameter internal thread form",
    "grooving_turning": "Turn the O-ring / seal groove",
    "cylindrical_grinding": "Achieve final OD tolerance and surface finish by grinding",
    "internal_grinding": "Achieve final bore tolerance and surface finish by grinding",
    "chamfering_turning": "Break sharp edges on the lathe",
    "chamfering_milling": "Break sharp edges on the VMC",
}

OPERATION_SOURCE_CHAPTER = {
    "facing_centering": "Chapter 1 -- Process Planning Fundamentals",
    "rough_turning": "Chapter 3 -- Turning",
    "semi_finish_turning": "Chapter 3 -- Turning",
    "finish_turning": "Chapter 3 -- Turning",
    "taper_turning": "Chapter 3 -- Turning",
    "grooving_turning": "Chapter 3 -- Turning",
    "thread_turning": "Chapter 3 -- Turning",
    "thread_rolling": "Chapter 3 -- Turning",
    "chamfering_turning": "Chapter 3 -- Turning",
    "centre_drilling": "Chapter 5 -- Hole Making",
    "drilling": "Chapter 5 -- Hole Making",
    "boring": "Chapter 5 -- Hole Making",
    "reaming": "Chapter 5 -- Hole Making",
    "tapping": "Chapter 5 -- Hole Making",
    "internal_thread_milling": "Chapter 5 -- Hole Making",
    "face_milling": "Chapter 4 -- Milling",
    "end_milling_rough": "Chapter 4 -- Milling",
    "end_milling_finish": "Chapter 4 -- Milling",
    "end_milling": "Chapter 4 -- Milling",
    "milling": "Chapter 4 -- Milling",
    "slot_milling": "Chapter 4 -- Milling",
    "shoulder_milling": "Chapter 4 -- Milling",
    "angle_milling": "Chapter 4 -- Milling",
    "chamfering_milling": "Chapter 4 -- Milling",
    "cylindrical_grinding": "Chapter 5 -- Grinding",
    "internal_grinding": "Chapter 5 -- Grinding",
}

SEQUENCING_RULE_TEXT = {
    "facing_centering": "RULE 1 -- datum first",
    "rough": "RULE 2 -- rough operations before semi-finish/finish",
    "semi_finish": "RULE 3 -- semi-finish before finish",
    "finish": "RULE 3/7/8 -- finish after rough/semi-finish "
    "(threads after bore/OD finished, O-ring groove after finish turning)",
    "grinding": "RULE 9 -- grinding always last for that feature",
    "chamfer": "RULE 10 -- chamfering/deburring is the final operation",
}

HANDBOOK_CITATION = (
    "Machining Data Handbook, Metcut Research Associates, 3rd Ed., 1980. "
    "Available: archive.org/details/machiningdatahan0002unse"
)

DATASET_SOURCES = {
    "feature_vocabulary": "FeatureNet dataset, Zhang et al., Computer-Aided Design, Vol.101, "
    "2018. DOI:10.1016/j.cad.2018.01.001",
    "part_classification": "MechCAD dataset, 10-class mechanical part B-rep taxonomy",
    "operation_rules": HANDBOOK_CITATION,
    "tolerance_standard": "ISO 286-1: Geometrical product specifications -- Limits and fits",
    "sequencing_rules": "Machining Data Handbook, Chapter 1 -- Process Planning Fundamentals",
}


def sequencing_bucket(op_key: str) -> str:
    if op_key == "facing_centering":
        return "facing_centering"
    p = OPERATION_PRIORITY[op_key]
    if p <= 10:
        return "rough"
    if p <= 20:
        return "semi_finish"
    if p <= 30:
        return "finish"
    if p <= 40:
        return "grinding"
    return "chamfer"


# ---------------------------------------------------------------------------
# STEP 1 -- sample part parameters
# ---------------------------------------------------------------------------
def sample_dimensions(part_type: str) -> dict:
    ranges = DIMENSION_RANGES[part_type]
    return {name: round(random.uniform(lo, hi), 1) for name, (lo, hi) in ranges.items()}


def sample_tolerance() -> tuple[str, str]:
    """Returns (category, label). label is context-independent; the H7/h6
    vs H8/h8 distinction is resolved per-feature at operation-build time via
    tol_is_h7_H7 checks in operation_rules, so a single representative label
    is stored on the part record."""
    r = random.random()
    cum = 0.0
    for category, weight in TOLERANCE_WEIGHTS:
        cum += weight
        if r <= cum:
            return category
    return "general"


def tolerance_label(category: str, rotational: bool) -> str:
    if category == "tight":
        return "h6" if rotational else "H7"
    if category == "standard":
        return "h8" if rotational else "H8"
    return "IT9"


def sample_surface_finish(category: str) -> float:
    ranges = {"tight": (0.8, 1.6), "standard": (1.6, 3.2), "general": (3.2, 6.3)}
    lo, hi = ranges[category]
    return round(random.uniform(lo, hi), 2)


def key_dimension_text(part_type: str, dims: dict) -> str:
    if part_type == "shaft":
        return f"{dims['diameter_mm']}mm diameter, {dims['length_mm']}mm length"
    if part_type == "flange":
        return f"{dims['OD_mm']}mm OD, {dims['bore_mm']}mm bore"
    if part_type == "bracket":
        return f"{dims['length_mm']}x{dims['width_mm']}x{dims['height_mm']}mm envelope"
    if part_type == "coupling":
        return f"{dims['OD_mm']}mm OD, {dims['bore_mm']}mm bore"
    if part_type == "gear":
        return f"{dims['OD_mm']}mm OD, {dims['face_width_mm']}mm face width, {dims['bore_mm']}mm bore"
    if part_type == "bearing_housing":
        return f"{dims['OD_mm']}mm OD, {dims['bore_mm']}mm bore"
    if part_type == "pulley":
        return f"{dims['OD_mm']}mm OD, {dims['face_width_mm']}mm face width, {dims['bore_mm']}mm bore"
    if part_type == "cover_plate":
        return f"{dims['length_mm']}x{dims['width_mm']}x{dims['thickness_mm']}mm plate"
    if part_type == "bushing":
        return f"{dims['OD_mm']}mm OD, {dims['ID_mm']}mm ID, {dims['length_mm']}mm length"
    if part_type == "connecting_rod":
        return f"{dims['length_mm']}mm length, {dims['big_end_bore_mm']}mm big-end bore, {dims['small_end_bore_mm']}mm small-end bore"
    raise ValueError(part_type)


def relevant_bore_diameter(part_type: str, dims: dict) -> float:
    for key in ("bore_mm", "ID_mm", "big_end_bore_mm", "diameter_mm"):
        if key in dims:
            return dims[key]
    return 25.0


# ---------------------------------------------------------------------------
# STEP 2 -- feature selection
# ---------------------------------------------------------------------------
def select_features(part_type: str) -> list[str]:
    eligible = PART_FEATURE_COMPATIBILITY[part_type]
    selected = []
    if part_type in ROTATIONAL_PART_TYPES and "round_external_cylinder" in eligible:
        selected.append("round_external_cylinder")
    if "chamfer" in eligible:
        selected.append("chamfer")

    remaining = [f for f in eligible if f not in selected]
    n_extra = min(len(remaining), random.randint(2, 4))
    selected.extend(random.sample(remaining, n_extra))
    return selected


def make_feature_instance(feature_name: str, dims: dict, part_type: str) -> dict:
    """Sample instance-level parameters (diameter, thread size) for a feature."""
    inst = {"feature_name": feature_name, "feature_id": FEATURE_NAME_TO_ID[feature_name]}
    if feature_name in ("through_hole", "blind_hole"):
        bore_ref = relevant_bore_diameter(part_type, dims)
        inst["diameter_mm"] = round(random.uniform(5, max(6, min(bore_ref, 60))), 1)
        inst["count"] = random.choice([1, 1, 2, 4, 6])
    if feature_name in ("thread_external", "thread_internal"):
        inst["thread_size_mm"] = random.choice(THREAD_SIZES_MM)
        inst["count"] = random.choice([1, 1, 2, 4])
    if feature_name == "rectangular_blind_slot":
        inst["width_mm"] = random.choice([6, 8, 10, 12, 14, 16, 18])
        inst["depth_mm"] = round(inst["width_mm"] * 0.4, 1)
    return inst


# ---------------------------------------------------------------------------
# STEP 3 -- build process plan
# ---------------------------------------------------------------------------
def build_step_entry(op_key: str, material: str, *, diameter_mm=None, tolerance_label_val=None) -> dict:
    if op_key in ("drilling", "centre_drilling") and diameter_mm is not None and material in (
        "mild_steel", "EN24_alloy_steel", "cast_iron",
    ):
        tool = get_drilling_tool(material, diameter_mm)
    else:
        tool = get_tool(op_key, material, tolerance=tolerance_label_val)

    machine = get_machine(op_key, diameter_mm=diameter_mm)
    params = get_cutting_params(material, op_key)
    bucket = sequencing_bucket(op_key)

    return {
        "operation_key": op_key,
        "operation": OPERATION_DISPLAY_NAME[op_key],
        "machine": machine,
        "tool": tool,
        "cutting_params": params,
        "purpose": OPERATION_PURPOSE[op_key],
        "sequencing_rule_applied": SEQUENCING_RULE_TEXT[bucket],
        "operation_source": "Machining Data Handbook, Metcut Research Associates, 3rd Ed., 1980, "
        f"{OPERATION_SOURCE_CHAPTER.get(op_key, 'Chapter 3 -- Turning')}",
        "_priority": OPERATION_PRIORITY[op_key],
    }


def build_process_plan(features: list[dict], material: str, tolerance: str, ra: float, part_type: str) -> list[dict]:
    rotational = part_type in ROTATIONAL_PART_TYPES
    raw_steps = [build_step_entry("facing_centering", material)]
    other_steps = []

    for feat in features:
        name = feat["feature_name"]
        diameter_mm = feat.get("diameter_mm")
        thread_size_mm = feat.get("thread_size_mm")
        ops = get_operations_for_feature(
            name,
            diameter_mm=diameter_mm,
            tolerance=tolerance,
            ra=ra,
            is_threaded=False,
            thread_size_mm=thread_size_mm,
            rotational_part=rotational,
        )
        for op_key in ops:
            other_steps.append(
                build_step_entry(op_key, material, diameter_mm=diameter_mm, tolerance_label_val=tolerance)
            )

    other_steps.sort(key=lambda s: s["_priority"])
    plan = raw_steps + other_steps

    for i, step in enumerate(plan, start=1):
        step["step"] = i
        del step["_priority"]

    # reorder keys for readability
    ordered = []
    for step in plan:
        ordered.append(
            {
                "step": step["step"],
                "operation": step["operation"],
                "machine": step["machine"],
                "tool": step["tool"],
                "cutting_params": step["cutting_params"],
                "purpose": step["purpose"],
                "sequencing_rule_applied": step["sequencing_rule_applied"],
                "operation_source": step["operation_source"],
            }
        )
    return ordered


# ---------------------------------------------------------------------------
# STEP 4 -- natural language description
# ---------------------------------------------------------------------------
FEATURE_DESC_TEMPLATES = {
    "round_external_cylinder": lambda inst: "turned outside diameter",
    "through_hole": lambda inst: f"{inst.get('count',1)} through hole(s) Ø{inst.get('diameter_mm','?')}mm",
    "blind_hole": lambda inst: f"{inst.get('count',1)} blind hole(s) Ø{inst.get('diameter_mm','?')}mm",
    "rectangular_blind_slot": lambda inst: f"one rectangular keyway {inst.get('width_mm','?')}×{inst.get('depth_mm','?')}mm",
    "rectangular_through_slot": lambda inst: "one rectangular through slot",
    "O_ring_groove": lambda inst: "one O-ring sealing groove",
    "chamfer": lambda inst: "chamfered edges",
    "thread_external": lambda inst: f"{inst.get('count',1)} M{inst.get('thread_size_mm','?')} external thread(s)",
    "thread_internal": lambda inst: f"{inst.get('count',1)} M{inst.get('thread_size_mm','?')} tapped hole(s)",
    "taper": lambda inst: "one tapered section",
    "rectangular_through_step": lambda inst: "a stepped diameter change",
    "two_sided_through_step": lambda inst: "a two-sided through step",
    "slanted_through_step": lambda inst: "a slanted through step",
    "circular_through_slot": lambda inst: "a circular snap-ring groove",
    "rectangular_pocket": lambda inst: "one rectangular pocket",
    "circular_end_pocket": lambda inst: "one counterbored pocket",
    "rectangular_passage": lambda inst: "one rectangular through passage",
    "rectangular_blind_step": lambda inst: "a blind shoulder step",
}


def build_description(part_type: str, material: str, dims: dict, features: list[dict], tolerance: str, ra: float) -> str:
    mat = MATERIAL_DISPLAY[material]
    ptype = PART_TYPE_DISPLAY[part_type]
    dim_text = key_dimension_text(part_type, dims)
    feature_texts = []
    relevant_surface = "the primary bore" if part_type != "shaft" else "the bearing journal"
    for feat in features:
        name = feat["feature_name"]
        if name in ("round_external_cylinder", "chamfer"):
            continue
        tmpl = FEATURE_DESC_TEMPLATES.get(name)
        if tmpl:
            feature_texts.append(tmpl(feat))

    parts = [f"{mat} {ptype}, {dim_text}"]
    parts.extend(feature_texts)
    parts.append(f"{tolerance} tolerance on {relevant_surface}")
    parts.append(f"Ra {ra} surface finish")
    return ", ".join(parts) + "."


# ---------------------------------------------------------------------------
# STEP 5 -- build one dataset entry
# ---------------------------------------------------------------------------
def generate_part(idx: int) -> dict:
    part_type = random.choice(MECHCAD_PART_CLASSES)
    material = random.choice(MATERIALS)
    dims = sample_dimensions(part_type)

    tol_category = sample_tolerance()
    rotational = part_type in ROTATIONAL_PART_TYPES
    tolerance = tolerance_label(tol_category, rotational)
    ra = sample_surface_finish(tol_category)

    feature_names = select_features(part_type)
    features = [make_feature_instance(f, dims, part_type) for f in feature_names]

    process_plan = build_process_plan(features, material, tolerance, ra, part_type)
    description = build_description(part_type, material, dims, features, tolerance, ra)

    features_list = [
        {
            "feature_id": f["feature_id"],
            "feature_name": f["feature_name"],
            "source": feature_source(f["feature_name"]),
        }
        for f in features
    ]

    return {
        "part_id": f"PART_{idx:03d}",
        "part_type": part_type,
        "material": material,
        "dimensions": dims,
        "features_list": features_list,
        "tolerance": tolerance,
        "surface_finish_Ra": ra,
        "part_description": description,
        "process_plan": process_plan,
        "total_operations": len(process_plan),
        "dataset_sources": DATASET_SOURCES,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
REVERSE_DISPLAY = {v: k for k, v in OPERATION_DISPLAY_NAME.items()}
ALL_FEATURES = list(FEATURE_VOCABULARY.values())


def check1_feature_coverage(parts: list[dict], lines: list[str]):
    lines.append("=" * 70)
    lines.append("CHECK 1 -- Feature coverage")
    lines.append("=" * 70)
    counts = {f: 0 for f in ALL_FEATURES}
    for p in parts:
        for f in p["features_list"]:
            counts[f["feature_name"]] += 1
    for f in ALL_FEATURES:
        lines.append(f"  {f:40s} {counts[f]:4d}")
    under = [f for f, c in counts.items() if c < 5]
    if under:
        lines.append(f"WARNING: under-represented (<5 occurrences): {under}")
    else:
        lines.append("All 27 features appear at least 5 times.")
    lines.append("")
    return counts


def check2_part_distribution(parts: list[dict], lines: list[str]):
    lines.append("=" * 70)
    lines.append("CHECK 2 -- Part type distribution")
    lines.append("=" * 70)
    counts = {pt: 0 for pt in MECHCAD_PART_CLASSES}
    for p in parts:
        counts[p["part_type"]] += 1
    for pt in MECHCAD_PART_CLASSES:
        lines.append(f"  {pt:20s} {counts[pt]:4d}")
    under = [pt for pt, c in counts.items() if c < 40]
    if under:
        lines.append(f"WARNING: under-represented (<40 entries, target ~60): {under}")
    else:
        lines.append("All part types have >= 40 entries.")
    lines.append("")
    return counts


def check3_sequencing(parts: list[dict], lines: list[str]):
    lines.append("=" * 70)
    lines.append("CHECK 3 -- Sequencing correctness")
    lines.append("=" * 70)
    passed = 0
    failures = []
    for p in parts:
        plan = p["process_plan"]
        ok = True
        reasons = []

        if not plan or plan[0]["operation"] != "Facing and Centering":
            ok = False
            reasons.append("step1 not Facing and Centering")

        priorities = [OPERATION_PRIORITY[REVERSE_DISPLAY[s["operation"]]] for s in plan]
        if priorities != sorted(priorities):
            ok = False
            reasons.append("priorities not monotonic (rough/semi/finish/grind order violated)")

        chamfer_idxs = [
            i for i, s in enumerate(plan) if REVERSE_DISPLAY[s["operation"]] in ("chamfering_turning", "chamfering_milling")
        ]
        if chamfer_idxs and min(len(plan) - i for i in chamfer_idxs) > 2:
            ok = False
            reasons.append("chamfering not in last 2 steps")

        if ok:
            passed += 1
        else:
            failures.append((p["part_id"], reasons))

    lines.append(f"{passed}/{len(parts)} plans passed sequencing validation")
    if failures:
        lines.append(f"Failures (first 10 shown of {len(failures)}):")
        for pid, reasons in failures[:10]:
            lines.append(f"  {pid}: {reasons}")
    lines.append("")
    return passed


def check4_operation_counts(parts: list[dict], lines: list[str]):
    lines.append("=" * 70)
    lines.append("CHECK 4 -- Operation count sanity")
    lines.append("=" * 70)
    buckets = {"3-5": 0, "6-8": 0, "9-12": 0, "13+": 0}
    flagged = []
    for p in parts:
        n = p["total_operations"]
        if 3 <= n <= 5:
            buckets["3-5"] += 1
        elif 6 <= n <= 8:
            buckets["6-8"] += 1
        elif 9 <= n <= 12:
            buckets["9-12"] += 1
        elif n >= 13:
            buckets["13+"] += 1
        if n < 3 or n > 18:
            flagged.append((p["part_id"], n))
    for k, v in buckets.items():
        lines.append(f"  {k:10s} {v:4d}")
    if flagged:
        lines.append(f"FLAGGED (n<3 or n>18): {flagged}")
    else:
        lines.append("No plans flagged for op-count out of [3, 18].")
    lines.append("")
    return buckets


def check5_source_traceability(parts: list[dict], lines: list[str]):
    lines.append("=" * 70)
    lines.append("CHECK 5 -- Source traceability")
    lines.append("=" * 70)
    all_ok = all(bool(p.get("dataset_sources")) for p in parts)
    lines.append(f"All {len(parts)} parts have source citation metadata: {'YES' if all_ok else 'NO'}")
    lines.append("")
    return all_ok


def run_validation(parts: list[dict]) -> str:
    lines = []
    check1_feature_coverage(parts, lines)
    check2_part_distribution(parts, lines)
    check3_sequencing(parts, lines)
    check4_operation_counts(parts, lines)
    check5_source_traceability(parts, lines)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parts = [generate_part(i) for i in range(1, N_PARTS + 1)]

    dataset_path = os.path.join(OUT_DIR, "capp_dataset.json")
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(parts, f, indent=2)

    metadata = {
        "dataset_name": "CAPP-Bench-600",
        "version": "1.0",
        "created_by": "Generated by LLM-CAPP Research Team",
        "generation_date": date.today().isoformat(),
        "total_parts": N_PARTS,
        "feature_vocabulary_source": {
            "name": "FeatureNet Machining Feature Dataset",
            "authors": "Zhang et al.",
            "journal": "Computer-Aided Design",
            "volume": 101,
            "year": 2018,
            "doi": "10.1016/j.cad.2018.01.001",
            "url": "https://github.com/zibozzb/FeatureNet",
            "feature_classes_used": 24,
            "supplementary_features": 3,
            "supplementary_source": "MFCAD++ dataset, Colligan et al. 2022",
        },
        "part_type_source": {
            "name": "MechCAD Dataset",
            "description": "10-class mechanical part B-rep classification dataset",
            "classes_used": 10,
        },
        "operation_rule_source": {
            "name": "Machining Data Handbook",
            "publisher": "Metcut Research Associates",
            "edition": "3rd Edition",
            "year": 1980,
            "url": "https://archive.org/details/machiningdatahan0002unse",
        },
        "tolerance_standard": {
            "name": "ISO 286-1",
            "title": "Geometrical product specifications — Limits and fits — Part 1",
        },
        "generation_notes": (
            "Part dimensions, materials, tolerances, and feature selection are "
            "randomly sampled (seed=42) subject to the rule tables in "
            "operation_rules.py. Feature-to-operation, machine, tool, and "
            "cutting-parameter mappings are this project's rule-based encoding "
            "informed by (not a verbatim transcription of) the cited handbook; "
            "see provenance notes in operation_rules.py and part_vocabulary.py."
        ),
    }
    metadata_path = os.path.join(OUT_DIR, "dataset_metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    report = run_validation(parts)
    report_path = os.path.join(OUT_DIR, "validation_report.txt")
    header = (
        f"CAPP-Bench-600 Validation Report\n"
        f"Generated: {date.today().isoformat()}\n"
        f"Total parts: {N_PARTS}\n\n"
    )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(header + report)

    print(header + report)
    print(f"\nWrote {dataset_path}")
    print(f"Wrote {metadata_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
