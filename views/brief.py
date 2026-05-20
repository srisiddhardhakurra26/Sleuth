from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from analyzer.analysis import analyze_pdf_direct, analyze_text, analyze_url_doc
from analyzer.extractors import EXTRACTORS, run_extractor
from views.errors import show_error


def render_brief_view(ctx: dict) -> None:
    client = ctx["client"]
    llama_key = ctx["llama_key"]
    doc_names = ctx["doc_names"]
    doc_kind = ctx["doc_kind"]

    st.subheader("Page brief for sales research")
    st.caption(
        "Structured analysis of a single page: purpose, audience, pain points addressed, "
        "differentiators, offers, proof points, and concrete talking points to use in outreach."
    )
    sel = st.selectbox("Document", doc_names, key="t2_doc")

    if doc_kind(sel) == "url":
        _render_url_controls(client, sel)
    else:
        _render_pdf_controls(client, llama_key, sel)

    brief = st.session_state.get(f"page_brief::{sel}")
    if brief:
        _render_brief(brief, sel, doc_kind)


def _render_url_controls(client, sel: str) -> None:
    st.caption(
        "URL doc — markdown was pre-extracted by Playwright. "
        "Gemini will also see the full-page screenshot for visual cues."
    )
    use_screenshot = st.checkbox(
        "Include screenshot for visual analysis",
        value=bool(st.session_state.urls[sel].get("screenshot")),
        help="Lets Gemini describe colors, typography, hero imagery.",
    )
    if st.button("Generate Brief", type="primary", key="t2_btn"):
        with st.spinner("Analyzing..."):
            try:
                result = analyze_url_doc(
                    client, st.session_state.urls[sel], use_screenshot=use_screenshot
                )
                st.session_state[f"page_brief::{sel}"] = result
            except Exception as e:
                show_error(e)


def _render_pdf_controls(client, llama_key: str, sel: str) -> None:
    source_options = [
        lbl for lbl in EXTRACTORS.keys()
        if not (EXTRACTORS[lbl] == "llamaparse" and not llama_key)
    ] + ["Gemini Vision (analyze PDF directly)"]
    src_label = st.selectbox("Source", source_options, key="t2_src")

    if st.button("Generate Brief", type="primary", key="t2_btn"):
        with st.spinner("Analyzing..."):
            try:
                if src_label == "Gemini Vision (analyze PDF directly)":
                    result = analyze_pdf_direct(
                        client, st.session_state.docs[sel], sel
                    )
                else:
                    ex_id = EXTRACTORS[src_label]
                    text = run_extractor(
                        client, ex_id, st.session_state.docs[sel], sel, llama_key
                    )
                    if not text.strip():
                        st.error("No text extracted. Try a different source.")
                        st.stop()
                    result = analyze_text(client, text)
                st.session_state[f"page_brief::{sel}"] = result
            except Exception as e:
                show_error(e)


def _render_brief(brief: dict, sel: str, doc_kind) -> None:
    if brief.get("company_name"):
        st.markdown(f"### {brief['company_name']}")
    if brief.get("page_purpose"):
        st.write(brief["page_purpose"])

    chip_bits = []
    if brief.get("page_intent"):
        chip_bits.append(f"**Intent:** {brief['page_intent']}")
    if brief.get("pricing_signal"):
        chip_bits.append(f"**Pricing:** {brief['pricing_signal']}")
    if brief.get("tone"):
        chip_bits.append(f"**Tone:** {brief['tone']}")
    if chip_bits:
        st.caption(" · ".join(chip_bits))

    st.divider()

    if brief.get("sales_talking_points"):
        st.markdown("**Sales Talking Points**")
        for item in brief["sales_talking_points"]:
            st.markdown(f"- {item}")
    if brief.get("outreach_recommendation"):
        st.markdown("**Outreach Recommendation**")
        st.write(brief["outreach_recommendation"])

    st.divider()

    if brief.get("target_audience"):
        st.markdown("**Target Audience**")
        st.write(brief["target_audience"])
    if brief.get("pain_points_addressed"):
        st.markdown("**Pain Points Addressed**")
        for item in brief["pain_points_addressed"]:
            st.markdown(f"- {item}")
    if brief.get("differentiators"):
        st.markdown("**Differentiators**")
        for item in brief["differentiators"]:
            st.markdown(f"- {item}")
    if brief.get("key_value_propositions"):
        st.markdown("**Key Value Propositions**")
        for item in brief["key_value_propositions"]:
            st.markdown(f"- {item}")

    if brief.get("promotional_offers") is not None:
        st.markdown("**Promotional Offers**")
        offers = brief["promotional_offers"] or []
        if not offers:
            st.caption("_(none found)_")
        else:
            for o in offers:
                v = o.get("value", "")
                cond = o.get("condition", "")
                cta = o.get("cta", "")
                bits = [f"**{v}**"] if v else []
                if cond:
                    bits.append(cond)
                if cta:
                    bits.append(f"_CTA: {cta}_")
                st.markdown("- " + " — ".join(bits))

    if brief.get("proof_points") is not None:
        st.markdown("**Proof Points**")
        points = brief["proof_points"] or []
        if not points:
            st.caption("_(none found)_")
        else:
            for p in points:
                m = p.get("metric", "")
                c = p.get("claim", "")
                src = p.get("source", "")
                line = f"- **{m}** {c}" if m else f"- {c}"
                if src:
                    line += f" _({src})_"
                st.markdown(line)

    if brief.get("calls_to_action"):
        st.markdown("**Calls to Action**")
        for item in brief["calls_to_action"]:
            st.markdown(f"- {item}")

    if brief.get("visual_brand_cues"):
        st.markdown("**Visual Brand Cues**")
        st.write(brief["visual_brand_cues"])

    st.divider()
    st.download_button(
        "Download JSON",
        json.dumps(brief, indent=2),
        file_name=f"{Path(sel).stem if doc_kind(sel) == 'pdf' else 'page'}_brief.json",
    )
