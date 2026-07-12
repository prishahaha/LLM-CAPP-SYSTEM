"""
Feature vocabulary sourced from FeatureNet dataset (Zhang et al., Computer-Aided Design,
Vol.101, 2018, Elsevier). DOI: 10.1016/j.cad.2018.01.001

FeatureNet defines 24 machining feature classes used to benchmark 3D-CNN-based
machining feature recognition. Classes 0-23 below reproduce that vocabulary
exactly (class index -> class name).

Three supplementary feature classes (24-26) are added because they are required
for a complete CAPP process-planning vocabulary (threads, tapers) but are not
present in FeatureNet's 24 classes. These are sourced from the MFCAD++ dataset
(Colligan et al., "Hierarchical CADNet: Learning from B-Reps for Machining
Feature Recognition", Computer-Aided Design, 2022).

NOTE ON PROVENANCE: classes 0-23 are the published FeatureNet taxonomy and can
be cited directly. Classes 24-26 are supplementary additions for this project's
process-planning scope and should be cited as such (not as FeatureNet classes)
in any downstream publication.
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
    23: "round_external_cylinder",
}

SUPPLEMENTARY_FEATURES = {
    24: "thread_external",
    25: "thread_internal",
    26: "taper",
}

# Combined vocabulary: id -> feature name (0-23 FeatureNet, 24-26 supplementary)
FEATURE_VOCABULARY = {**FEATURENET_24_CLASSES, **SUPPLEMENTARY_FEATURES}

# Reverse lookup: feature name -> id
FEATURE_NAME_TO_ID = {name: fid for fid, name in FEATURE_VOCABULARY.items()}

FEATURE_SOURCE_CITATION = {
    "featurenet_classes": {
        "ids": list(FEATURENET_24_CLASSES.keys()),
        "source": "FeatureNet dataset, Zhang et al., Computer-Aided Design, "
        "Vol.101, 2018, Elsevier. DOI: 10.1016/j.cad.2018.01.001",
    },
    "supplementary_classes": {
        "ids": list(SUPPLEMENTARY_FEATURES.keys()),
        "source": "MFCAD++ dataset, Colligan et al., 2022 "
        "(Hierarchical CADNet: Learning from B-Reps for Machining Feature Recognition, "
        "Computer-Aided Design)",
    },
}


def feature_source(feature_name: str) -> str:
    """Return the citation string for a given feature name."""
    fid = FEATURE_NAME_TO_ID[feature_name]
    if fid <= 23:
        return f"FeatureNet class {fid}, Zhang et al. 2018"
    return f"MFCAD++ supplementary class {fid}, Colligan et al. 2022"
