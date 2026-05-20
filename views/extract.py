from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from analyzer.extractors import EXTRACTORS, run_extractor


def render_extract_view(ctx: dict) -> None:
    client = ctx["client"]
    llama_key = ctx["llama_key"]
    doc_names = ctx["doc_names"]
    doc_kind = ctx["doc_kind"]

    st.subheader("Side-by-side text extraction")
    st.caption(
        "Same PDF, different extractors. PyMuPDF is instant; "
        "Gemini Vision and LlamaParse take 10-30s on first run (then cached)."
    )

    pdf_docs = [n for n in doc_names if doc_kind(n) == "pdf"]
    if not pdf_docs:
        st.info("Upload a PDF to compare extractors. URL docs are pre-extracted by Playwright.")
        return

    available_labels = [
        lbl for lbl, eid in EXTRACTORS.items()
        if not (eid == "llamaparse" and not llama_key)
    ]
    default_pick = [
        lbl for lbl in available_labels
        if EXTRACTORS[lbl] in ("pymupdf", "gemini_vision")
    ]
    sel = st.selectbox("Document", pdf_docs, key="t1_doc")
    picked_labels = st.multiselect(
        "Extractors to compare",
        available_labels,
        default=default_pick or available_labels[:2],
        help="LLM-based extractors are slower but handle layout/tables/OCR better.",
    )

    if not llama_key:
        st.caption(":grey[LlamaParse hidden — add API key in sidebar to enable.]")

    if picked_labels:
        per_row = 3
        for row_start in range(0, len(picked_labels), per_row):
            row = picked_labels[row_start : row_start + per_row]
            cols = st.columns(len(row))
            for col, label in zip(cols, row):
                ex_id = EXTRACTORS[label]
                with col:
                    st.markdown(f"**{label}**")
                    try:
                        t0 = time.time()
                        with st.spinner("Extracting..."):
                            text = run_extractor(
                                client, ex_id, st.session_state.docs[sel], sel, llama_key
                            )
                        elapsed = time.time() - t0
                        st.caption(f"{len(text.split())} words · {elapsed:.2f}s")
                        st.text_area(
                            "Extracted text",
                            text[:8000],
                            height=320,
                            key=f"t1_{ex_id}_{sel}",
                            label_visibility="collapsed",
                        )
                        st.download_button(
                            "Download full text",
                            text,
                            file_name=f"{Path(sel).stem}__{ex_id}.txt",
                            key=f"dl_{ex_id}_{sel}",
                        )
                    except Exception as e:
                        st.error(f"Failed: {e}")
