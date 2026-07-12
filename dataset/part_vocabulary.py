"""
Part type vocabulary based on MechCAD dataset (10 mechanical part classes from a
B-rep classification dataset used as the source of part-type taxonomy for this
project).

NOTE ON PROVENANCE: verify the exact MechCAD citation (authors, venue, model
count) against the primary source before using this attribution in a journal
submission — this project uses the class taxonomy only, not the underlying
B-rep models.
"""

MECHCAD_PART_CLASSES = [
    "shaft",  # rotating cylindrical parts, journals, steps
    "flange",  # disc-type parts with bolt hole pattern
    "bracket",  # structural support with mounting holes
    "coupling",  # connects two shafts, may have keyways and bores
    "gear",  # gear blank before tooth cutting, hub and bore
    "bearing_housing",  # cylindrical housing with precision bore
    "pulley",  # disc with hub bore and groove
    "cover_plate",  # flat plate with hole pattern and sealing features
    "bushing",  # cylindrical sleeve with internal and external cylinder
    "connecting_rod",  # reciprocating part with two bores
]

PART_CLASS_DESCRIPTIONS = {
    "shaft": "rotating cylindrical parts, journals, steps",
    "flange": "disc-type parts with bolt hole pattern",
    "bracket": "structural support with mounting holes",
    "coupling": "connects two shafts, may have keyways and bores",
    "gear": "gear blank before tooth cutting, hub and bore",
    "bearing_housing": "cylindrical housing with precision bore",
    "pulley": "disc with hub bore and groove",
    "cover_plate": "flat plate with hole pattern and sealing features",
    "bushing": "cylindrical sleeve with internal and external cylinder",
    "connecting_rod": "reciprocating part with two bores",
}

PART_VOCABULARY_SOURCE = (
    "Part type vocabulary based on MechCAD dataset "
    "(10 mechanical part classes from a B-rep classification dataset)"
)
