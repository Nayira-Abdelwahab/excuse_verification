"""Step 2: Scan metadata for AI tools and image-editing software."""

import re

from PIL import Image
from pypdf import PdfReader

AI_TOOLS = [
    "midjourney",
    "dall-e",
    "dalle",
    "stable diffusion",
    "stablediffusion",
    "firefly",
    "openai",
    "chatgpt",
    "gpt-image",
    "gpt-4o",
    "sora",
    "gemini",
    "nano banana",
    "imagen",
    "leonardo.ai",
    "ideogram",
    "flux",
    "copilot designer",
    "bing image creator",
    "trainedalgorithmicmedia",
]

EDIT_TOOLS = [
    "photoshop",
    "canva",
    "gimp",
    "pixlr",
    "picsart",
    "snapseed",
    "lightroom",
    "affinity photo",
]


def _compile(keywords):
    # حدود كلمات حتى لا تطابق "flux" داخل كلمة مثل "influx"
    return [
        (keyword, re.compile(
            r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
        ))
        for keyword in keywords
    ]


_AI_PATTERNS = _compile(AI_TOOLS)
_EDIT_PATTERNS = _compile(EDIT_TOOLS)


def _scan(text: str):
    text = text.lower()

    ai_matches = [k for k, p in _AI_PATTERNS if p.search(text)]
    edit_matches = [k for k, p in _EDIT_PATTERNS if p.search(text)]

    return ai_matches, edit_matches


def check_metadata(path: str, kind: str) -> dict:

    fields = {}

    try:
        if kind == "image":

            with Image.open(path) as img:

                for key, value in img.getexif().items():
                    fields[f"exif_{key}"] = str(value)

                # Read image information, PNG text chunks and XMP
                for key, value in (img.info or {}).items():

                    if isinstance(value, bytes):
                        fields[str(key)] = value.decode("utf-8", "ignore")

                    elif isinstance(value, str):
                        fields[str(key)] = value

        elif kind == "pdf":

            reader = PdfReader(path)

            for key, value in (reader.metadata or {}).items():
                fields[str(key)] = str(value)

            # XMP metadata (غالباً يحتوي على الأداة المنتجة للملف)
            try:
                xmp = reader.xmp_metadata

                if xmp is not None:
                    for attr in (
                        "pdf_producer",
                        "xmp_creator_tool",
                        "dc_creator",
                        "dc_title",
                    ):
                        value = getattr(xmp, attr, None)

                        if value:
                            fields[f"xmp_{attr}"] = str(value)

            except Exception:
                pass

    except Exception as error:

        return {
            "fields": {},
            "ai_hits": [],
            "edit_hits": [],
            "error": str(error)
        }

    metadata_text = " ".join(fields.values())

    ai_matches, edit_matches = _scan(metadata_text)

    return {
        "fields": fields,
        "ai_hits": ai_matches,
        "edit_hits": edit_matches,
        "error": None
    }