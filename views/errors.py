from __future__ import annotations

import streamlit as st


def _friendly(e: Exception) -> tuple[str, str]:
    """Return (headline, action) for known Gemini error shapes."""
    s = str(e)
    low = s.lower()

    if "api_key_invalid" in low or "api key not valid" in low:
        return (
            "Your Gemini API key isn't valid.",
            "Grab a fresh one at https://aistudio.google.com/apikey and paste it into the sidebar. "
            "Watch for trailing spaces when copying.",
        )
    if "503" in s or "unavailable" in low or "high demand" in low:
        return (
            "Gemini is busy right now.",
            "This usually clears within 10–30 seconds. Try again in a moment.",
        )
    if "429" in s or "resource_exhausted" in low or "rate limit" in low or "quota" in low:
        return (
            "You've hit the free-tier rate limit.",
            "Gemini's free tier allows ~15 requests per minute. Wait about a minute and try again.",
        )
    if "500" in s or "internal" in low and "internal error" in low:
        return (
            "Gemini had an internal error.",
            "This is on Google's end — not your code. Try again shortly.",
        )
    if "deadline" in low or "timeout" in low:
        return (
            "The request timed out.",
            "Could be a slow network or a very large document. Try again, or shrink the input.",
        )
    return ("Something went wrong.", "See technical details below.")


def show_error(e: Exception) -> None:
    """Render a friendly error block with a collapsible raw exception."""
    headline, action = _friendly(e)
    st.error(headline)
    st.caption(action)
    with st.expander("Technical details"):
        st.code(str(e))
