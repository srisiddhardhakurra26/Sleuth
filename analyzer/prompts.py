ANALYSIS_PROMPT = (
    "You are helping a B2B sales rep do prospect research from a single web page. "
    "Be specific, concrete, and grounded in what's actually on the page — no generic filler. "
    "Extract EVERY promotional offer (credits, discounts, trials, free tiers) and EVERY "
    "proof point (percentages, multipliers, user counts, before/after stats). "
    "For pain_points_addressed, phrase them as the customer's pain ('struggling to attribute ad spend'), "
    "not the company's solution. "
    "For sales_talking_points, give the rep 3-5 specific hooks they could use in an outreach "
    "email — pulled from THIS page, not generic. "
    "For visual_brand_cues, describe only what you can actually see; if no image was provided, "
    "return an empty string."
)

GEMINI_VISION_EXTRACT_PROMPT = (
    "Extract ALL text content from this PDF as clean markdown. "
    "Preserve headings, lists, tables, and reading order. "
    "Include image captions and alt-text where present. "
    "Do NOT summarize, omit, or add commentary — return only the "
    "extracted content."
)

IMAGE_CAPTION_PROMPT = (
    "Describe this image factually in 1-2 sentences. "
    "List any visible text/numbers/logos verbatim. "
    "Classify its likely purpose on a website "
    '(one of: logo, hero, product_shot, infographic, icon, headshot, screenshot, decorative).'
)
