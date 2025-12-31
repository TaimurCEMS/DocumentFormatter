"""Formatting profiles for DOCX format-only mode."""

from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_LINE_SPACING


class FormatProfile:
    """Defines formatting settings for a document."""
    
    def __init__(self, name, page_width, page_height, margins, normal_font_name, 
                 normal_font_size, line_spacing, paragraph_spacing_before, 
                 paragraph_spacing_after):
        self.name = name
        self.page_width = page_width
        self.page_height = page_height
        self.margins = margins  # dict with 'top', 'bottom', 'left', 'right' as cm floats
        self.normal_font_name = normal_font_name
        self.normal_font_size = normal_font_size
        self.line_spacing = line_spacing
        self.paragraph_spacing_before = paragraph_spacing_before
        self.paragraph_spacing_after = paragraph_spacing_after


# Standard clean profile: A4, 2.54cm margins, Calibri 11, 1.15 line spacing
STANDARD_CLEAN = FormatProfile(
    name="standard_clean",
    page_width=Cm(21.0),  # A4 width
    page_height=Cm(29.7),  # A4 height
    margins={
        'top': 2.54,  # cm as float
        'bottom': 2.54,
        'left': 2.54,
        'right': 2.54
    },
    normal_font_name="Calibri",
    normal_font_size=Pt(11),
    line_spacing=1.15,  # 1.15 line spacing
    paragraph_spacing_before=Pt(0),
    paragraph_spacing_after=Pt(6)
)

# Compact clean profile: A4, 2.0cm margins, Calibri 11, 1.0 line spacing
COMPACT_CLEAN = FormatProfile(
    name="compact_clean",
    page_width=Cm(21.0),  # A4 width
    page_height=Cm(29.7),  # A4 height
    margins={
        'top': 2.0,  # cm as float
        'bottom': 2.0,
        'left': 2.0,
        'right': 2.0
    },
    normal_font_name="Calibri",
    normal_font_size=Pt(11),
    line_spacing=1.0,  # 1.0 line spacing
    paragraph_spacing_before=Pt(0),
    paragraph_spacing_after=Pt(4)
)


# Registry of available profiles
PROFILES = {
    "standard_clean": STANDARD_CLEAN,
    "compact_clean": COMPACT_CLEAN
}


def get_profile(profile_name: str) -> FormatProfile:
    """Get a format profile by name. Returns standard_clean if not found."""
    return PROFILES.get(profile_name, STANDARD_CLEAN)

