

"""System for combining AI image detection indicators."""

MODEL_AI_THRESHOLD = 0.50
MODEL_REVIEW_THRESHOLD = 0.35

# c2pa قد يرجع Valid أو Trusted حسب الإصدار
VALID_C2PA_STATES = ("valid", "trusted", "success")


def score(report: dict) -> dict:
    reasons = []
    review_notes = []

    c2pa = report.get("c2pa", {})
    watermark = report.get("watermark", {})
    metadata = report.get("metadata", {})
    file_type = report.get("file_type", {})
    model = report.get("ai_model", {})

    ai_detected = False
    model_probability = model.get("ai_probability")

    # 1. Check the AI detection model
    if model.get("available") is True and model_probability is not None:
        try:
            model_probability = float(model_probability)

            if not 0 <= model_probability <= 1:
                raise ValueError("Probability must be between 0 and 1")

            if model_probability >= MODEL_AI_THRESHOLD:
                ai_detected = True
                reasons.append(
                    f"Strong AI-generation indication from the model "
                    f"({model_probability:.1%})"
                )

            elif model_probability >= MODEL_REVIEW_THRESHOLD:
                review_notes.append(
                    f"The AI detection model returned an uncertain score "
                    f"({model_probability:.1%})"
                )

        except (TypeError, ValueError):
            model_probability = None
            review_notes.append(
                "The AI model returned an invalid probability"
            )

    else:
        review_notes.append(
            "The AI detection model was unavailable"
        )

    # 2. Check image provenance
    if c2pa.get("ai") is True:
        validation = str(c2pa.get("validation", "")).lower()

        if any(state in validation for state in VALID_C2PA_STATES):
            ai_detected = True
            reasons.append(
                "AI generation indicator found in validated image credentials"
            )
        else:
            review_notes.append(
                "C2PA indicates AI generation, but validation was unsuccessful"
            )

    # 3. Check invisible watermark
    if watermark.get("found") is True:
        ai_detected = True
        reasons.append("A known AI image watermark was detected")

    # 4. Check metadata
    if metadata.get("ai_hits"):
        ai_detected = True
        reasons.append(
            "AI generation indicators found in metadata: "
            + ", ".join(metadata["ai_hits"])
        )

    # 5. Other review indicators
    if metadata.get("edit_hits"):
        review_notes.append(
            "Image editing information was found in metadata: "
            + ", ".join(metadata["edit_hits"])
        )

    # صور واتساب والسوشيال ميديا تمسح الـ metadata، فغيابها لا يعني شيئاً
    # لكنه يعني أن فحص الـ metadata والـ C2PA أضعف من المعتاد
    if (
        metadata.get("error") is None
        and not metadata.get("fields")
        and file_type.get("type") == "image"
    ):
        review_notes.append(
            "No metadata found (possibly stripped by compression or "
            "messaging apps), so provenance checks are weaker"
        )

    if file_type.get("extension_mismatch") is True:
        review_notes.append(
            "File extension does not match the actual file type"
        )

    kinds = {
        match.get("kind")
        for match in report.get("duplicates", {}).get("matches", [])
    }

    if kinds & {"exact", "near"}:
        review_notes.append(
            "Matching or similar files were uploaded by other students"
        )

    if "same_student" in kinds:
        review_notes.append(
            "This student uploaded a matching file before"
        )

    if "template" in kinds:
        review_notes.append(
            "Header/layout matches another student's document "
            "(may simply be the same clinic's template)"
        )

    if report.get("ela", {}).get("suspicious") is True:
        review_notes.append(
            "ELA found regions with inconsistent compression "
            "(possible local editing) - experimental indicator"
        )

    if report.get("text", {}).get("issues"):
        review_notes.append("Issues were found in the extracted text")

    if report.get("errors"):
        review_notes.append(
            "Some checks could not be completed due to errors"
        )

    # 6. Final result
    if ai_detected:
        verdict = "AI Indicators Detected"
    elif review_notes:
        verdict = "Needs Manual Review"
    else:
        verdict = (
            "No AI Indicators Detected - Authenticity Not Confirmed"
        )

    return {
        "ai_detected": ai_detected,
        "ai_probability": model_probability,
        "verdict": verdict,
        "reasons": reasons,
        "review_notes": review_notes,
        "is_final_judgment": False
    }