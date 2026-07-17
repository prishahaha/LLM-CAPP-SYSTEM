"""
Feature vocabulary sourced from FeatureNet dataset.
Zhang et al., Computer-Aided Design, Vol.101, 2018.
DOI: 10.1016/j.cad.2018.01.001
GitHub: https://github.com/madlabub/Machining-feature-dataset
"""

FEATURENET_24_CLASSES = {
    0: "chamfer",
    1: "through_hole",
    2: "triangular_passage",
    3: "rectangular_passage",
    4: "six_sided_passage",
    5: "triangular_through_slot",
    6: "rectangular_through_slot",
    7: "circular_through_slot",
    8: "rectangular_through_step",
    9: "two_sided_through_step",
    10: "slanted_through_step",
    11: "O_ring_groove",
    12: "blind_hole",
    13: "triangular_pocket",
    14: "rectangular_pocket",
    15: "six_sided_pocket",
    16: "circular_end_pocket",
    17: "rectangular_blind_slot",
    18: "vertical_circular_end_blind_slot",
    19: "horizontal_circular_end_blind_slot",
    20: "triangular_blind_step",
    21: "circular_blind_step",
    22: "rectangular_blind_step",
    23: "round_external_cylinder"
}

SUPPLEMENTARY_FEATURES = {
    24: "thread_external",
    25: "thread_internal",
    26: "taper"
}

ALL_FEATURES = {**FEATURENET_24_CLASSES, **SUPPLEMENTARY_FEATURES}
