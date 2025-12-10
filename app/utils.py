import re
import unicodedata
from typing import Optional

def sanitize_filename(filename: str, replace_char: str = "_") -> str:
    """Sanitize a filename for safe S3 keys and storage.

    - Normalizes unicode characters to ASCII when possible.
    - Removes path separators and control characters.
    - Replaces sequences of invalid characters with `replace_char`.
    - Keeps the file extension (if present) and sanitizes the name portion.

    Examples:
        "../evil/fi l e.png" -> "fi_l_e.png"
        "café.jpg" -> "cafe.jpg"
    """
    if not filename:
        return "unnamed"

    # strip surrounding whitespace and control chars
    filename = filename.strip()

    # Split extension
    parts = filename.rsplit('.', 1)
    name = parts[0]
    ext: Optional[str] = None
    if len(parts) == 2:
        ext = parts[1]

    # Normalize unicode to ASCII
    name = unicodedata.normalize('NFKD', name)
    name = name.encode('ascii', 'ignore').decode('ascii')

    # Remove path separators and null bytes
    name = name.replace('/', ' ').replace('\\', ' ')
    name = name.replace('\x00', '')

    # Replace any character that is not alphanumeric, dot, underscore or hyphen with separator
    # We already removed the dot for extension handling, so allow only [A-Za-z0-9._-]
    name = re.sub(r'[^A-Za-z0-9._-]+', replace_char, name)

    # collapse repeated separators
    name = re.sub(rf'{re.escape(replace_char)}{{2,}}', replace_char, name)

    # strip leading/trailing separators or dots
    name = name.strip(' ._-')

    if not name:
        name = 'file'

    if ext:
        # sanitize extension too
        ext = re.sub(r'[^A-Za-z0-9]+', '', ext)
        if ext:
            return f"{name}.{ext}"
    return name
