import json
import os
import random
from datetime import date

from feature_vocabulary import ALL_FEATURES
from part_vocabulary import MECHCAD_PART_CLASSES
from operation_rules import (
    FEATURE_TO_OPERATIONS,
    MACHINE_ASSIGNMENT,
    TOOL_ASSIGNMENT,
    DEFAULT_TOOL,
    CUTTING_PARAMS,
    DEFAULT_PARAMS,
    PART_FEATURE_COMPATIBILITY,
    SEQUENCING_PRIORITY,
)

random.seed(42)

N_PARTS = 600
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

MATERIALS = ["mild_steel", "EN24_alloy_steel", "cast_iron", "aluminium_6061", "stainless_steel_316"]

MATERIAL_DISPLAY = {
    "mild_steel": "Mild steel",
    "EN24_alloy_steel": "EN24 alloy steel",
    "cast_iron": "Cast iron",
    "aluminium_6061": "Aluminium 6061",
    "stainless_steel_316": "Stainless steel 316",
}

ROTATIONAL_PART_TYPES = {"shaft", "coupling", "gear", "bearing_housing", "pulley", "bushing"}

DIMENSION_RANGES = {
    "shaft": {"diameter": (20, 150), "length": (80, 500)},
    "flange": {"OD": (80, 400), "thickness": (15, 60), "bore": (20, 150)},
    "bracket": {"length": (80, 300), "width": (50, 200), "height": (30, 150)},
    "coupling": {"OD": (40, 200), "length": (60, 250), "bore": (20, 100)},
    "gear": {"OD": (50, 300), "face_width": (20, 80), "bore": (20, 80)},
    "bearing_housing": {"OD": (60, 250), "bore": (20, 120), "length": (40, 150)},
    "pulley": {"OD": (80, 500), "face_width": (30, 100), "bore": (20, 80)},
    "cover_plate": {"length": (80, 400), "width": (60, 300), "thickness": (8, 30)},
    "bushing": {"OD": (30, 150), "ID": (20, 100), "length": (20, 100)},
    "connecting_rod": {"length": (100, 400), "big_end_bore": (30, 80), "small_end_bore": (15, 40)},
}

THREAD_SIZES_MM = [6, 8, 10, 12, 14, 16, 18, 20, 24]

HANDBOOK_SOURCE = "Machining Data Handbook, Metcut Research, 3rd Ed. 1980"

OPERATION_PURPOSE = {
    "facing": "Establish datum face",
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
    "slot_milling": "Cut the slot to width and depth in a single pass",
    "shoulder_milling": "Machine the stepped shoulder feature",
    "angle_milling": "Machine the angled/slanted step feature",
    "taper_turning": "Turn the tapered section",
    "tapping": "Cut the internal thread form",
    "thread_turning": "Cut the external thread form on the lathe",
    "thread_rolling": "Form the external thread by cold rolling",
    "grooving_turning": "Turn the O-ring / seal groove",
    "cylindrical_grinding": "Achieve final OD tolerance and surface finish by grinding",
    "internal_grinding": "Achieve final bore tolerance and surface finish by grinding",
    "chamfering": "Break sharp edges",
    "deburring": "Remove burrs from machined edges",
}

SEQUENCING_RULE_TEXT = {
    1: "RULE 1 — datum first",
    2: "RULE 2 — rough operations before semi-finish/finish",
    3: "RULE 4 — drilling before boring before reaming",
    4: "RULE 3 — semi-finish before finish",
    5: "RULE 4 — drilling before boring before reaming",
    6: "RULE 5 — internal/prismatic features before external finishing",
    7: "RULE 6/8 — groove/taper after finish turning of that diameter",
    8: "RULE 3 — finish after rough/semi-finish",
    9: "RULE 6/7 — threads/reaming after finish turning of that diameter",
    10: "RULE 9 — grinding always the last size-controlling operation",
    11: "RULE 10 — chamfering/deburring is the final operation",
    12: "RULE 10 — chamfering/deburring is the final operation",
}


def sample_dimensions(part_type):
    ranges = DIMENSION_RANGES[part_type]
    return {name: random.randint(lo, hi) for name, (lo, hi) in ranges.items()}


def sample_tolerance():
    r = random.random()
    if r <= 0.30:
        return "tight"
    if r <= 0.60:
        return "H8"
    return "IT9"


def tolerance_label(category, rotational):
    if category == "tight":
        return "h6" if rotational else "H7"
    return category


def sample_surface_finish(category):
    if category == "tight":
        return random.choice([0.8, 1.6])
    if category == "H8":
        return random.choice([1.6, 3.2])
    return random.choice([3.2, 6.3])


def key_dimension_text(part_type, dims):
    if part_type == "shaft":
        return f"{dims['diameter']}mm diameter, {dims['length']}mm length"
    if part_type in ("flange", "coupling", "bearing_housing"):
        return f"{dims['OD']}mm OD, {dims['bore']}mm bore"
    if part_type == "bracket":
        return f"{dims['length']}x{dims['width']}x{dims['height']}mm envelope"
    if part_type == "gear":
        return f"{dims['OD']}mm OD, {dims['face_width']}mm face width, {dims['bore']}mm bore"
    if part_type == "pulley":
        return f"{dims['OD']}mm OD, {dims['face_width']}mm face width, {dims['bore']}mm bore"
    if part_type == "cover_plate":
        return f"{dims['length']}x{dims['width']}x{dims['thickness']}mm plate"
    if part_type == "bushing":
        return f"{dims['OD']}mm OD, {dims['ID']}mm ID, {dims['length']}mm length"
    if part_type == "connecting_rod":
        return f"{dims['length']}mm length, {dims['big_end_bore']}mm big-end bore, {dims['small_end_bore']}mm small-end bore"
    raise ValueError(part_type)


def bore_reference(part_type, dims):
    for key in ("bore", "ID", "big_end_bore", "diameter"):
        if key in dims:
            return dims[key]
    return 25


def select_features(part_type):
    eligible_ids = PART_FEATURE_COMPATIBILITY[part_type]
    selected = []
    if part_type in ROTATIONAL_PART_TYPES and 23 in eligible_ids:
        selected.append(23)
    if 0 in eligible_ids:
        selected.append(0)

    remaining = [fid for fid in eligible_ids if fid not in selected]
    n_extra = min(len(remaining), random.randint(2, 4))
    selected.extend(random.sample(remaining, n_extra))
    return selected


def make_feature_instance(feature_id, dims, part_type):
    feature_name = ALL_FEATURES[feature_id]
    inst = {"feature_id": feature_id, "feature_name": feature_name}
    if feature_name in ("through_hole", "blind_hole"):
        bore_ref = bore_reference(part_type, dims)
        inst["diameter_mm"] = round(random.uniform(5, max(6, min(bore_ref, 60))), 1)
        inst["count"] = random.choice([1, 1, 2, 4, 6])
    if feature_name in ("thread_external", "thread_internal"):
        inst["thread_size_mm"] = random.choice(THREAD_SIZES_MM)
        inst["count"] = random.choice([1, 1, 2, 4])
    if feature_name == "rectangular_blind_slot":
        inst["width_mm"] = random.choice([6, 8, 10, 12, 14, 16, 18])
        inst["depth_mm"] = round(inst["width_mm"] * 0.4, 1)
    return inst


def build_operations(features, material, tolerance, ra):
    operations = []

    operations.append({
        "step": 1,
        "operation": "facing",
        "machine": MACHINE_ASSIGNMENT.get("facing", "CNC_Turning_Centre"),
        "tool": TOOL_ASSIGNMENT.get(("rough_turning", material), DEFAULT_TOOL),
    })

    for feat in features:
        feature_name = feat["feature_name"]
        rule = FEATURE_TO_OPERATIONS.get(feature_name)
        if rule is None:
            continue

        if isinstance(rule, dict):
            ops = list(rule.get("base", []))
            diameter_mm = feat.get("diameter_mm")
            if diameter_mm is not None and diameter_mm > 25 and "if_diameter_gt_25" in rule:
                ops += rule["if_diameter_gt_25"]
            if tolerance == "H7" and "if_tolerance_H7" in rule:
                ops += rule["if_tolerance_H7"]
            if tolerance == "h6" and "if_tolerance_h6" in rule:
                ops += rule["if_tolerance_h6"]
            if ra <= 1.6 and "if_Ra_lte_1_6" in rule:
                ops += rule["if_Ra_lte_1_6"]
        else:
            ops = list(rule)

        for op in ops:
            operations.append({
                "step": 0,
                "operation": op,
                "machine": MACHINE_ASSIGNMENT.get(op, "General_Machine"),
                "tool": TOOL_ASSIGNMENT.get((op, material), DEFAULT_TOOL),
            })

    operations.append({
        "step": 0,
        "operation": "chamfering",
        "machine": MACHINE_ASSIGNMENT.get("chamfering", "VMC_Vertical_Machining_Centre"),
        "tool": DEFAULT_TOOL,
    })

    seen_ops = []
    unique_operations = []
    for op in operations:
        if op["operation"] not in seen_ops:
            seen_ops.append(op["operation"])
            unique_operations.append(op)

    unique_operations.sort(key=lambda o: SEQUENCING_PRIORITY.get(o["operation"], 99))

    process_plan = []
    for i, op in enumerate(unique_operations, start=1):
        priority = SEQUENCING_PRIORITY.get(op["operation"], 99)
        process_plan.append({
            "step": i,
            "operation": op["operation"],
            "machine": op["machine"],
            "tool": op["tool"],
            "cutting_params": CUTTING_PARAMS.get((material, op["operation"]), DEFAULT_PARAMS),
            "purpose": OPERATION_PURPOSE.get(op["operation"], "Perform required machining operation"),
            "sequencing_rule": SEQUENCING_RULE_TEXT.get(priority, "RULE — standard sequencing"),
            "source": HANDBOOK_SOURCE,
        })
    return process_plan


FEATURE_DESC_TEMPLATES = {
    "round_external_cylinder": lambda f, dims: None,  # folded into key dimension string
    "through_hole": lambda f, dims: f"{f.get('count', 1)} through hole(s) {f.get('diameter_mm', '?')}mm diameter",
    "blind_hole": lambda f, dims: f"{f.get('count', 1)} blind hole(s) {f.get('diameter_mm', '?')}mm diameter",
    "rectangular_blind_slot": lambda f, dims: f"keyway {f.get('width_mm', '?')}x{f.get('depth_mm', '?')}mm",
    "O_ring_groove": lambda f, dims: "O-ring groove",
    "thread_external": lambda f, dims: f"M{f.get('thread_size_mm', '?')} external thread",
    "thread_internal": lambda f, dims: f"M{f.get('thread_size_mm', '?')} tapped holes",
    "chamfer": lambda f, dims: "chamfered edges",
}


def feature_description(feature, dims):
    name = feature["feature_name"]
    tmpl = FEATURE_DESC_TEMPLATES.get(name)
    if tmpl:
        text = tmpl(feature, dims)
        return text
    return name.replace("_", " ")


def build_description(part_type, material, dims, features, tolerance, ra):
    mat = MATERIAL_DISPLAY[material]
    dim_text = key_dimension_text(part_type, dims)
    feature_texts = []
    for feat in features:
        if feat["feature_name"] in ("round_external_cylinder",):
            continue
        text = feature_description(feat, dims)
        if text:
            feature_texts.append(text)

    relevant_surface = "the bearing journal" if part_type == "shaft" else "the primary bore"
    parts = [f"{mat} {part_type}", dim_text]
    parts.extend(feature_texts)
    parts.append(f"{tolerance} tolerance on {relevant_surface}")
    parts.append(f"Ra {ra} μm surface finish")
    return ", ".join(parts)


DATASET_SOURCES = {
    "feature_vocabulary": "FeatureNet — Zhang et al., Computer-Aided Design, Vol.101, 2018. DOI:10.1016/j.cad.2018.01.001",
    "part_classification": "MechCAD dataset — arXiv:2504.07134",
    "operation_rules": "Machining Data Handbook — Metcut Research Associates, 3rd Ed., 1980",
    "tolerance_standard": "ISO 286-1: Geometrical product specifications — Limits and fits",
}


def feature_source(feature_id):
    if feature_id <= 23:
        return f"FeatureNet class {feature_id} — Zhang et al., CAD Vol.101, 2018"
    return f"MFCAD++ supplementary class {feature_id} — Colligan et al., 2022"


def generate_part(idx):
    part_type = random.choice(MECHCAD_PART_CLASSES)
    material = random.choice(MATERIALS)
    dims = sample_dimensions(part_type)

    tol_category = sample_tolerance()
    rotational = part_type in ROTATIONAL_PART_TYPES
    tolerance = tolerance_label(tol_category, rotational)
    ra = sample_surface_finish(tol_category)

    feature_ids = select_features(part_type)
    features = [make_feature_instance(fid, dims, part_type) for fid in feature_ids]

    process_plan = build_operations(features, material, tolerance, ra)
    description = build_description(part_type, material, dims, features, tolerance, ra)

    features_list = [
        {
            "feature_id": f["feature_id"],
            "feature_name": f["feature_name"],
            "source": feature_source(f["feature_id"]),
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


def main():
    parts = [generate_part(i) for i in range(1, N_PARTS + 1)]

    out_path = os.path.join(OUT_DIR, "synthetic_parts.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(parts, f, indent=2)
    print(f"Generated {len(parts)} parts -> {out_path}")

    part_type_counts = {}
    feature_counts = {}
    op_counts = []
    for p in parts:
        part_type_counts[p["part_type"]] = part_type_counts.get(p["part_type"], 0) + 1
        for f in p["features_list"]:
            feature_counts[f["feature_name"]] = feature_counts.get(f["feature_name"], 0) + 1
        op_counts.append(p["total_operations"])

    print("\nPart type distribution:")
    for pt, c in sorted(part_type_counts.items()):
        print(f"  {pt:20s} {c:4d}")

    print("\nFeature coverage:")
    for fname, c in sorted(feature_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {fname:40s} {c:4d}")

    print(f"\nAverage operations per plan: {sum(op_counts)/len(op_counts):.2f}")

    seq_pass = 0
    for p in parts:
        plan = p["process_plan"]
        ok = plan and plan[0]["operation"] == "facing"
        if ok:
            chamfer_idx = [i for i, s in enumerate(plan) if s["operation"] in ("chamfering", "deburring")]
            if chamfer_idx and min(len(plan) - i for i in chamfer_idx) > 2:
                ok = False
        if ok:
            seq_pass += 1
    print(f"\nSequencing check passed: {seq_pass}/{len(parts)}")


if __name__ == "__main__":
    main()
