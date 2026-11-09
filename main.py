
"""
Usage:
    python main.py excuse.pdf --student 12345
    python main.py excuse.jpg --student 12345 --absence 2026-11-02
    python main.py --folder uploads --student 12345
"""

import argparse
import json
import os
import tempfile
from datetime import date

from PIL import Image

from file_type import detect_type, pdf_to_images
from metadata_check import check_metadata
from c2pa_check import check_c2pa
from watermark_check import check_invisible_watermark
from duplicates import check_duplicates
from ocr_check import ocr_images, analyze_text
from model_check import check_ai_image
from scoring import score


def run_ai_model(path, kind, images):
    """Run the AI detector on an image or every PDF page."""

    if not images:
        return {
            "available": False,
            "ai_probability": None,
            "page_probabilities": [],
            "error": "No image available for AI detection"
        }

    probabilities = []
    errors = []

    try:
        if kind == "image":
            result = check_ai_image(path)

            if result.get("available") and result.get("ai_probability") is not None:
                probabilities.append(float(result["ai_probability"]))
            else:
                errors.append(result.get("error") or "AI detection failed")

        elif kind == "pdf":
            with tempfile.TemporaryDirectory() as temp_dir:

                for index, page in enumerate(images):
                    page_path = os.path.join(
                        temp_dir,
                        f"page_{index + 1}.jpg"
                    )

                    page.convert("RGB").save(
                        page_path,
                        format="JPEG"
                    )

                    result = check_ai_image(page_path)

                    if (
                        result.get("available")
                        and result.get("ai_probability") is not None
                    ):
                        probabilities.append(
                            float(result["ai_probability"])
                        )
                    else:
                        errors.append(
                            f"Page {index + 1}: "
                            f"{result.get('error') or 'AI detection failed'}"
                        )

        else:
            errors.append("Unsupported file type for AI detection")

    except Exception as error:
        errors.append(str(error))

    if probabilities:
        return {
            "available": True,
            "ai_probability": max(probabilities),
            "page_probabilities": probabilities,
            "error": "; ".join(errors) if errors else None
        }

    return {
        "available": False,
        "ai_probability": None,
        "page_probabilities": [],
        "error": "; ".join(errors) if errors else "AI detection failed"
    }


def analyze_file(
    path: str,
    student_id: str,
    absence_date=None,
    ocr_lang="ara+eng"
) -> dict:

    file_type = detect_type(path)
    kind = file_type["type"]
    errors = []
    images = []

    # 1. Read file
    try:
        if kind == "pdf":
            images, error = pdf_to_images(path)

            if error:
                errors.append(error)

        elif kind == "image":
            with Image.open(path) as img:
                images = [img.convert("RGB").copy()]

        else:
            errors.append("Unsupported file type")

    except Exception as error:
        errors.append(f"Failed to open file: {error}")

    first_image = images[0] if images else None

    # 2. AI image detection model
    ai_model_result = run_ai_model(path, kind, images)

    if not ai_model_result.get("available"):
        errors.append(
            "AI model check failed: "
            + str(ai_model_result.get("error"))
        )
    elif ai_model_result.get("error"):
        errors.append(
            "Some AI model checks failed: "
            + str(ai_model_result["error"])
        )

    # 3. Metadata check
    try:
        metadata = (
            check_metadata(path, kind)
            if kind in ("image", "pdf")
            else {
                "fields": {},
                "ai_hits": [],
                "edit_hits": []
            }
        )

    except Exception as error:
        metadata = {
            "fields": {},
            "ai_hits": [],
            "edit_hits": [],
            "note": f"Metadata check failed: {error}"
        }
        errors.append(metadata["note"])

    # 4. C2PA check
    try:
        c2pa_result = (
            check_c2pa(path)
            if kind in ("image", "pdf")
            else {
                "available": False,
                "found": None,
                "ai": None,
                "note": "Unsupported file type for C2PA check"
            }
        )

    except Exception as error:
        c2pa_result = {
            "available": True,
            "found": None,
            "ai": None,
            "note": f"C2PA check failed: {error}"
        }
        errors.append(c2pa_result["note"])

    # 5. Invisible watermark check
    try:
        watermark_result = (
            check_invisible_watermark(first_image)
            if first_image is not None
            else {
                "available": False,
                "found": None,
                "note": "Watermark check skipped because no image is available"
            }
        )

    except Exception as error:
        watermark_result = {
            "available": True,
            "found": None,
            "note": f"Watermark check failed: {error}"
        }
        errors.append(watermark_result["note"])

    # 6. Duplicate check
    try:
        duplicate_result = check_duplicates(
            path,
            first_image,
            student_id
        )

    except Exception as error:
        duplicate_result = {
            "matches": [],
            "note": f"Duplicate check failed: {error}"
        }
        errors.append(duplicate_result["note"])

    # 7. OCR check
    try:
        text, ocr_error = (
            ocr_images(images, ocr_lang)
            if images
            else ("", "No readable content found")
        )

        if ocr_error:
            errors.append(ocr_error)

        text_result = (
            analyze_text(text, absence_date)
            if images
            else {
                "dates": [],
                "license": None,
                "doctor": None,
                "issues": ["No content available"]
            }
        )

    except Exception as error:
        text_result = {
            "dates": [],
            "license": None,
            "doctor": None,
            "issues": ["Text extraction failed"]
        }
        errors.append(f"OCR error: {error}")

    # 8. Collect report
    report = {
        "file": os.path.basename(path),
        "student_id": student_id,
        "file_type": file_type,
        "ai_model": ai_model_result,
        "metadata": metadata,
        "c2pa": c2pa_result,
        "watermark": watermark_result,
        "duplicates": duplicate_result,
        "text": text_result,
        "errors": errors
    }

    # 9. Calculate final result
    report["score"] = score(report)

    return report


def print_report(report):

    print("=" * 60)

    print(
        f"File: {report['file']} | "
        f"Student: {report['student_id']}"
    )

    print(f"Detected file type: {report['file_type']['type']}")

    # AI model result
    model = report.get("ai_model", {})

    print("\nAI Model:")

    if model.get("available"):
        probability = model.get("ai_probability")

        if probability is not None:
            print(f"AI probability: {probability:.2%}")

        for index, page_probability in enumerate(
            model.get("page_probabilities", []),
            start=1
        ):
            print(f"Page {index}: {page_probability:.2%}")

    else:
        print(f"Unavailable: {model.get('error')}")

    print(f"\nC2PA: {report['c2pa'].get('note', '-')}")
    print(f"Watermark: {report['watermark'].get('note', '-')}")

    print(
        f"Metadata AI: {report['metadata'].get('ai_hits', []) or 'None'}"
        f" | Editing: {report['metadata'].get('edit_hits', []) or 'None'}"
    )

    if report["duplicates"].get("matches"):
        print(f"Duplicate matches: {report['duplicates']['matches']}")

    text_result = report["text"]

    print(
        f"Text: Dates={text_result.get('dates', [])} "
        f"Doctor={text_result.get('doctor')} "
        f"License={text_result.get('license')}"
    )

    for issue in text_result.get("issues", []):
        print(f"  - {issue}")

    for error in report.get("errors", []):
        print(f"  [Warning] {error}")

    result = report["score"]

    for reason in result.get("reasons", []):
        print(f"  * {reason}")

    for note in result.get("review_notes", []):
        print(f"  [Review note] {note}")

    print(f"\nFinal result: {result['verdict']}")

    print("(This result is a technical indicator, not a final judgment.)")


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("path", nargs="?")
    parser.add_argument("--folder")
    parser.add_argument("--student", default="unknown")
    parser.add_argument("--absence", help="YYYY-MM-DD")
    parser.add_argument("--json", action="store_true")

    args = parser.parse_args()

    try:
        absence_date = (
            date.fromisoformat(args.absence)
            if args.absence else None
        )

    except ValueError:
        parser.error("Invalid absence date. Use YYYY-MM-DD.")

    files = []

    if args.folder:

        if not os.path.isdir(args.folder):
            parser.error("Folder does not exist")

        files = [
            os.path.join(args.folder, filename)
            for filename in sorted(os.listdir(args.folder))
            if os.path.isfile(os.path.join(args.folder, filename))
        ]

    elif args.path:
        files = [args.path]

    else:
        parser.error("You must specify a file or --folder")

    for file_path in files:

        if not os.path.isfile(file_path):
            print(f"[Warning] File not found: {file_path}")
            continue

        student_id = (
            args.student
            if args.folder is None
            else os.path.splitext(os.path.basename(file_path))[0]
        )

        try:
            report = analyze_file(
                file_path,
                student_id,
                absence_date
            )

            if args.json:
                print(json.dumps(
                    report,
                    ensure_ascii=False,
                    indent=2,
                    default=str
                ))

            else:
                print_report(report)

        except Exception as error:
            print(f"[Error] Failed to analyze {file_path}: {error}")


if __name__ == "__main__":
    main()
