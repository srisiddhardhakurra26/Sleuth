from __future__ import annotations

import hashlib
import os
import re
import tempfile
import time

import pymupdf  # imported as `pymupdf`; older versions use `fitz`
import requests
import streamlit as st
from google.genai import types

from analyzer.prompts import GEMINI_VISION_EXTRACT_PROMPT


def _file_key(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()[:12]


@st.cache_data(show_spinner=False)
def extract_pymupdf(pdf_bytes: bytes, _key: str) -> str:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return "\n\n".join(page.get_text() for page in doc)


def upload_pdf_to_gemini(client, pdf_bytes: bytes, name: str):
    safe_name = re.sub(r"[^\x00-\x7F]", "_", name) or "doc.pdf"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    try:
        pdf_file = client.files.upload(file=path)
        waited = 0
        while pdf_file.state.name == "PROCESSING" and waited < 60:
            time.sleep(2)
            waited += 2
            pdf_file = client.files.get(name=pdf_file.name)
        if pdf_file.state.name != "ACTIVE":
            raise RuntimeError(f"Gemini file processing failed: {pdf_file.state.name}")
        return pdf_file
    finally:
        os.unlink(path)


@st.cache_data(show_spinner=False)
def extract_gemini_vision(_client, pdf_bytes: bytes, _key: str, name: str) -> str:
    pdf_file = upload_pdf_to_gemini(_client, pdf_bytes, name)
    try:
        resp = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[pdf_file, GEMINI_VISION_EXTRACT_PROMPT],
            config=types.GenerateContentConfig(temperature=0),
        )
        return resp.text or ""
    finally:
        try:
            _client.files.delete(name=pdf_file.name)
        except Exception:
            pass


@st.cache_data(show_spinner=False)
def extract_llamaparse(pdf_bytes: bytes, _key: str, api_key: str) -> str:
    """LlamaParse via direct REST API — bypasses the SDK (broken on Python 3.9)."""
    if not api_key:
        return ""
    base = "https://api.cloud.llamaindex.ai/api/parsing"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"file": ("document.pdf", pdf_bytes, "application/pdf")}
    data = {"result_type": "markdown"}

    r = requests.post(f"{base}/upload", headers=headers, files=files, data=data)
    r.raise_for_status()
    job_id = r.json()["id"]

    deadline = time.time() + 180
    while time.time() < deadline:
        r = requests.get(f"{base}/job/{job_id}", headers=headers)
        r.raise_for_status()
        status = (r.json().get("status") or "").upper()
        if status == "SUCCESS":
            break
        if status in ("ERROR", "CANCELLED", "FAILED"):
            raise RuntimeError(f"LlamaParse job {status.lower()}")
        time.sleep(2)
    else:
        raise RuntimeError("LlamaParse timed out after 3 minutes")

    r = requests.get(f"{base}/job/{job_id}/result/markdown", headers=headers)
    r.raise_for_status()
    return r.json().get("markdown", "")


EXTRACTORS = {
    "PyMuPDF (local, fast)": "pymupdf",
    "Gemini Vision (LLM, intelligent)": "gemini_vision",
    "LlamaParse (cloud, layout-aware)": "llamaparse",
}


def run_extractor(
    client,
    extractor_id: str,
    pdf_bytes: bytes,
    name: str = "doc.pdf",
    llama_key: str = "",
) -> str:
    key = _file_key(pdf_bytes)
    if extractor_id == "pymupdf":
        return extract_pymupdf(pdf_bytes, key)
    if extractor_id == "gemini_vision":
        return extract_gemini_vision(client, pdf_bytes, key, name)
    if extractor_id == "llamaparse":
        return extract_llamaparse(pdf_bytes, key, llama_key)
    return ""
