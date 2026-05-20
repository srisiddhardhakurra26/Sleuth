from __future__ import annotations

import streamlit as st
from google.genai import types

from analyzer.extractors import EXTRACTORS
from analyzer.rag import RAGIndex


def render_chat_view(ctx: dict) -> None:
    client = ctx["client"]
    llama_key = ctx["llama_key"]
    doc_names = ctx["doc_names"]
    doc_kind = ctx["doc_kind"]
    doc_text = ctx["doc_text"]

    st.subheader("Ask questions about the documents")
    mode = st.radio(
        "Mode",
        ["Single document (full context)", "Multi-document (RAG)"],
        horizontal=True,
        key="t3_mode",
    )

    if mode.startswith("Single"):
        _render_single_doc(client, llama_key, doc_names, doc_kind, doc_text)
    else:
        _render_rag(client, doc_names, doc_text)


def _render_single_doc(client, llama_key: str, doc_names, doc_kind, doc_text) -> None:
    st.caption(
        "Feeds the entire selected PDF into Gemini's 1M-token context. "
        "Best for small libraries or deep questions about one doc."
    )
    sel = st.selectbox("Document", doc_names, key="t3_single_doc")
    if doc_kind(sel) == "pdf":
        single_extractor_labels = [
            lbl for lbl in EXTRACTORS.keys()
            if not (EXTRACTORS[lbl] == "llamaparse" and not llama_key)
        ]
        ex_label = st.selectbox(
            "Extractor", single_extractor_labels, key="t3_single_ex"
        )
        ex_id = EXTRACTORS[ex_label]
    else:
        st.caption(":grey[URL doc — markdown pre-extracted by Playwright.]")
        ex_id = "pymupdf"  # ignored for URL docs

    question = st.text_input("Your question", key="t3_single_q")
    if question:
        with st.spinner("Thinking..."):
            try:
                text = doc_text(sel, ex_id)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=(
                        "Answer the question using ONLY the document below. "
                        "If the answer is not in the document, say so.\n\n"
                        f"--- DOCUMENT ({sel}) ---\n{text}\n\n"
                        f"QUESTION: {question}"
                    ),
                    config=types.GenerateContentConfig(temperature=0),
                )
                st.markdown(resp.text)
            except Exception as e:
                st.error(f"Failed: {e}")


def _render_rag(client, doc_names, doc_text) -> None:
    st.caption(
        "Chunks all uploaded PDFs, embeds with Gemini gemini-embedding-001, "
        "retrieves top-k by cosine similarity, answers with Gemini Flash."
    )
    cols = st.columns([1, 1, 2])
    with cols[0]:
        k = st.slider("Top-k chunks", 3, 12, 6)
    with cols[1]:
        chunk_words = st.slider("Chunk size (words)", 150, 500, 300, step=50)
    with cols[2]:
        rebuild = st.button("Rebuild index", help="Re-chunk and re-embed everything")

    index_key = (tuple(doc_names), chunk_words)
    need_build = (
        rebuild
        or "rag_index_key" not in st.session_state
        or st.session_state.rag_index_key != index_key
    )

    if need_build:
        with st.spinner("Building index..."):
            try:
                index = RAGIndex.build(
                    client, doc_text, doc_names, chunk_words=chunk_words
                )
            except RuntimeError as e:
                st.error(str(e))
                st.stop()
            st.session_state.rag_index = index
            st.session_state.rag_index_key = index_key

    index: RAGIndex = st.session_state.rag_index
    st.success(f"Indexed {len(index)} chunks across {len(doc_names)} docs.")

    question = st.text_input("Your question", key="t3_rag_q")
    if question:
        with st.spinner("Retrieving + answering..."):
            try:
                retrieved = index.search(client, question, k=k)
                context = "\n\n".join(
                    f"[source: {s}]\n{c}" for s, c, _ in retrieved
                )
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=(
                        "Answer the question using ONLY the retrieved context. "
                        "Cite source filenames inline like [source.pdf]. "
                        "If the context doesn't contain the answer, say so.\n\n"
                        f"--- RETRIEVED CONTEXT ---\n{context}\n\n"
                        f"QUESTION: {question}"
                    ),
                    config=types.GenerateContentConfig(temperature=0),
                )
                st.markdown(resp.text)
                with st.expander(f"Retrieved sources ({len(retrieved)})"):
                    for src, ch, score in retrieved:
                        st.markdown(f"**{src}** · similarity {score:.3f}")
                        st.text(ch[:400] + ("..." if len(ch) > 400 else ""))
            except Exception as e:
                st.error(f"Failed: {e}")
