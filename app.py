import streamlit as st

from analyzer.client import get_client
from analyzer.crawler import crawl_url
from views.brief import render_brief_view
from views.chat import render_chat_view
from views.extract import render_extract_view
from views.images import render_images_view
from views.sidebar import render_crawled_urls, render_sidebar
from views.state import build_context, init_state, sync_pdfs


st.set_page_config(page_title="Website PDF Analyzer", layout="wide")

init_state()
inputs = render_sidebar()

if not inputs["gemini_key"]:
    st.warning("Add your Gemini API key in the sidebar to begin.")
    st.stop()

client = get_client(inputs["gemini_key"])

st.title("Website Analyzer")
st.caption("Extract, analyze, and chat with website content — PDFs or live URLs. Free tier only.")

sync_pdfs(inputs["uploaded"])

if inputs["crawl_btn"] and inputs["url_input"].strip():
    target = inputs["url_input"].strip()
    with st.spinner(f"Rendering {target} in headless Chromium..."):
        try:
            st.session_state.urls[target] = crawl_url(target)
            st.success(
                f"Crawled — {len(st.session_state.urls[target]['markdown'].split())} words captured."
            )
        except Exception as e:
            st.error(f"Crawl failed: {e}")

render_crawled_urls()

ctx = build_context(client, inputs["llama_key"])

if not ctx["doc_names"]:
    st.info("Upload a PDF or scrape a URL in the sidebar to begin.")
    st.stop()

VIEWS = {
    "Extract & Compare": render_extract_view,
    "Page Brief": render_brief_view,
    "Chat / RAG": render_chat_view,
    "Images": render_images_view,
}
active_view = st.radio(
    "View",
    list(VIEWS),
    horizontal=True,
    label_visibility="collapsed",
    key="active_view",
)
st.divider()
VIEWS[active_view](ctx)
