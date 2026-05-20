from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
import streamlit as st
from PIL import Image, UnidentifiedImageError

from analyzer.crawler import extract_media_from_html
from analyzer.extractors import _file_key
from analyzer.images import caption_image, extract_images_from_pdf


def render_images_view(ctx: dict) -> None:
    client = ctx["client"]
    doc_names = ctx["doc_names"]
    doc_kind = ctx["doc_kind"]

    st.subheader("Pull images out of a PDF and caption them")
    st.caption(
        "PyMuPDF extracts images locally (free, instant). Optionally caption each "
        "with Gemini Vision to identify logos, hero shots, infographics, etc."
    )
    sel = st.selectbox("Document", doc_names, key="t4_doc")

    # Full-page screenshot for URL docs — show it first.
    if doc_kind(sel) == "url" and st.session_state.urls[sel].get("screenshot"):
        with st.expander("Full-page screenshot (Playwright)", expanded=True):
            try:
                st.image(
                    st.session_state.urls[sel]["screenshot"],
                    caption=f"Captured from {sel}",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Screenshot render failed: {e}")

    cols = st.columns([1, 1, 1])
    with cols[0]:
        min_dim = st.slider(
            "Min image size (pixels per side)", 32, 400, 100, step=16,
            help="Filter out small icons/decorations.",
        )
    with cols[1]:
        max_to_caption = st.slider(
            "Max images to caption", 0, 50, 12,
            help="Each caption is one Gemini Flash call. Set to 0 to skip captioning.",
        )
    with cols[2]:
        run_btn = st.button("Extract images", type="primary", key="t4_btn")

    if run_btn:
        imgs = _extract_images(sel, doc_kind, min_dim)
        st.write(f"Found **{len(imgs)}** images.")
        _caption_batch(client, imgs, max_to_caption)
        st.session_state[f"images::{sel}"] = imgs

    video_urls = st.session_state.get(f"videos::{sel}", [])
    if video_urls:
        with st.expander(f"Videos / embeds found ({len(video_urls)})", expanded=False):
            for v in video_urls:
                st.markdown(f"- [{v}]({v})")

    imgs = st.session_state.get(f"images::{sel}")
    if imgs:
        _render_grid(imgs, sel, doc_kind)


def _extract_images(sel: str, doc_kind, min_dim: int) -> list:
    """Extract images either from PDF bytes (PyMuPDF) or URL HTML (fetch + filter)."""
    imgs: list = []
    with st.spinner("Extracting images..."):
        try:
            if doc_kind(sel) == "pdf":
                imgs = extract_images_from_pdf(
                    st.session_state.docs[sel],
                    _file_key(st.session_state.docs[sel]),
                    min_pixels=min_dim * min_dim,
                )
            else:
                url_data = st.session_state.urls[sel]
                media = extract_media_from_html(
                    url_data.get("html", ""), url_data.get("url", "")
                )
                st.session_state[f"videos::{sel}"] = media["videos"]
                imgs = _fetch_url_images(media["images"], min_dim)
        except Exception as e:
            st.error(f"Image extraction failed: {e}")
    return imgs


def _fetch_url_images(image_urls: list, min_dim: int) -> list:
    """Download each <img> URL, validate decodable, filter small/duplicates."""
    imgs: list = []
    seen_hashes: set = set()
    for i, img_url in enumerate(image_urls):
        if img_url.startswith("data:"):
            continue
        if img_url.lower().split("?")[0].endswith(".svg"):
            continue  # skip SVG icons
        try:
            r = requests.get(img_url, timeout=15)
            r.raise_for_status()
            b = r.content
            ct = r.headers.get("content-type", "").lower()
            if "svg" in ct or "gif" in ct and len(b) < 4096:
                continue
            # Validate decodable + check real dimensions.
            try:
                with Image.open(BytesIO(b)) as pim:
                    pim.load()
                    w, h = pim.size
                    fmt = (pim.format or "PNG").lower()
            except (UnidentifiedImageError, Exception):
                continue
            if min(w, h) < min_dim:
                continue
            # Dedupe by content hash (catches retina variants of same image).
            digest = hashlib.md5(b).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            imgs.append(
                {
                    "page": 0,
                    "xref": i,
                    "ext": "jpg" if fmt == "jpeg" else fmt,
                    "bytes": b,
                    "width": w,
                    "height": h,
                    "source_url": img_url,
                }
            )
        except Exception:
            continue
    return imgs


def _caption_batch(client, imgs: list, max_to_caption: int) -> None:
    if imgs and max_to_caption > 0:
        to_caption = imgs[:max_to_caption]
        progress = st.progress(0.0, text="Captioning with Gemini Vision...")
        captions = {}
        for i, img in enumerate(to_caption):
            try:
                captions[img["xref"]] = caption_image(
                    client, img["bytes"], f"image/{img['ext']}"
                )
            except Exception as e:
                captions[img["xref"]] = {
                    "description": f"(caption failed: {e})",
                    "visible_text": "",
                    "likely_purpose": "",
                }
            progress.progress(
                (i + 1) / len(to_caption),
                text=f"Captioning {i + 1}/{len(to_caption)}...",
            )
        progress.empty()
        for img in imgs:
            img["caption"] = captions.get(img["xref"])
    else:
        for img in imgs:
            img["caption"] = None


def _render_grid(imgs: list, sel: str, doc_kind) -> None:
    purposes = sorted(
        {(im.get("caption") or {}).get("likely_purpose", "") for im in imgs}
        - {""}
    )
    if purposes:
        filt = st.multiselect(
            "Filter by purpose",
            purposes,
            default=[p for p in purposes if p not in ("icon", "decorative")],
        )
        shown = [
            im for im in imgs
            if not im.get("caption")
            or im["caption"].get("likely_purpose") in filt
        ]
    else:
        shown = imgs

    st.write(f"Showing {len(shown)} of {len(imgs)} images.")
    per_row = 3
    is_url = doc_kind(sel) == "url"
    stem = (
        re.sub(r"[^A-Za-z0-9._-]", "_", urlparse(sel).netloc or "url")
        if is_url else Path(sel).stem
    )
    for row_start in range(0, len(shown), per_row):
        row = shown[row_start : row_start + per_row]
        cols = st.columns(per_row)
        for col, img in zip(cols, row):
            with col:
                if is_url:
                    caption = f"{img['width']}×{img['height']}"
                else:
                    caption = f"page {img['page']} · {img['width']}×{img['height']}"
                try:
                    st.image(
                        img["bytes"],
                        caption=caption,
                        use_container_width=True,
                    )
                except Exception as e:
                    st.warning(f"Could not render image: {e}")
                    continue
                cap = img.get("caption")
                if cap:
                    purpose = cap.get("likely_purpose", "")
                    if purpose:
                        st.markdown(f"**{purpose}**")
                    st.write(cap.get("description", ""))
                    vt = cap.get("visible_text", "")
                    if vt:
                        st.caption(f"Text: {vt}")
                st.download_button(
                    "Download",
                    img["bytes"],
                    file_name=f"{stem}_img{img['xref']}.{img['ext']}",
                    key=f"dlimg_{sel}_{img['xref']}",
                )
