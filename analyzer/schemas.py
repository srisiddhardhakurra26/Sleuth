from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class PromotionalOffer(BaseModel):
    value: str = Field(..., description='dollar/credit/discount amount, e.g. "$500 in Ad Credit", "30-day free trial"')
    condition: str = Field(..., description='qualifier, e.g. "when you spend $500", "for new accounts" — empty if unconditional')
    cta: str = Field(..., description='nearby call-to-action button text, e.g. "Get Started" — empty if none')


class ProofPoint(BaseModel):
    metric: str = Field(..., description='quantitative claim, e.g. "51%", "+46%", "2.5x", "10M users"')
    claim: str = Field(..., description='what the metric is about, e.g. "of online purchasing discussions are on Reddit"')
    source: str = Field(..., description='citation if shown, e.g. "footnote 4", "Forrester 2024" — empty if uncited')


class PageBrief(BaseModel):
    company_name: str = Field(..., description="company or brand name")
    page_purpose: str = Field(
        ...,
        description="1-2 sentences: what this page is for and what action it pushes the reader toward",
    )
    page_intent: str = Field(
        ...,
        description=(
            'one of: "lead_gen", "product_education", "pricing", "trial_signup", '
            '"case_study", "comparison", "support", "events", "general_marketing"'
        ),
    )
    target_audience: str = Field(
        ...,
        description=(
            "who this page is speaking to — be specific by role, company size, and use case "
            "(e.g., 'mid-market marketing leaders evaluating ad platforms', not 'businesses')"
        ),
    )
    tone: str = Field(..., description="1-3 words: e.g., formal, casual, technical, aspirational, urgent")
    pricing_signal: str = Field(
        ...,
        description=(
            'one of: "free", "freemium", "trial", "contact_sales", "self_serve_paid", '
            '"enterprise", "unclear"'
        ),
    )
    key_value_propositions: List[str] = Field(
        ..., description="3-5 core claims this page makes about the product or company"
    )
    pain_points_addressed: List[str] = Field(
        ...,
        description=(
            "specific problems, frustrations, or jobs-to-be-done this page promises to solve — "
            "phrase as the customer's pain, not the company's solution"
        ),
    )
    differentiators: List[str] = Field(
        ...,
        description=(
            "explicit or implied claims of what makes them different from competitors — "
            "what they have/do that others don't"
        ),
    )
    promotional_offers: List[PromotionalOffer] = Field(
        ..., description="every monetary or trial-based incentive on the page"
    )
    proof_points: List[ProofPoint] = Field(
        ..., description="every numeric stat used to persuade (percentages, multipliers, user counts)"
    )
    calls_to_action: List[str] = Field(
        ..., description="every CTA button/link visible on the page, verbatim"
    )
    visual_brand_cues: str = Field(
        ...,
        description="color palette, imagery, typography — empty string if no image/screenshot was provided",
    )
    sales_talking_points: List[str] = Field(
        ...,
        description=(
            "3-5 specific, concrete things a sales rep should mention or ask about when "
            "reaching out — drawn directly from THIS page's content, not generic"
        ),
    )
    outreach_recommendation: str = Field(
        ...,
        description=(
            "1-2 sentences: what the page suggests about how to approach this prospect "
            "(channel, tone, pace). E.g., 'Heavy self-serve focus — start with a low-friction "
            "email about the free trial, not a sales call.'"
        ),
    )


# Back-compat alias preserved from the monolithic version.
BrandAnalysis = PageBrief


class ImageCaption(BaseModel):
    description: str = Field(..., description="1-2 sentence factual description of what's in the image")
    visible_text: str = Field(..., description="any text/numbers/logos visible in the image, verbatim — empty if none")
    likely_purpose: str = Field(
        ...,
        description='one of: "logo", "hero", "product_shot", "infographic", "icon", "headshot", "screenshot", "decorative"',
    )
