
"""Step 1: Detect file type using file signatures, not just the extension."""

from pathlib import Path

SIGNATURES = {
    b"%PDF": "pdf",
    b"\xff\xd8\xff": "image",       # JPEG
    b"\x89PNG\r\n\x1a\n": "image",  # PNG
    b"RIFF": "image",               # WEBP (approximate detection)
}


def detect_type(path: str) -> dict:
    file_path = Path(path)

    with open(file_path, "rb") as file:
        header = file.read(16)

    real_type = "unknown"

    for signature, kind in SIGNATURES.items():
        if header.startswith(signature):
            real_type = kind
            break

    extension = file_path.suffix.lower()

    extension_type = (
        "pdf" if extension == ".pdf"
        else "image" if extension in (".jpg", ".jpeg", ".png", ".webp")
        else "unknown"
    )

    return {
        "type": real_type,
        "extension_mismatch": (
            real_type != "unknown" and extension_type != real_type
        ),
    }


def pdf_to_images(path: str, dpi: int = 200):
    """Convert PDF pages into images. Requires Poppler on Windows."""

    try:
        from pdf2image import convert_from_path

        return convert_from_path(path, dpi=dpi), None

    except Exception as error:
        return [], f"Failed to convert PDF to images: {error}"
