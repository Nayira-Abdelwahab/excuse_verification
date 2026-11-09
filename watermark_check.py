
"""Check for invisible watermarks compatible with the invisible-watermark library."""

def check_invisible_watermark(img) -> dict:

    try:
        import cv2
        import numpy as np
        from imwatermark import WatermarkDecoder

    except ImportError:
        return {
            "available": False,
            "found": None,
            "note": "Watermark or OpenCV library is not available"
        }

    known_marks = [
        "StableDiffusionV1",
        "SDV2"
    ]

    try:
        rgb = np.array(img.convert("RGB"))

        bgr = cv2.cvtColor(
            rgb,
            cv2.COLOR_RGB2BGR
        )

        for mark in known_marks:

            nbits = len(mark.encode("utf-8")) * 8

            decoder = WatermarkDecoder(
                "bytes",
                nbits
            )

            result = decoder.decode(
                bgr,
                "dwtDct"
            )

            try:
                decoded = result.decode("utf-8").strip()

                if decoded == mark:
                    return {
                        "available": True,
                        "found": True,
                        "note": f"Known watermark detected: {mark}"
                    }

            except UnicodeDecodeError:
                continue

        return {
            "available": True,
            "found": False,
            "note": "None of the specific watermarks checked by the program were detected"
        }

    except Exception as error:
        return {
            "available": True,
            "found": None,
            "note": f"Watermark check failed: {error}"
        }
