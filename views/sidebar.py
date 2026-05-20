from __future__ import annotations

import os

import streamlit as st

from views.state import remove_url


def render_sidebar() -> dict:
    """Render the sidebar inputs. Returns a dict for the orchestrator."""
    with st.sidebar:
        st.header("Setup")
        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=os.getenv("GEMINI_API_KEY", ""),
            help="Free at aistudio.google.com",
        )
        llama_key = st.text_input(
            "LlamaParse API Key (optional)",
            type="password",
            value=os.getenv("LLAMA_CLOUD_API_KEY", ""),
            help="Free tier at cloud.llamaindex.ai — enables the LlamaParse extractor",
        )
        st.divider()
        st.header("Inputs")
        uploaded = st.file_uploader(
            "Upload PDFs", type="pdf", accept_multiple_files=True
        )
        with st.form("crawl_form", clear_on_submit=False, border=False):
            url_input = st.text_input(
                "Or scrape a URL",
                placeholder="https://www.business.reddit.com/",
                help="Renders the page locally with headless Chromium "
                     "(captures JS, lazy-loaded sections, full-page screenshot). "
                     "Press Enter or click Crawl URL to start.",
            )
            crawl_btn = st.form_submit_button("Crawl URL", type="primary")

    return {
        "gemini_key": gemini_key,
        "llama_key": llama_key,
        "uploaded": uploaded,
        "url_input": url_input,
        "crawl_btn": crawl_btn,
    }


def render_crawled_urls() -> None:
    """List crawled URLs in the sidebar with a Remove button each.
    Rendered AFTER the crawl handler runs so a freshly-crawled URL appears immediately."""
    with st.sidebar:
        if not st.session_state.urls:
            return
        st.markdown(f"**Crawled URLs ({len(st.session_state.urls)})**")
        for u in list(st.session_state.urls.keys()):
            meta = st.session_state.urls[u].get("metadata", {}) or {}
            title = (meta.get("title") or "").strip()
            label = title or u
            display = label if len(label) <= 50 else label[:47] + "..."
            url_display = u if len(u) <= 50 else u[:47] + "..."
            with st.container(border=True):
                st.markdown(f"**{display}**")
                st.caption(url_display)
                if st.button(
                    "Remove",
                    key=f"rm_url_{u}",
                    help=f"Remove {u}",
                    use_container_width=True,
                ):
                    remove_url(u)
                    st.rerun()
