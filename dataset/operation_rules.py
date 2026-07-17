"""
Operation-feature mapping rules sourced from:
Machining Data Handbook, Metcut Research Associates, 3rd Ed., 1980.
Free access: https://archive.org/details/machiningdatahan0002unse
"""

FEATURE_TO_OPERATIONS = {
    "round_external_cylinder": {
        "base": ["rough_turning", "semi_finish_turning", "finish_turning"],
        "if_tolerance_h6": ["cylindrical_grinding"],
        "if_Ra_lte_1_6":  ["cylindrical_grinding"]
    },
    "through_hole": {
        "base": ["centre_drilling", "drilling"],
        "if_diameter_gt_25": ["boring"],
        "if_tolerance_H7":   ["reaming"]
    },
    "blind_hole": {
        "base": ["centre_drilling", "drilling"],
        "if_diameter_gt_25": ["boring"],
        "if_tolerance_H7":   ["reaming"]
    },
    "rectangular_pocket":              ["face_milling", "end_milling_rough", "end_milling_finish"],
    "circular_end_pocket":             ["face_milling", "end_milling_rough", "end_milling_finish"],
    "triangular_pocket":               ["end_milling_rough", "end_milling_finish"],
    "six_sided_pocket":                ["end_milling_rough", "end_milling_finish"],
    "rectangular_through_slot":        ["slot_milling"],
    "rectangular_blind_slot":          ["slot_milling"],
    "rectangular_through_step":        ["face_milling", "shoulder_milling"],
    "rectangular_blind_step":          ["shoulder_milling"],
    "two_sided_through_step":          ["face_milling", "shoulder_milling"],
    "slanted_through_step":            ["face_milling", "angle_milling"],
    "triangular_through_slot":         ["end_milling"],
    "circular_through_slot":           ["end_milling"],
    "triangular_blind_step":           ["end_milling"],
    "circular_blind_step":             ["end_milling"],
    "vertical_circular_end_blind_slot":   ["end_milling"],
    "horizontal_circular_end_blind_slot": ["end_milling"],
    "chamfer":                         ["chamfering"],
    "O_ring_groove":                   ["grooving_turning"],
    "rectangular_passage":             ["drilling", "boring"],
    "triangular_passage":              ["end_milling"],
    "six_sided_passage":               ["end_milling"],
    "thread_external":                 ["thread_turning"],
    "thread_internal":                 ["tapping"],
    "taper":                           ["taper_turning"]
}

MACHINE_ASSIGNMENT = {
    "rough_turning":       "CNC_Turning_Centre",
    "semi_finish_turning": "CNC_Turning_Centre",
    "finish_turning":      "CNC_Turning_Centre",
    "taper_turning":       "CNC_Turning_Centre",
    "grooving_turning":    "CNC_Turning_Centre",
    "thread_turning":      "CNC_Turning_Centre",
    "boring":              "CNC_Turning_Centre",
    "cylindrical_grinding":"Cylindrical_Grinder",
    "internal_grinding":   "Internal_Grinder",
    "face_milling":        "VMC_Vertical_Machining_Centre",
    "end_milling_rough":   "VMC_Vertical_Machining_Centre",
    "end_milling_finish":  "VMC_Vertical_Machining_Centre",
    "end_milling":         "VMC_Vertical_Machining_Centre",
    "shoulder_milling":    "VMC_Vertical_Machining_Centre",
    "slot_milling":        "VMC_Vertical_Machining_Centre",
    "angle_milling":       "VMC_Vertical_Machining_Centre",
    "chamfering":          "VMC_Vertical_Machining_Centre",
    "centre_drilling":     "VMC_Vertical_Machining_Centre",
    "drilling":            "VMC_Vertical_Machining_Centre",
    "reaming":             "VMC_Vertical_Machining_Centre",
    "tapping":             "VMC_Vertical_Machining_Centre",
    "thread_rolling":      "Thread_Rolling_Machine"
}

TOOL_ASSIGNMENT = {
    ("rough_turning",       "mild_steel"):        "Carbide_insert_CNMG_432_P25",
    ("rough_turning",       "EN24_alloy_steel"):  "Carbide_insert_CNMG_432_P25",
    ("rough_turning",       "cast_iron"):         "Carbide_insert_CNMG_432_K20",
    ("rough_turning",       "aluminium_6061"):    "Carbide_insert_CCMT_K10",
    ("rough_turning",       "stainless_steel_316"): "Carbide_insert_CNMG_432_M25",
    ("finish_turning",      "mild_steel"):        "Carbide_insert_DCMT_070204_P10",
    ("finish_turning",      "EN24_alloy_steel"):  "Carbide_insert_DCMT_070204_P10",
    ("finish_turning",      "aluminium_6061"):    "Carbide_insert_VCMT_PCD",
    ("finish_turning",      "cast_iron"):         "Carbide_insert_DCMT_K10",
    ("finish_turning",      "stainless_steel_316"): "Carbide_insert_DCMT_M15",
    ("drilling",            "mild_steel"):        "HSS_twist_drill_DIN338",
    ("drilling",            "EN24_alloy_steel"):  "Carbide_tipped_drill",
    ("drilling",            "cast_iron"):         "HSS_twist_drill_DIN338",
    ("drilling",            "aluminium_6061"):    "HSS_drill_bright_finish",
    ("drilling",            "stainless_steel_316"): "Cobalt_HSS_drill",
    ("reaming",             "mild_steel"):        "HSS_reamer",
    ("reaming",             "EN24_alloy_steel"):  "Carbide_reamer",
    ("end_milling_rough",   "mild_steel"):        "Carbide_end_mill_4_flute_TiAlN",
    ("end_milling_finish",  "mild_steel"):        "Carbide_end_mill_4_flute_TiAlN",
    ("end_milling_rough",   "aluminium_6061"):    "Carbide_end_mill_3_flute_uncoated",
    ("end_milling_finish",  "aluminium_6061"):    "Carbide_end_mill_3_flute_uncoated",
    ("face_milling",        "mild_steel"):        "Carbide_face_mill_SNMG_P25",
    ("cylindrical_grinding","mild_steel"):        "Al_oxide_wheel_A60_K5_V",
    ("cylindrical_grinding","EN24_alloy_steel"):  "CBN_wheel_B126_100V",
    ("tapping",             "mild_steel"):        "HSS_tap_with_cutting_oil",
    ("tapping",             "aluminium_6061"):    "HSS_tap_spiral_flute",
}

DEFAULT_TOOL = "Carbide_general_purpose"

CUTTING_PARAMS = {
    ("mild_steel",        "rough_turning"):   {"speed_mpm": "80-120",  "feed_mm_rev": "0.25-0.4",  "doc_mm": "2-5"},
    ("mild_steel",        "finish_turning"):  {"speed_mpm": "150-200", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.2-0.5"},
    ("mild_steel",        "drilling"):        {"speed_mpm": "20-30",   "feed_mm_rev": "0.1-0.25",  "doc_mm": "full_depth"},
    ("mild_steel",        "end_milling_rough"):  {"speed_mpm": "60-100", "feed_mm_rev": "0.05-0.15", "doc_mm": "1-3"},
    ("mild_steel",        "end_milling_finish"): {"speed_mpm": "80-120", "feed_mm_rev": "0.02-0.08", "doc_mm": "0.2-0.5"},
    ("EN24_alloy_steel",  "rough_turning"):   {"speed_mpm": "60-90",   "feed_mm_rev": "0.2-0.35",  "doc_mm": "2-4"},
    ("EN24_alloy_steel",  "finish_turning"):  {"speed_mpm": "100-150", "feed_mm_rev": "0.05-0.12", "doc_mm": "0.2-0.4"},
    ("cast_iron",         "rough_turning"):   {"speed_mpm": "70-100",  "feed_mm_rev": "0.2-0.4",   "doc_mm": "2-5"},
    ("cast_iron",         "finish_turning"):  {"speed_mpm": "120-160", "feed_mm_rev": "0.05-0.12", "doc_mm": "0.2-0.4"},
    ("aluminium_6061",    "rough_turning"):   {"speed_mpm": "200-400", "feed_mm_rev": "0.2-0.4",   "doc_mm": "2-6"},
    ("aluminium_6061",    "finish_turning"):  {"speed_mpm": "300-500", "feed_mm_rev": "0.05-0.15", "doc_mm": "0.1-0.3"},
    ("aluminium_6061",    "drilling"):        {"speed_mpm": "40-80",   "feed_mm_rev": "0.1-0.3",   "doc_mm": "full_depth"},
    ("stainless_steel_316","rough_turning"):  {"speed_mpm": "40-60",   "feed_mm_rev": "0.15-0.25", "doc_mm": "1.5-3"},
    ("stainless_steel_316","finish_turning"): {"speed_mpm": "60-90",   "feed_mm_rev": "0.05-0.12", "doc_mm": "0.1-0.3"},
}

DEFAULT_PARAMS = {"speed_mpm": "refer_handbook", "feed_mm_rev": "refer_handbook", "doc_mm": "refer_handbook"}

TOLERANCE_REQUIREMENTS = {
    "h6": {"mandatory_finish": "cylindrical_grinding", "note": "ISO 286-1: grinding mandatory"},
    "H7": {"mandatory_finish": "reaming",              "note": "ISO 286-1: reaming or fine boring"},
    "H8": {"mandatory_finish": "semi_finish_turning",  "note": "ISO 286-1: fine turning acceptable"},
    "IT9": {"mandatory_finish": None,                  "note": "ISO 286-1: standard turning sufficient"}
}

SURFACE_FINISH_REQUIREMENTS = {
    0.8: "cylindrical_grinding",
    1.6: "finish_turning",
    3.2: "semi_finish_turning",
    6.3: "rough_turning"
}

PART_FEATURE_COMPATIBILITY = {
    "shaft":          [23, 1, 12, 17, 11, 0, 24, 26, 8, 7],
    "flange":         [23, 1, 12, 11, 0, 8, 25, 16],
    "bracket":        [1, 12, 14, 6, 0, 8, 25, 3],
    "coupling":       [23, 1, 12, 17, 25, 0, 11],
    "gear":           [23, 1, 12, 17, 0, 11],
    "bearing_housing":[23, 1, 12, 14, 0, 11, 25, 8],
    "pulley":         [23, 1, 17, 0, 11, 7],
    "cover_plate":    [1, 12, 14, 6, 0, 25, 16, 11],
    "bushing":        [23, 1, 11, 0, 17, 8],
    "connecting_rod": [1, 12, 14, 0, 25, 8]
}

SEQUENCING_PRIORITY = {
    "centre_drilling":    1,
    "facing":             1,
    "rough_turning":      2,
    "rough_boring":       2,
    "drilling":           3,
    "semi_finish_turning":4,
    "boring":             5,
    "end_milling_rough":  5,
    "slot_milling":       6,
    "face_milling":       6,
    "shoulder_milling":   6,
    "angle_milling":      6,
    "taper_turning":      7,
    "grooving_turning":   7,
    "finish_turning":     8,
    "end_milling_finish": 8,
    "reaming":            9,
    "thread_turning":     9,
    "tapping":            9,
    "thread_rolling":     9,
    "cylindrical_grinding":10,
    "internal_grinding":  10,
    "chamfering":         11,
    "deburring":          12
}
