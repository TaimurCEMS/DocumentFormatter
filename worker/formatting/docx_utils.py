"""Utility functions for DOCX manipulation."""

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn
import io


def set_section_margins(section, margins):
    """Set margins for a document section.
    
    Args:
        section: docx.section.Section object
        margins: dict with 'top', 'bottom', 'left', 'right' as cm floats
    """
    section.top_margin = Cm(margins['top'])
    section.bottom_margin = Cm(margins['bottom'])
    section.left_margin = Cm(margins['left'])
    section.right_margin = Cm(margins['right'])


def set_page_size(section, width, height):
    """Set page size for a document section.
    
    Args:
        section: docx.section.Section object
        width: page width (e.g., Cm(21.0))
        height: page height (e.g., Cm(29.7))
    """
    section.page_width = width
    section.page_height = height


def apply_normal_style(paragraph, font_name, font_size, line_spacing, 
                       spacing_before, spacing_after):
    """Apply formatting to a paragraph's Normal style.
    
    Args:
        paragraph: docx.text.paragraph.Paragraph
        font_name: str (e.g., "Calibri")
        font_size: Pt value
        line_spacing: float (e.g., 1.15)
        spacing_before: Pt value
        spacing_after: Pt value
    """
    # Set paragraph spacing
    paragraph_format = paragraph.paragraph_format
    paragraph_format.space_before = spacing_before
    paragraph_format.space_after = spacing_after
    paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    paragraph_format.line_spacing = line_spacing
    
    # Apply font to all runs in the paragraph
    # Use OXML to ensure font is properly serialized (rFonts with ascii, hAnsi, eastAsia, cs)
    for run in paragraph.runs:
        run.font.name = font_name
        run.font.size = font_size
        
        # Force font serialization via OXML
        rPr = run._element.get_or_add_rPr()
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = rPr.makeelement(qn('w:rFonts'))
            rPr.append(rFonts)
        rFonts.set(qn('w:ascii'), font_name)
        rFonts.set(qn('w:hAnsi'), font_name)
        rFonts.set(qn('w:eastAsia'), font_name)
        rFonts.set(qn('w:cs'), font_name)
        
        # Set font size via OXML (convert Pt to half-points)
        sz = rPr.find(qn('w:sz'))
        if sz is None:
            sz = rPr.makeelement(qn('w:sz'))
            rPr.append(sz)
        # font_size is a Pt object, convert to half-points
        half_points = int(font_size.pt * 2)
        sz.set(qn('w:val'), str(half_points))
        
        # Set complex script size
        szCs = rPr.find(qn('w:szCs'))
        if szCs is None:
            szCs = rPr.makeelement(qn('w:szCs'))
            rPr.append(szCs)
        szCs.set(qn('w:val'), str(half_points))


def update_normal_style_definition(document, font_name, font_size, line_spacing,
                                   spacing_before, spacing_after):
    """Update the Normal style definition in the document styles.
    
    Args:
        document: docx.Document
        font_name: str (e.g., "Calibri")
        font_size: Pt value
        line_spacing: float (e.g., 1.0)
        spacing_before: Pt value
        spacing_after: Pt value
    """
    styles = document.styles
    if 'Normal' not in styles:
        return
    
    normal_style = styles['Normal']
    
    # Update font in style definition
    try:
        font = normal_style.font
        font.name = font_name
        font.size = font_size
        
        # Force font serialization via OXML
        style_element = normal_style._element
        rPr = style_element.find(qn('w:rPr'))
        if rPr is None:
            rPr = style_element.makeelement(qn('w:rPr'))
            style_element.append(rPr)
        
        rFonts = rPr.find(qn('w:rFonts'))
        if rFonts is None:
            rFonts = rPr.makeelement(qn('w:rFonts'))
            rPr.append(rFonts)
        rFonts.set(qn('w:ascii'), font_name)
        rFonts.set(qn('w:hAnsi'), font_name)
        rFonts.set(qn('w:eastAsia'), font_name)
        rFonts.set(qn('w:cs'), font_name)
        
        # Set font size (convert Pt to half-points: 11pt = 22 half-points)
        sz = rPr.find(qn('w:sz'))
        if sz is None:
            sz = rPr.makeelement(qn('w:sz'))
            rPr.append(sz)
        # font_size is a Pt object, convert to half-points
        half_points = int(font_size.pt * 2)
        sz.set(qn('w:val'), str(half_points))
        
        szCs = rPr.find(qn('w:szCs'))
        if szCs is None:
            szCs = rPr.makeelement(qn('w:szCs'))
            rPr.append(szCs)
        szCs.set(qn('w:val'), str(half_points))
    except Exception as e:
        print(f"Warning: Could not update Normal style font: {e}")
    
    # Update paragraph format in style definition
    try:
        pPr = normal_style._element.find(qn('w:pPr'))
        if pPr is None:
            pPr = normal_style._element.makeelement(qn('w:pPr'))
            normal_style._element.insert(0, pPr)
        
        # Set spacing
        spacing = pPr.find(qn('w:spacing'))
        if spacing is None:
            spacing = pPr.makeelement(qn('w:spacing'))
            pPr.append(spacing)
        
        # Convert Pt to twips (1 pt = 20 twips)
        # spacing_before and spacing_after are Pt objects
        spacing.set(qn('w:before'), str(int(spacing_before.pt * 20)))
        spacing.set(qn('w:after'), str(int(spacing_after.pt * 20)))
        
        # Set line spacing (1.0 = single, stored as 240 twips per line)
        if line_spacing == 1.0:
            spacing.set(qn('w:line'), '240')
            spacing.set(qn('w:lineRule'), 'auto')
        else:
            # Multiple line spacing
            spacing.set(qn('w:line'), str(int(line_spacing * 240)))
            spacing.set(qn('w:lineRule'), 'auto')
    except Exception as e:
        print(f"Warning: Could not update Normal style paragraph format: {e}")


def normalize_heading_styles(document):
    """Normalize Heading 1, 2, 3 styles if paragraphs already use them.
    Only modifies paragraphs that already have heading styles.
    
    Args:
        document: docx.Document
    """
    # Get heading styles from document
    styles = document.styles
    
    # Normalize Heading 1, 2, 3 if they exist
    for level in [1, 2, 3]:
        style_name = f'Heading {level}'
        if style_name in styles:
            heading_style = styles[style_name]
            # Set consistent font (Calibri 11 for headings too, or keep existing)
            # Only normalize if paragraph already uses this style
            pass  # For now, we preserve existing heading styles


def extract_plain_text(document):
    """Extract plain text from a document, preserving paragraph structure.
    
    Args:
        document: docx.Document
        
    Returns:
        str: Plain text with newlines between paragraphs
    """
    paragraphs = []
    for para in document.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return '\n'.join(paragraphs)


def docx_to_bytes(document):
    """Convert a Document to bytes.
    
    Args:
        document: docx.Document
        
    Returns:
        bytes: DOCX file content
    """
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def bytes_to_docx(docx_bytes):
    """Load a Document from bytes.
    
    Args:
        docx_bytes: bytes
        
    Returns:
        docx.Document
    """
    buffer = io.BytesIO(docx_bytes)
    return Document(buffer)

