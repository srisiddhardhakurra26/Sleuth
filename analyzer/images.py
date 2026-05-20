from __future__ import annotations

import json

import pymupdf
import streamlit as st
from google.genai import types

from analyzer.prompts import IMAGE_CAPTION_PROMPT
from analyzer.schemas import ImageCaption


@st.cache_data(show_spinner=False)
def extract_images_from_pdf(pdf_bytes: bytes, _key: str, min_pixels: int = 10_000):
    """Pull images out of a PDF with PyMuPDF. Filters tiny icons by area."""
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    seen_xrefs = set()
    images = []
    for page_num, page in enumerate(doc, start=1):
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                base = doc.extract_image(xref)
            except Exception:
                continue
            w, h = base.get("width", 0), base.get("height", 0)
            if w * h < min_pixels:
                continue
            images.append(
                {
                    "page": page_num,
                    "xref": xref,
                    "ext": base["ext"],
                    "bytes": base["image"],
                    "width": w,
                    "height": h,
                }
            )
    doc.close()
    return images


_IMAGE_CAPTION_CONFIG = types.GenerateContentConfig(
    temperature=0,
    response_mime_type="application/json",
    response_schema=ImageCaption,
)


def caption_image(client, image_bytes: bytes, mime_type: str) -> dict:
    img_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[img_part, IMAGE_CAPTION_PROMPT],
        config=_IMAGE_CAPTION_CONFIG,
    )
    return json.loads(resp.text)
