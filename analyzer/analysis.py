from __future__ import annotations

import json

from google.genai import types

from analyzer.extractors import upload_pdf_to_gemini
from analyzer.prompts import ANALYSIS_PROMPT
from analyzer.schemas import PageBrief


_ANALYSIS_CONFIG = types.GenerateContentConfig(
    temperature=0,
    response_mime_type="application/json",
    response_schema=PageBrief,
)


def analyze_text(client, text: str) -> dict:
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{ANALYSIS_PROMPT}\n\n--- DOCUMENT TEXT ---\n{text}",
        config=_ANALYSIS_CONFIG,
    )
    return json.loads(resp.text)


def analyze_pdf_direct(client, pdf_bytes: bytes, name: str) -> dict:
    pdf_file = upload_pdf_to_gemini(client, pdf_bytes, name)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[pdf_file, ANALYSIS_PROMPT],
            config=_ANALYSIS_CONFIG,
        )
        return json.loads(resp.text)
    finally:
        try:
            client.files.delete(name=pdf_file.name)
        except Exception:
            pass


def analyze_url_doc(client, url_data: dict, use_screenshot: bool = True) -> dict:
    """Analyze a crawled URL using both markdown and full-page screenshot."""
    contents = [ANALYSIS_PROMPT]
    if use_screenshot and url_data.get("screenshot"):
        contents.append(
            types.Part.from_bytes(
                data=url_data["screenshot"], mime_type="image/png"
            )
        )
    contents.append(
        f"--- PAGE CONTENT (markdown from {url_data.get('url', 'URL')}) ---\n"
        f"{url_data.get('markdown', '')}"
    )
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=_ANALYSIS_CONFIG,
    )
    return json.loads(resp.text)
