
def check_c2pa(path: str) -> dict:
    try:
        import c2pa
    except ImportError:
        return {
            "available": False,
            "found": None,
            "ai": None,
            "note": "C2PA library is not installed"
        }

    try:
        reader = c2pa.Reader.try_create(path)

        if reader is None:
            return {
                "available": True,
                "found": False,
                "ai": None,
                "validation": None,
                "generator": None,
                "note": "No Content Credentials found"
            }

        validation = reader.get_validation_state()
        active = reader.get_active_manifest() or {}

        # Extract C2PA actions
        actions = []

        for assertion in active.get("assertions", []):
            if str(assertion.get("label", "")).startswith("c2pa.actions"):
                actions.extend(
                    assertion.get("data", {}).get("actions", [])
                )

        # Detect AI-related digital source types
        ai_sources = [
            action.get("digitalSourceType", "")
            for action in actions
            if "trainedalgorithmicmedia" in
            str(action.get("digitalSourceType", "")).lower()
        ]

        generator = (
            active.get("claim_generator")
            or active.get("claim_generator_info")
        )

        # Interpret validation state
        if str(validation).lower() == "valid":
            validation_note = "C2PA validation successful"
        else:
            validation_note = f"C2PA validation state: {validation}"

        # Build result note
        if ai_sources:
            ai_note = (
                "AI generation indicator found: "
                + str(ai_sources[0].split("/")[-1])
            )
        else:
            ai_note = "No AI generation indicator found in C2PA actions"

        note = (
            "Content Credentials found. "
            + validation_note
            + ". "
            + ai_note
        )

        return {
            "available": True,
            "found": True,
            "ai": bool(ai_sources),
            "validation": str(validation),
            "generator": str(generator) if generator else None,
            "ai_sources": ai_sources,
            "note": note
        }

    except Exception as e:
        return {
            "available": True,
            "found": None,
            "ai": None,
            "validation": None,
            "generator": None,
            "note": f"C2PA inspection failed: {e}"
        }
