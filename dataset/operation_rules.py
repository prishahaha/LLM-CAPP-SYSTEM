"""
Operation-feature-machine-tool mapping rules.

Primary reference: Machining Data Handbook, Metcut Research Associates,
3rd Edition, 1980. Available: archive.org/details/machiningdatahan0002unse

Tolerance/finish rules reference: ISO 286-1, "Geometrical product
specifications -- Limits and fits -- Part 1".

PROVENANCE NOTE: the feature->operation sequences, machine/tool assignment
tables, and CUTTING_PARAMS values below are this project's *encoding* of
standard machining practice, informed by (but not a verbatim transcription
of) the Machining Data Handbook. Several tool/machine choices for operations
not explicitly enumerated in the source spec (e.g. centre_drilling tooling,
semi-finish turning tooling, grinding wheel choice for softer materials) are
engineering-reasonable extrapolations made for pipeline completeness and are
marked inline. Treat this module as a documented rule-based heuristic engine
for synthetic dataset generation, not as a citation-checked digitisation of
the handbook -- verify specific values against the primary source before
quoting them in a publication.
"""

from __future__ import annotations

MATERIALS = [
    "mild_steel",
    "EN24_alloy_steel",
    "cast_iron",
    "aluminium_6061",
    "stainless_steel_316",
]

STEEL_FAMILY = {"mild_steel", "EN24_alloy_steel", "stainless_steel_316"}

# ---------------------------------------------------------------------------
# Operation sequencing priority buckets (Machining Data Handbook, Chapter 1 --
# Process Planning Fundamentals): rough 1-10, semi-finish 11-20, finish 21-30,
# grinding 31-40, chamfer/deburr 50.
# ---------------------------------------------------------------------------
OPERATION_PRIORITY = {
    "facing_centering": 0,
    "centre_drilling": 2,
    "drilling": 3,
    "boring": 4,
    "reaming": 5,
    "rough_turning": 6,
    "face_milling": 7,
    "end_milling_rough": 8,
    "slot_milling": 9,
    "shoulder_milling": 9,
    "angle_milling": 9,
    "end_milling": 9,
    "milling": 9,
    "taper_turning": 9,
    "semi_finish_turning": 15,
    "end_milling_finish": 21,
    "finish_turning": 22,
    "tapping": 23,
    "thread_turning": 24,
    "thread_rolling": 24,
    "internal_thread_milling": 25,
    "grooving_turning": 26,
    "cylindrical_grinding": 31,
    "internal_grinding": 32,
    "surface_grinding": 33,
    "chamfering_turning": 50,
    "chamfering_milling": 50,
    "deburring": 51,
}

OPERATION_DISPLAY_NAME = {
    "facing_centering": "Facing and Centering",
    "centre_drilling": "Centre Drilling",
    "drilling": "Drilling",
    "boring": "Boring",
    "reaming": "Reaming",
    "rough_turning": "Rough Turning",
    "semi_finish_turning": "Semi-Finish Turning",
    "finish_turning": "Finish Turning",
    "face_milling": "Face Milling",
    "end_milling_rough": "End Milling (Rough)",
    "end_milling_finish": "End Milling (Finish)",
    "end_milling": "End Milling",
    "milling": "Milling",
    "slot_milling": "Slot Milling",
    "shoulder_milling": "Shoulder Milling",
    "angle_milling": "Angle Milling",
    "taper_turning": "Taper Turning",
    "tapping": "Tapping",
    "thread_turning": "Thread Turning",
    "thread_rolling": "Thread Rolling",
    "internal_thread_milling": "Internal Thread Milling",
    "grooving_turning": "Grooving (Turning)",
    "cylindrical_grinding": "Cylindrical Grinding",
    "internal_grinding": "Internal Grinding",
    "surface_grinding": "Surface Grinding",
    "chamfering_turning": "Chamfering (Turning)",
    "chamfering_milling": "Chamfering (Milling)",
    "deburring": "Deburring",
}


# ---------------------------------------------------------------------------
# FEATURE_TO_OPERATIONS -- feature-specific operation logic
# ---------------------------------------------------------------------------
def get_operations_for_feature(
    feature_name: str,
    *,
    diameter_mm: float | None = None,
    tolerance: str | None = None,
    ra: float | None = None,
    is_threaded: bool = False,
    thread_size_mm: float | None = None,
    rotational_part: bool = True,
) -> list[str]:
    """Return the ordered list of raw operation names for a single feature
    instance, before global sequencing/priority sorting is applied.
    """
    tol_is_h7_H7 = tolerance in ("H7", "h6")
    fine_finish = ra is not None and ra <= 1.6

    if feature_name == "through_hole":
        ops = ["centre_drilling", "drilling"]
        if diameter_mm is not None and diameter_mm >= 25:
            ops.append("boring")
        if tol_is_h7_H7:
            ops.append("reaming")
        if fine_finish:
            ops.append("internal_grinding")
        return ops

    if feature_name == "blind_hole":
        ops = ["centre_drilling", "drilling"]
        if diameter_mm is not None and diameter_mm > 25:
            ops.append("boring")
        if is_threaded:
            ops.append("tapping")
        if tol_is_h7_H7:
            ops.append("reaming")
        return ops

    if feature_name == "round_external_cylinder":
        ops = ["rough_turning", "semi_finish_turning", "finish_turning"]
        if tolerance == "h6" or (ra is not None and ra <= 0.8):
            ops.append("cylindrical_grinding")
        return ops

    if feature_name in ("rectangular_pocket", "circular_end_pocket"):
        return ["face_milling", "end_milling_rough", "end_milling_finish"]

    if feature_name in ("triangular_pocket", "six_sided_pocket"):
        return ["end_milling_rough", "end_milling_finish"]

    if feature_name in ("rectangular_through_slot", "rectangular_blind_slot"):
        return ["slot_milling"]

    if feature_name in ("rectangular_through_step", "two_sided_through_step"):
        return ["face_milling", "shoulder_milling"]

    if feature_name == "rectangular_blind_step":
        return ["shoulder_milling"]

    if feature_name == "slanted_through_step":
        return ["face_milling", "angle_milling"]

    if feature_name in (
        "triangular_through_slot",
        "circular_through_slot",
        "triangular_blind_step",
        "circular_blind_step",
        "vertical_circular_end_blind_slot",
        "horizontal_circular_end_blind_slot",
    ):
        return ["end_milling"]

    if feature_name == "chamfer":
        return ["chamfering_turning"] if rotational_part else ["chamfering_milling"]

    if feature_name == "O_ring_groove":
        return ["grooving_turning"]

    if feature_name == "rectangular_passage":
        return ["drilling", "boring"] if rotational_part else ["milling"]

    if feature_name in ("triangular_passage", "six_sided_passage"):
        return ["end_milling"]

    if feature_name == "thread_external":
        if thread_size_mm is not None and thread_size_mm >= 18:
            return ["thread_turning"]
        return ["thread_turning"]  # M6-M16: thread_turning chosen (alt: thread_rolling)

    if feature_name == "thread_internal":
        if thread_size_mm is not None and thread_size_mm >= 18:
            return ["internal_thread_milling"]
        return ["tapping"]

    if feature_name == "taper":
        return ["taper_turning"]

    raise ValueError(f"No operation rule defined for feature '{feature_name}'")


# ---------------------------------------------------------------------------
# MACHINE ASSIGNMENT (Machining Data Handbook, Chapter 1 -- Machine Tool
# Selection)
# ---------------------------------------------------------------------------
_TURNING_OPS = {
    "rough_turning",
    "semi_finish_turning",
    "finish_turning",
    "boring",
    "reaming",  # inferred: reaming follows boring on the same setup
    "taper_turning",
    "grooving_turning",
    "thread_turning",
    "chamfering_turning",
}
_MILLING_OPS = {
    "milling",
    "slot_milling",
    "face_milling",
    "shoulder_milling",
    "angle_milling",
    "end_milling",
    "end_milling_rough",
    "end_milling_finish",
    "chamfering_milling",
    "internal_thread_milling",
}


def get_machine(operation: str, *, diameter_mm: float | None = None) -> str:
    if operation in _TURNING_OPS:
        return "CNC_Turning_Centre"
    if operation in _MILLING_OPS:
        return "VMC_Vertical_Machining_Centre"
    if operation in ("drilling", "centre_drilling"):
        if diameter_mm is not None and diameter_mm > 25:
            return "Radial_Drilling_Machine"
        return "VMC_Vertical_Machining_Centre"
    if operation == "tapping":
        return "Tapping_Machine"
    if operation == "cylindrical_grinding":
        return "Cylindrical_Grinder"
    if operation == "internal_grinding":
        return "Internal_Grinder"
    if operation == "surface_grinding":
        return "Surface_Grinder"
    if operation == "thread_rolling":
        return "Thread_Rolling_Machine"
    if operation == "facing_centering":
        return "CNC_Turning_Centre"
    raise ValueError(f"No machine assignment rule for operation '{operation}'")


# ---------------------------------------------------------------------------
# TOOL ASSIGNMENT (Machining Data Handbook, Chapters 3-5)
# ---------------------------------------------------------------------------
def get_tool(operation: str, material: str, *, tolerance: str | None = None) -> str:
    is_steel = material in STEEL_FAMILY

    if operation == "rough_turning":
        return {
            "mild_steel": "Carbide_insert_CNMG_432_grade_P25",
            "EN24_alloy_steel": "Carbide_insert_CNMG_432_grade_P25",
            "cast_iron": "Carbide_insert_CNMG_432_grade_K20",
            "aluminium_6061": "Carbide_insert_CCMT_grade_K10_uncoated",
            "stainless_steel_316": "Carbide_insert_CNMG_432_grade_M25_coated",
        }[material]

    if operation == "semi_finish_turning":
        # inferred: same insert family as rough turning, lighter cut
        return get_tool("rough_turning", material)

    if operation in ("finish_turning", "taper_turning"):
        if material == "aluminium_6061":
            return "Carbide_insert_VCMT_PCD_tipped"
        return "Carbide_insert_DCMT_070204_grade_P10"

    if operation in ("drilling", "centre_drilling"):
        if material == "aluminium_6061":
            return "HSS_drill_bright_finish"
        if material == "stainless_steel_316":
            return "Cobalt_HSS_drill"
        # mild_steel / EN24_alloy_steel / cast_iron: diameter-tiered rule
        # applied by caller via get_drilling_tool_for_diameter()
        return "HSS_twist_drill_DIN338"

    if operation == "boring":
        return "PCD_boring_bar" if material == "aluminium_6061" else "Carbide_boring_bar_positive_rake"

    if operation == "reaming":
        if tolerance == "H8":
            return "HSS_reamer"
        return "Carbide_reamer"  # H7 (or default)

    if operation == "tapping":
        return "HSS_tap_with_cutting_oil"

    if operation in ("end_milling", "end_milling_rough", "end_milling_finish",
                      "shoulder_milling", "angle_milling", "milling"):
        if material == "aluminium_6061":
            return "Carbide_end_mill_3_flute_uncoated_polished"
        return "Carbide_end_mill_4_flute_TiAlN_coated"

    if operation == "face_milling":
        return "Carbide_face_mill_insert_SNMG_grade_P25"

    if operation == "slot_milling":
        return "Carbide_slot_drill_2_flute"

    if operation == "cylindrical_grinding":
        return "CBN_wheel_B126_100V" if material == "stainless_steel_316" else "Aluminium_oxide_wheel_A60_K5_V"

    if operation == "internal_grinding":
        return "Aluminium_oxide_wheel_small_diameter"

    if operation == "surface_grinding":
        return "Aluminium_oxide_wheel_A60_K5_V"

    # Operations not explicitly specified in the source handbook excerpt --
    # engineering-reasonable defaults, not directly cited.
    if operation == "grooving_turning":
        return "Carbide_grooving_insert_2mm"
    if operation == "thread_turning":
        return "Carbide_thread_turning_insert_60deg"
    if operation == "thread_rolling":
        return "Thread_rolling_die_set"
    if operation == "internal_thread_milling":
        return "Carbide_thread_mill"
    if operation in ("chamfering_turning",):
        return "Carbide_insert_chamfer_tool"
    if operation in ("chamfering_milling",):
        return "Carbide_chamfer_end_mill"
    if operation == "facing_centering":
        return "Carbide_insert_CNMG_432_grade_P25" if is_steel or material == "cast_iron" else "Carbide_insert_CCMT_grade_K10_uncoated"

    raise ValueError(f"No tool assignment rule for operation '{operation}' / material '{material}'")


def get_drilling_tool(material: str, diameter_mm: float) -> str:
    """Diameter-tiered drilling tool selection (steel-family materials use
    the diameter-tiered rule; aluminium/stainless use the fixed material rule
    from get_tool())."""
    if material == "aluminium_6061":
        return "HSS_drill_bright_finish"
    if material == "stainless_steel_316":
        return "Cobalt_HSS_drill"
    if diameter_mm < 12:
        return "HSS_twist_drill_DIN338"
    if diameter_mm <= 25:
        return "Carbide_tipped_drill"
    return "Carbide_indexable_drill"


# ---------------------------------------------------------------------------
# CUTTING PARAMETERS (Machining Data Handbook, material-specific tables)
# ---------------------------------------------------------------------------
CUTTING_PARAMS = {
    ("mild_steel", "rough_turning"): {"speed_mpm": "80-120", "feed_mm_rev": "0.25-0.4", "doc_mm": "2-5"},
    ("mild_steel", "semi_finish_turning"): {"speed_mpm": "120-160", "feed_mm_rev": "0.15-0.25", "doc_mm": "0.5-1.5"},
    ("mild_steel", "finish_turning"): {"speed_mpm": "150-200", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.2-0.5"},
    ("mild_steel", "drilling"): {"speed_mpm": "20-30", "feed_mm_rev": "0.1-0.25", "doc_mm": "full_depth"},
    ("mild_steel", "centre_drilling"): {"speed_mpm": "15-25", "feed_mm_rev": "0.05-0.1", "doc_mm": "N/A"},
    ("mild_steel", "boring"): {"speed_mpm": "60-90", "feed_mm_rev": "0.1-0.2", "doc_mm": "0.5-2"},
    ("mild_steel", "reaming"): {"speed_mpm": "10-15", "feed_mm_rev": "0.2-0.4", "doc_mm": "0.1-0.2"},
    ("mild_steel", "tapping"): {"speed_mpm": "8-12", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("mild_steel", "end_milling"): {"speed_mpm": "60-100", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.5-2"},
    ("mild_steel", "face_milling"): {"speed_mpm": "90-140", "feed_mm_rev": "0.1-0.2", "doc_mm": "1-3"},
    ("mild_steel", "slot_milling"): {"speed_mpm": "60-90", "feed_mm_rev": "0.05-0.12", "doc_mm": "full_width"},
    ("mild_steel", "grooving_turning"): {"speed_mpm": "60-90", "feed_mm_rev": "0.05-0.1", "doc_mm": "groove_width"},
    ("mild_steel", "thread_turning"): {"speed_mpm": "40-70", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("mild_steel", "cylindrical_grinding"): {"speed_mpm": "25-35", "feed_mm_rev": "0.01-0.03", "doc_mm": "0.01-0.05"},
    ("mild_steel", "internal_grinding"): {"speed_mpm": "20-30", "feed_mm_rev": "0.01-0.02", "doc_mm": "0.01-0.03"},

    ("EN24_alloy_steel", "rough_turning"): {"speed_mpm": "60-90", "feed_mm_rev": "0.2-0.35", "doc_mm": "2-4"},
    ("EN24_alloy_steel", "semi_finish_turning"): {"speed_mpm": "90-120", "feed_mm_rev": "0.12-0.2", "doc_mm": "0.5-1.2"},
    ("EN24_alloy_steel", "finish_turning"): {"speed_mpm": "110-150", "feed_mm_rev": "0.05-0.12", "doc_mm": "0.2-0.4"},
    ("EN24_alloy_steel", "drilling"): {"speed_mpm": "15-22", "feed_mm_rev": "0.08-0.2", "doc_mm": "full_depth"},
    ("EN24_alloy_steel", "centre_drilling"): {"speed_mpm": "12-20", "feed_mm_rev": "0.04-0.08", "doc_mm": "N/A"},
    ("EN24_alloy_steel", "boring"): {"speed_mpm": "45-70", "feed_mm_rev": "0.08-0.18", "doc_mm": "0.5-1.5"},
    ("EN24_alloy_steel", "reaming"): {"speed_mpm": "8-12", "feed_mm_rev": "0.15-0.3", "doc_mm": "0.1-0.2"},
    ("EN24_alloy_steel", "tapping"): {"speed_mpm": "6-10", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("EN24_alloy_steel", "end_milling"): {"speed_mpm": "45-75", "feed_mm_rev": "0.04-0.1", "doc_mm": "0.5-1.5"},
    ("EN24_alloy_steel", "face_milling"): {"speed_mpm": "70-100", "feed_mm_rev": "0.08-0.15", "doc_mm": "1-2.5"},
    ("EN24_alloy_steel", "slot_milling"): {"speed_mpm": "45-70", "feed_mm_rev": "0.04-0.1", "doc_mm": "full_width"},
    ("EN24_alloy_steel", "grooving_turning"): {"speed_mpm": "45-70", "feed_mm_rev": "0.04-0.08", "doc_mm": "groove_width"},
    ("EN24_alloy_steel", "thread_turning"): {"speed_mpm": "30-55", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("EN24_alloy_steel", "cylindrical_grinding"): {"speed_mpm": "22-30", "feed_mm_rev": "0.01-0.025", "doc_mm": "0.01-0.04"},
    ("EN24_alloy_steel", "internal_grinding"): {"speed_mpm": "18-25", "feed_mm_rev": "0.01-0.02", "doc_mm": "0.01-0.03"},

    ("cast_iron", "rough_turning"): {"speed_mpm": "70-100", "feed_mm_rev": "0.2-0.4", "doc_mm": "2-5"},
    ("cast_iron", "semi_finish_turning"): {"speed_mpm": "100-130", "feed_mm_rev": "0.12-0.22", "doc_mm": "0.5-1.5"},
    ("cast_iron", "finish_turning"): {"speed_mpm": "130-170", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.2-0.5"},
    ("cast_iron", "drilling"): {"speed_mpm": "18-28", "feed_mm_rev": "0.1-0.25", "doc_mm": "full_depth"},
    ("cast_iron", "centre_drilling"): {"speed_mpm": "15-22", "feed_mm_rev": "0.05-0.1", "doc_mm": "N/A"},
    ("cast_iron", "boring"): {"speed_mpm": "55-85", "feed_mm_rev": "0.1-0.2", "doc_mm": "0.5-2"},
    ("cast_iron", "reaming"): {"speed_mpm": "9-14", "feed_mm_rev": "0.2-0.4", "doc_mm": "0.1-0.2"},
    ("cast_iron", "tapping"): {"speed_mpm": "6-10", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("cast_iron", "end_milling"): {"speed_mpm": "55-90", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.5-2"},
    ("cast_iron", "face_milling"): {"speed_mpm": "80-120", "feed_mm_rev": "0.1-0.2", "doc_mm": "1-3"},
    ("cast_iron", "slot_milling"): {"speed_mpm": "55-85", "feed_mm_rev": "0.05-0.12", "doc_mm": "full_width"},
    ("cast_iron", "grooving_turning"): {"speed_mpm": "55-85", "feed_mm_rev": "0.05-0.1", "doc_mm": "groove_width"},
    ("cast_iron", "thread_turning"): {"speed_mpm": "35-60", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("cast_iron", "cylindrical_grinding"): "N/A",
    ("cast_iron", "internal_grinding"): "N/A",

    ("aluminium_6061", "rough_turning"): {"speed_mpm": "200-400", "feed_mm_rev": "0.2-0.4", "doc_mm": "2-6"},
    ("aluminium_6061", "semi_finish_turning"): {"speed_mpm": "300-450", "feed_mm_rev": "0.12-0.25", "doc_mm": "0.5-1.5"},
    ("aluminium_6061", "finish_turning"): {"speed_mpm": "350-600", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.2-0.5"},
    ("aluminium_6061", "drilling"): {"speed_mpm": "60-100", "feed_mm_rev": "0.15-0.3", "doc_mm": "full_depth"},
    ("aluminium_6061", "centre_drilling"): {"speed_mpm": "40-70", "feed_mm_rev": "0.08-0.15", "doc_mm": "N/A"},
    ("aluminium_6061", "boring"): {"speed_mpm": "150-300", "feed_mm_rev": "0.1-0.25", "doc_mm": "0.5-2"},
    ("aluminium_6061", "reaming"): {"speed_mpm": "20-30", "feed_mm_rev": "0.2-0.4", "doc_mm": "0.1-0.2"},
    ("aluminium_6061", "tapping"): {"speed_mpm": "10-15", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("aluminium_6061", "end_milling"): {"speed_mpm": "200-350", "feed_mm_rev": "0.08-0.2", "doc_mm": "0.5-3"},
    ("aluminium_6061", "face_milling"): {"speed_mpm": "250-450", "feed_mm_rev": "0.12-0.25", "doc_mm": "1-4"},
    ("aluminium_6061", "slot_milling"): {"speed_mpm": "200-350", "feed_mm_rev": "0.08-0.18", "doc_mm": "full_width"},
    ("aluminium_6061", "grooving_turning"): {"speed_mpm": "150-300", "feed_mm_rev": "0.05-0.12", "doc_mm": "groove_width"},
    ("aluminium_6061", "thread_turning"): {"speed_mpm": "100-200", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("aluminium_6061", "cylindrical_grinding"): "N/A",
    ("aluminium_6061", "internal_grinding"): "N/A",

    ("stainless_steel_316", "rough_turning"): {"speed_mpm": "40-60", "feed_mm_rev": "0.15-0.25", "doc_mm": "1.5-3"},
    ("stainless_steel_316", "semi_finish_turning"): {"speed_mpm": "60-85", "feed_mm_rev": "0.1-0.18", "doc_mm": "0.4-1"},
    ("stainless_steel_316", "finish_turning"): {"speed_mpm": "80-110", "feed_mm_rev": "0.05-0.1", "doc_mm": "0.15-0.4"},
    ("stainless_steel_316", "drilling"): {"speed_mpm": "10-18", "feed_mm_rev": "0.06-0.15", "doc_mm": "full_depth"},
    ("stainless_steel_316", "centre_drilling"): {"speed_mpm": "8-14", "feed_mm_rev": "0.03-0.06", "doc_mm": "N/A"},
    ("stainless_steel_316", "boring"): {"speed_mpm": "30-50", "feed_mm_rev": "0.06-0.14", "doc_mm": "0.4-1.2"},
    ("stainless_steel_316", "reaming"): {"speed_mpm": "6-10", "feed_mm_rev": "0.1-0.25", "doc_mm": "0.1-0.15"},
    ("stainless_steel_316", "tapping"): {"speed_mpm": "4-8", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("stainless_steel_316", "end_milling"): {"speed_mpm": "30-55", "feed_mm_rev": "0.03-0.08", "doc_mm": "0.3-1.2"},
    ("stainless_steel_316", "face_milling"): {"speed_mpm": "50-80", "feed_mm_rev": "0.06-0.12", "doc_mm": "0.8-2"},
    ("stainless_steel_316", "slot_milling"): {"speed_mpm": "30-55", "feed_mm_rev": "0.03-0.08", "doc_mm": "full_width"},
    ("stainless_steel_316", "grooving_turning"): {"speed_mpm": "30-50", "feed_mm_rev": "0.03-0.06", "doc_mm": "groove_width"},
    ("stainless_steel_316", "thread_turning"): {"speed_mpm": "20-35", "feed_mm_rev": "pitch", "doc_mm": "N/A"},
    ("stainless_steel_316", "cylindrical_grinding"): {"speed_mpm": "18-25", "feed_mm_rev": "0.008-0.02", "doc_mm": "0.01-0.03"},
    ("stainless_steel_316", "internal_grinding"): {"speed_mpm": "15-22", "feed_mm_rev": "0.008-0.015", "doc_mm": "0.01-0.02"},
}


def get_cutting_params(material: str, operation: str) -> dict | str:
    """Look up cutting parameters; falls back to the same-material
    end_milling/rough_turning entry for milling/turning sub-operations not
    explicitly tabulated (e.g. end_milling_rough uses end_milling params)."""
    key = (material, operation)
    if key in CUTTING_PARAMS:
        return CUTTING_PARAMS[key]

    fallback_map = {
        "end_milling_rough": "end_milling",
        "end_milling_finish": "end_milling",
        "shoulder_milling": "end_milling",
        "angle_milling": "end_milling",
        "milling": "end_milling",
        "taper_turning": "finish_turning",
        "thread_rolling": "rough_turning",
        "internal_thread_milling": "end_milling",
        "chamfering_turning": "finish_turning",
        "chamfering_milling": "end_milling",
        "facing_centering": "rough_turning",
    }
    if operation in fallback_map:
        return CUTTING_PARAMS.get((material, fallback_map[operation]), "N/A")
    return "N/A"


# ---------------------------------------------------------------------------
# TOLERANCE / SURFACE FINISH RULES (ISO 286-1)
# ---------------------------------------------------------------------------
TOLERANCE_TO_FINISHING_OPERATION = {
    "IT6_h6": "cylindrical_grinding is mandatory as final operation",
    "IT7_H7": "reaming (bore) or fine_boring or cylindrical_grinding (shaft)",
    "IT8_H8": "fine_turning or reaming acceptable",
    "IT9": "standard turning or milling is sufficient",
    "IT11": "rough turning or rough milling is sufficient",
}

SURFACE_FINISH_TO_OPERATION = {
    "Ra_0_8": "cylindrical_grinding or internal_grinding mandatory",
    "Ra_1_6": "finish_turning (skilled) or grinding",
    "Ra_3_2": "semi_finish_turning or finish_milling",
    "Ra_6_3": "rough_turning acceptable",
    "Ra_12_5": "rough_milling or rough_turning",
}


def ra_bucket(ra: float) -> str:
    if ra <= 0.8:
        return "Ra_0_8"
    if ra <= 1.6:
        return "Ra_1_6"
    if ra <= 3.2:
        return "Ra_3_2"
    if ra <= 6.3:
        return "Ra_6_3"
    return "Ra_12_5"


# ---------------------------------------------------------------------------
# PART-TO-FEATURE COMPATIBILITY (manufacturing common sense)
# ---------------------------------------------------------------------------
PART_FEATURE_COMPATIBILITY = {
    "shaft": [
        "round_external_cylinder",
        "through_hole",
        "blind_hole",
        "rectangular_blind_slot",
        "O_ring_groove",
        "chamfer",
        "thread_external",
        "taper",
        "rectangular_through_step",
        "circular_through_slot",
    ],
    "flange": [
        "round_external_cylinder",
        "through_hole",
        "blind_hole",
        "O_ring_groove",
        "chamfer",
        "rectangular_through_step",
        "thread_internal",
        "circular_end_pocket",
    ],
    "bracket": [
        "through_hole",
        "blind_hole",
        "rectangular_pocket",
        "rectangular_through_slot",
        "chamfer",
        "rectangular_through_step",
        "thread_internal",
        "rectangular_passage",
    ],
    "coupling": [
        "round_external_cylinder",
        "through_hole",
        "blind_hole",
        "rectangular_blind_slot",
        "thread_internal",
        "chamfer",
        "O_ring_groove",
    ],
    "gear": [
        "round_external_cylinder",
        "through_hole",
        "blind_hole",
        "rectangular_blind_slot",
        "chamfer",
        "O_ring_groove",
        # note: gear teeth are NOT in FeatureNet -- excluded from scope
    ],
    "bearing_housing": [
        "round_external_cylinder",
        "through_hole",
        "blind_hole",
        "rectangular_pocket",
        "chamfer",
        "O_ring_groove",
        "thread_internal",
        "rectangular_through_step",
    ],
    "pulley": [
        "round_external_cylinder",
        "through_hole",
        "rectangular_blind_slot",
        "chamfer",
        "O_ring_groove",
        "circular_through_slot",
    ],
    "cover_plate": [
        "through_hole",
        "blind_hole",
        "rectangular_pocket",
        "rectangular_through_slot",
        "chamfer",
        "thread_internal",
        "circular_end_pocket",
        "O_ring_groove",
    ],
    "bushing": [
        "round_external_cylinder",
        "through_hole",
        "O_ring_groove",
        "chamfer",
        "rectangular_blind_slot",
        "rectangular_through_step",
    ],
    "connecting_rod": [
        "through_hole",
        "blind_hole",
        "rectangular_pocket",
        "chamfer",
        "thread_internal",
        "rectangular_through_step",
    ],
}

ROTATIONAL_PART_TYPES = {"shaft", "flange", "coupling", "gear", "bearing_housing", "pulley", "bushing"}
