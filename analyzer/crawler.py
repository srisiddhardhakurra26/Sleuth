from __future__ import annotations

import re
from urllib.parse import urljoin

import streamlit as st


@st.cache_data(show_spinner=False)
def crawl_url(url: str) -> dict:
    """Render a page locally with headless Chromium. Scrolls to trigger lazy loading,
    then captures full HTML + full-page screenshot + markdown conversion."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright is not installed. Run: pip install playwright && playwright install chromium"
        )
    from markdownify import markdownify as md

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            page.evaluate(
                """
                async () => {
                    let total = 0;
                    const step = 400;
                    while (total < document.body.scrollHeight) {
                        window.scrollBy(0, step);
                        total += step;
                        await new Promise(r => setTimeout(r, 100));
                    }
                    window.scrollTo(0, 0);
                }
                """
            )
            page.wait_for_timeout(1500)
            html = page.content()
            screenshot_bytes = page.screenshot(full_page=True, type="png")
            title = page.title()
            meta_desc = page.evaluate(
                "document.querySelector('meta[name=\"description\"]')?.content || ''"
            )
        finally:
            browser.close()

    markdown = md(html, heading_style="ATX", strip=["script", "style", "noscript"])

    return {
        "url": url,
        "markdown": markdown,
        "html": html,
        "screenshot": screenshot_bytes,
        "metadata": {"title": title, "description": meta_desc},
    }


def extract_media_from_html(html: str, base_url: str) -> dict:
    """Parse <img>/<video>/<iframe> src URLs from HTML, resolve to absolute URLs."""
    if not html:
        return {"images": [], "videos": []}
    img_pat = re.compile(
        r'<(?:img|source)[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE
    )
    vid_pat = re.compile(
        r'<video[^>]+src=["\']([^"\']+)["\']'
        r'|<source[^>]+src=["\']([^"\']+\.(?:mp4|webm|mov))["\']'
        r'|<iframe[^>]+src=["\']([^"\']*(?:youtube\.com|youtu\.be|vimeo\.com)[^"\']*)["\']',
        re.IGNORECASE,
    )
    images = []
    for m in img_pat.findall(html):
        u = urljoin(base_url, m)
        if u.startswith(("http://", "https://", "data:")):
            images.append(u)
    videos = []
    for m in vid_pat.findall(html):
        # findall returns tuples for grouped alternation
        u = next((x for x in m if x), "") if isinstance(m, tuple) else m
        if u:
            u = urljoin(base_url, u)
            if u.startswith(("http://", "https://")):
                videos.append(u)
    # De-dupe preserving order
    seen = set()
    images = [x for x in images if not (x in seen or seen.add(x))]
    seen = set()
    videos = [x for x in videos if not (x in seen or seen.add(x))]
    return {"images": images, "videos": videos}
