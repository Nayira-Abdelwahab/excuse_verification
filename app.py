import os
import tempfile

import streamlit as st

from main import analyze_file


st.set_page_config(
    page_title="Medical Excuse Checker",
    page_icon="🔍",
    layout="centered"
)

st.markdown("""
<style>
.main {
    direction: rtl;
}
h1, h2, p, label {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("نظام فحص الأعذار الطبية")
st.write("ارفعي صورة العذر الطبي لبدء الفحص.")

st.divider()

student_id = st.text_input("رقم الطالب")

use_absence = st.checkbox("أعرف تاريخ الغياب")
absence_date = None
if use_absence:
    absence_date = st.date_input("تاريخ الغياب")

uploaded_file = st.file_uploader(
    "اختاري صورة العذر الطبي",
    type=["jpg", "jpeg", "png", "pdf"]
)

if st.button("فحص العذر الطبي", use_container_width=True):

    student_id = student_id.strip()

    if not student_id:
        st.warning("من فضلك أدخلي رقم الطالب.")

    elif not student_id.isdigit():
        st.warning("رقم الطالب يجب أن يتكون من أرقام فقط.")

    elif uploaded_file is None:
        st.warning("من فضلك ارفعي ملف العذر.")

    else:
        temp_path = None

        try:
            suffix = os.path.splitext(uploaded_file.name)[1]

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix
            ) as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_path = temp_file.name

            with st.spinner("جاري فحص المستند واستخراج البيانات..."):
                report = analyze_file(
                    temp_path,
                    student_id,
                    absence_date=absence_date
                )
            score_data = report["score"]

            st.divider()
            st.subheader("النتيجة النهائية")

            # عرض النتيجة ثنائية (AI أو REAL) فقط
            if score_data["ai_detected"]:
                st.error("AI")
            else:
                st.success("REAL")

            if score_data["ai_probability"] is not None:
                st.metric(
                    "احتمال التوليد بالذكاء الاصطناعي (حسب النموذج)",
                    f"{score_data['ai_probability']:.1%}"
                )

            if report["duplicates"].get("matches"):
                st.markdown("**ملفات مشابهة تم رفعها سابقاً:**")
                for match in report["duplicates"]["matches"]:
                    st.write(f"- الطالب {match['student_id']}: {match['reason']}")

            if suffix.lower() in (".jpg", ".jpeg"):
                try:
                    ela_image = make_ela_image(temp_path)

                    if ela_image is not None:
                        with st.expander(
                            "صورة ELA للمراجع (المناطق الأفتح قد تكون معدّلة)"
                        ):
                            st.image(ela_image, use_container_width=True)

                except Exception:
                    pass

            st.caption(
                "REAL تعني عدم اكتشاف مؤشرات توليد AI، "
                "ولا تثبت أن الصورة أصلية بشكل قاطع."
            )

        except Exception as e:
            st.error(f"حدث خطأ أثناء الفحص: {e}")

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)