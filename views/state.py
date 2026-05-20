from __future__ import annotations

import streamlit as st

from analyzer.extractors import run_extractor


def init_state() -> None:
    """Initialize session-state containers. Idempotent across reruns."""
    if "docs" not in st.session_state:
        st.session_state.docs = {}      # PDF: name -> bytes
    if "urls" not in st.session_state:
        st.session_state.urls = {}      # URL: url -> {markdown, html, screenshot, metadata}


def sync_pdfs(uploaded_files) -> None:
    """Add new PDFs from the uploader; drop ones the user removed from the widget."""
    current_names = []
    for f in uploaded_files or []:
        if f.name not in st.session_state.docs:
            st.session_state.docs[f.name] = f.read()
        current_names.append(f.name)
    for name in list(st.session_state.docs.keys()):
        if name not in current_names:
            del st.session_state.docs[name]


def remove_url(url: str) -> None:
    """Drop a crawled URL and any derived state for it."""
    st.session_state.urls.pop(url, None)
    for prefix in ("page_brief::", "images::", "videos::"):
        st.session_state.pop(prefix + url, None)


def all_doc_names() -> list:
    return list(st.session_state.docs.keys()) + list(st.session_state.urls.keys())


def doc_kind(name: str) -> str:
    return "url" if name in st.session_state.urls else "pdf"


def make_doc_text(client, llama_key: str):
    """Return a (name, extractor_id) -> text function bound to the current client."""

    def _doc_text(name: str, extractor_id: str = "pymupdf") -> str:
        if doc_kind(name) == "url":
            return st.session_state.urls[name]["markdown"]
        return run_extractor(
            client, extractor_id, st.session_state.docs[name], name, llama_key
        )

    return _doc_text


def build_context(client, llama_key: str) -> dict:
    """Bundle dependencies for view functions in one dict."""
    return {
        "client": client,
        "llama_key": llama_key,
        "doc_names": all_doc_names(),
        "doc_kind": doc_kind,
        "doc_text": make_doc_text(client, llama_key),
    }
