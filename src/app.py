from pathlib import Path

import streamlit as st

from rag_chain import answer_question

ROOT = Path(__file__).resolve().parent.parent

DISCLAIMER = (
    "⚠️ This assistant answers only from two public documents "
    "(WHO: Diagnosis and Management of Type 2 Diabetes, and Care of Adults with Advanced CKD). "
    "It is for information only and is not medical advice. Always consult a healthcare professional.\n\n"
    "⚠️ هذا المساعد يجيب فقط من مستندين عامين، وهو للمعلومات فقط وليس بديلاً عن الاستشارة الطبية."
)

st.set_page_config(page_title="Medical RAG Assistant", page_icon="🩺")
st.title("🩺 Medical RAG Assistant")
st.warning(DISCLAIMER)
st.caption("Each question is answered on its own, without memory of earlier questions. Please write complete questions.")

question = st.chat_input("Ask a question about the documents / اسألي عن المستندات")

if question:
    st.chat_message("user").write(question)

    with st.spinner("Searching the documents..."):
        answer, chunks = answer_question(question)

    # the last line "SOURCES: ..." is hidden from the answer and used to find the pages
    parts = answer.split("SOURCES:")
    answer_text = parts[0].strip()
    st.chat_message("assistant").write(answer_text)

    sources_line = answer
    if len(parts) > 1:
        sources_line = parts[-1]

    cited_chunks = []
    for chunk in chunks:
        if f"page {chunk['page']})" in sources_line:
            cited_chunks.append(chunk)

    if len(cited_chunks) > 0:
        st.markdown("**Sources:**")
        shown_sources = []
        for chunk in cited_chunks:
            source_text = f"{chunk['source']} — page {chunk['page']}"
            if source_text not in shown_sources:
                shown_sources.append(source_text)
                st.markdown("- " + source_text)

        st.caption("For more details and to verify the answer, please check the cited pages in the original documents. Page images are shown below when available. / للمزيد من التفاصيل وللتحقق، راجعي الصفحات المذكورة في المستند الأصلي.")

        for chunk in cited_chunks:
            if chunk["image_path"] != "":
                with st.expander(f"Original page image and full content (page {chunk['page']})"):
                    st.image(str(ROOT / chunk["image_path"]))
                    if "STEP 1 - BOXES" in chunk["text"]:
                        st.caption("The arrows in this flowchart were extracted automatically and may contain errors. Please check them against the image above.")
                    st.markdown("**Full content of this page's figure or table (text):**")
                    st.text(chunk["text"])