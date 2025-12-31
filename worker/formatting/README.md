# Format-Only DOCX Processing

## Overview

The format-only mode provides deterministic DOCX formatting that **preserves all text content exactly** while applying consistent formatting properties (margins, fonts, spacing, etc.).

## Format-Only Promise

**Guarantee**: Text content is never modified. Only formatting properties are changed:
- ✅ Margins and page size
- ✅ Font names and sizes
- ✅ Line spacing and paragraph spacing
- ✅ Style normalization (for headings that already use heading styles)

**Never changes**:
- ❌ Text content
- ❌ Paragraph order
- ❌ Paragraph count
- ❌ Table structure or content

## How It Works

1. **Input**: Original DOCX file (bytes)
2. **Processing**: Apply formatting profile to all sections and paragraphs
3. **Output**: Formatted DOCX (bytes) + extracted plain text

The formatter:
- Extracts text BEFORE formatting (to verify preservation)
- Applies formatting profile to sections, paragraphs, and tables
- Verifies text content is unchanged after formatting
- Returns formatted DOCX bytes and extracted text

## Format Profiles

### Standard Clean Profile

The `standard_clean` profile applies:
- **Page**: A4 (21.0cm × 29.7cm)
- **Margins**: 2.54cm on all sides
- **Normal Style Font**: Calibri 11pt
- **Line Spacing**: 1.15
- **Paragraph Spacing**: 0pt before, 6pt after

### Compact Clean Profile

The `compact_clean` profile applies:
- **Page**: A4 (21.0cm × 29.7cm)
- **Margins**: 2.0cm on all sides
- **Normal Style Font**: Calibri 11pt
- **Line Spacing**: 1.0
- **Paragraph Spacing**: 0pt before, 4pt after

### Adding New Profiles

To add a new format profile:

1. Edit `format_profiles.py`
2. Create a new `FormatProfile` instance:

```python
MY_PROFILE = FormatProfile(
    name="my_profile",
    page_width=Cm(21.0),
    page_height=Cm(29.7),
    margins={
        'top': Cm(2.54),
        'bottom': Cm(2.54),
        'left': Cm(2.54),
        'right': Cm(2.54)
    },
    normal_font_name="Calibri",
    normal_font_size=Pt(11),
    line_spacing=1.15,
    paragraph_spacing_before=Pt(0),
    paragraph_spacing_after=Pt(6)
)
```

3. Add to `PROFILES` registry:

```python
PROFILES = {
    "standard_clean": STANDARD_CLEAN,
    "my_profile": MY_PROFILE
}
```

## Worker Integration

The worker chooses mode and style based on job fields:

### Job Fields

- `mode`: Processing mode
  - `"format_only"` (default): Format-only processing
  - Other values: Legacy text formatting mode
  
- `style` or `profile`: Format profile name
  - `"standard_clean"` (default): Standard clean profile
  - Any profile name from `PROFILES` registry

### Default Behavior

If `mode` or `style`/`profile` are missing from the job:
- `mode` defaults to `"format_only"`
- `style`/`profile` defaults to `"standard_clean"`

This ensures backward compatibility with existing jobs.

### Example Job Document

```json
{
  "doc_id": "uuid",
  "storage_path": "gs://bucket/input.docx",
  "mode": "format_only",
  "style": "standard_clean",
  "state": "QUEUED"
}
```

## Testing

Run tests with:

```bash
cd worker
python -m unittest formatting.test_formatter
```

Tests verify:
- Text content is preserved exactly
- Section margins match profile
- Normal style font matches profile
- Paragraph spacing matches profile
- Line spacing matches profile
- Multiple paragraphs are preserved
- Empty documents are handled
- Tables are formatted correctly

## Architecture

```
formatting/
├── __init__.py           # Module init
├── format_profiles.py    # Profile definitions
├── formatter_engine.py   # Main formatting logic
├── docx_utils.py         # DOCX helper functions
├── test_formatter.py     # Unit tests
└── README.md             # This file
```

## Usage Example

```python
from formatting.formatter_engine import apply_format_only

# Load DOCX bytes
with open('input.docx', 'rb') as f:
    input_bytes = f.read()

# Apply formatting
formatted_bytes, extracted_text = apply_format_only(
    input_bytes, 
    profile_name="standard_clean"
)

# Save formatted DOCX
with open('output.docx', 'wb') as f:
    f.write(formatted_bytes)
```

