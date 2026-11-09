
import re
from datetime import date
import pytesseract
import cv2
import numpy as np

# ضبط مسار Tesseract
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789"
)

DATE_RE = re.compile(
    r"(\d{1,2})[/\\.-](\d{1,2})[/\\.-](\d{4})"
    r"|(\d{4})[/\\.-](\d{1,2})[/\\.-](\d{1,2})"
)

LICENSE_RE = re.compile(
    r"(?:license|licence|reg(?:istration)?|"
    r"ترخيص|رقم القيد|رقم التسجيل)"
    r"\D{0,15}(\d{4,})",
    re.I
)

DOCTOR_RE = re.compile(
    r"(?:dr\.?|doctor|د\.|دكتور|الدكتور)"
    r"\s*([^\n\d]{3,40})",
    re.I
)


def preprocess_image(image):
    """معالجة مسبقة للصورة بـ OpenCV لتحسين جودة الـ OCR وقراءة الخطوط والختم"""
    try:
        open_cv_image = np.array(image)
        if len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 3:
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
        elif len(open_cv_image.shape) == 3 and open_cv_image.shape[2] == 4:
            gray = cv2.cvtColor(open_cv_image, cv2.COLOR_RGBA2GRAY)
        else:
            gray = open_cv_image

        # تحسين التباين باستخدام CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        return enhanced
    except Exception:
        return image


def ocr_images(images, lang="ara+eng"):
    try:
        extracted_text = ""
        for image in images:
            processed_img = preprocess_image(image)
            # استخدام psm 6 لتحسين استخراج الكتل النصية
            text = pytesseract.image_to_string(
                processed_img,
                lang=lang,
                config='--psm 6'
            )
            extracted_text += text + "\n"

        return extracted_text, None

    except Exception as error:
        return "", (
            "OCR failed. Make sure Tesseract is installed "
            f"and the required language data is available: {error}"
        )


def _parse_dates(text: str):
    text = text.translate(ARABIC_DIGITS)
    dates = []

    for match in DATE_RE.finditer(text):
        try:
            if match.group(1):
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
            else:
                year = int(match.group(4))
                month = int(match.group(5))
                day = int(match.group(6))

            dates.append(date(year, month, day))
        except ValueError:
            continue

    return dates


def analyze_text(
    text: str,
    absence_date: date | None = None
) -> dict:
    normalized_text = text.translate(ARABIC_DIGITS)
    dates = _parse_dates(normalized_text)

    license_match = LICENSE_RE.search(normalized_text)
    doctor_match = DOCTOR_RE.search(normalized_text)

    issues = []

    if not text.strip():
        issues.append("No text could be extracted")
    else:
        if not dates:
            issues.append("No clear date was found")

        if any(d > date.today() for d in dates):
            issues.append("A future date was found")

        if absence_date and dates:
            # التحقق مما إذا كان أقرب تاريخ ضمن نطاق 7 أيام من تاريخ الغياب
            closest_diff = min(abs((d - absence_date).days) for d in dates)
            if closest_diff > 7:
                issues.append(
                    "The document dates are not close to the absence date (difference > 7 days)"
                )

        if not license_match:
            issues.append("No doctor license or registration number was found")

        if not doctor_match:
            issues.append("No clear doctor name was found")

    return {
        "dates": [
            extracted_date.isoformat()
            for extracted_date in dates
        ],
        "license": (
            license_match.group(1)
            if license_match else None
        ),
        "doctor": (
            doctor_match.group(1).strip()
            if doctor_match else None
        ),
        "issues": issues
    }