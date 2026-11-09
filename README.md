# Medical Excuse Checker — فاحص الأعذار الطبية

سكريبت Python بيفحص الأعذار الطبية (صور / PDF) ويطلّع **مؤشرات** على احتمال إنها متولّدة بالـ AI أو مزوّرة.
النتيجة مؤشر للمراجعة البشرية، **مش حكم نهائي**.

## الفحوصات
1. نوع الملف الحقيقي (من أول بايتات الملف مش من الامتداد)
2. الـ Metadata (بيدوّر على أدوات AI وأدوات تعديل)
3. Content Credentials / C2PA
4. Invisible watermark (أدوات Stable Diffusion الشائعة فقط)
5. كشف التكرار بين الطلبة (SHA-256 + perceptual hash)
6. OCR + استخراج التاريخ واسم الدكتور ورقم الترخيص + قواعد منطقية
7. نظام درجات + توصية

## التسطيب على ويندوز

### 1) Python
نزّلي Python 3.10 أو أحدث من python.org، وعلّمي على **Add Python to PATH** وقت التسطيب.

### 2) المكتبات
افتحي PowerShell جوّه فولدر المشروع:
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
لو `invisible-watermark` أو `c2pa-python` فشلوا في التسطيب، مفيش مشكلة: المشروع بيتخطى الفحص ده ويكمّل.

### 3) Tesseract (للـ OCR)
- نزّلي المسطّب من: https://github.com/UB-Mannheim/tesseract/wiki
- وقت التسطيب اختاري لغة **Arabic** من Additional language data.
- ضيفي مسار التسطيب (غالباً `C:\Program Files\Tesseract-OCR`) لـ PATH، أو حطي السطر ده في أول `ocr_check.py`:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### 4) Poppler (لتحويل PDF لصور)
- نزّلي Poppler لويندوز من: https://github.com/oschwartz10612/poppler-windows/releases
- فكّي الضغط وضيفي فولدر `bin` لـ PATH.

## التشغيل
```
python main.py excuse.pdf --student 12345
python main.py excuse.jpg --student 12345 --absence 2026-11-02
python main.py --folder uploads          (اسم كل ملف = رقم الطالب)
python main.py excuse.pdf --student 12345 --json
```

## ملاحظات
- الفحوصات بتسجّل الملفات في `seen_files.json` عشان تكتشف التكرار. امسحيه لو عايزة تبدئي من الأول.
- غياب watermark أو Content Credentials **مش معناه** إن العذر حقيقي.
- أقوى فحص فعلي هو التحقق من المصدر (QR / اتصال بالمستشفى) — ده برّه نطاق السكريبت.
- OCR على صور رديئة ممكن يغلط في الأرقام، فاتأكدي من الملاحظات يدوياً.

## هيكل المشروع
```
main.py             # بيجمع كل حاجة
file_type.py        # 1
metadata_check.py   # 2
c2pa_check.py       # 3
watermark_check.py  # 4
duplicates.py       # 5
ocr_check.py        # 6
scoring.py          # 7
```
