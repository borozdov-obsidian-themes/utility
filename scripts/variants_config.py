"""Which sibling themes become Style Settings variants of this one."""

ID = "borozdov-utility"  # Style Settings section id and the body-class prefix
NAME = "Borozdov Utility"
DEFAULT_LABEL = "Utility"

# (repository folder next to this one, label in the Variant menu)
MEMBERS = [
    ("compositor", "Compositor"),
    ("beaker", "Beaker"),
    ("ledger", "Ledger"),
    ("wire", "Wire"),
    ("clinic", "Clinic"),
    ("tracing", "Tracing"),
    ("easel", "Easel"),
    ("marble", "Marble"),
    ("tessera", "Tessera"),
    ("keynote", "Keynote"),
    ("cobalt", "Cobalt"),
    ("flint", "Flint"),
    ("porcelain", "Porcelain"),
    ("alpine", "Alpine"),
    ("archive", "Archive"),
    ("grayscale", "Grayscale"),
    ("specimen", "Specimen"),
    ("vial", "Vial"),
    ("pixel", "Pixel"),
    ("blueline", "Blueline"),
]

# Palette names of this theme that no Obsidian variable reads in section 3:
# which of the sibling's resolved variables to take for them instead.
ALIASES = {
    "--panel": "--background-primary",
}

# The palette name the highlight rule colours its text with: the generator
# picks whichever of the sibling's text and canvas reads on its highlight.
MARK_TEXT = "--on-mark"
