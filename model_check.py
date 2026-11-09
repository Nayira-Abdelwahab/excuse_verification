
"""AI-generated image detection using Smaug."""

import sys
from functools import lru_cache
from huggingface_hub import snapshot_download


MODEL_ID = "abacusai/Smaug-AI-Image-Detector"


@lru_cache(maxsize=1)
def load_detector():
    """Download and load the detector once."""

    model_path = snapshot_download(MODEL_ID)

    if model_path not in sys.path:
        sys.path.insert(0, model_path)

    from smaug_image_detect import SmaugImageDetect

    return SmaugImageDetect.from_pretrained(model_path)


def check_ai_image(image_path: str) -> dict:
    """Return the model's estimated AI-generation probability."""

    try:
        detector = load_detector()
        probability = float(detector(image_path))

        return {
            "available": True,
            "ai_probability": probability,
            "error": None
        }

    except Exception as error:
        return {
            "available": False,
            "ai_probability": None,
            "error": str(error)
        }
