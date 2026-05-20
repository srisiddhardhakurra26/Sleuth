---
title: Sleuth
emoji: 🕵️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Sleuth

Investigate any website or PDF — extract, brief, and chat with the content. Free tier only.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium         # one-time, ~150MB
```

## Run

```bash
streamlit run app.py
```

## API keys (paste into the sidebar)

- **Gemini** (required) — https://aistudio.google.com
- **LlamaParse** (optional) — https://cloud.llamaindex.ai

## Features

- **Extract & Compare** — run the same PDF through PyMuPDF, Gemini Vision, and LlamaParse side by side
- **Page Brief** — structured Pydantic-validated JSON brief for sales research (purpose, audience, pain points, differentiators, offers, proof points, talking points)
- **Chat / RAG** — single-doc full-context Q&A, or multi-doc retrieval-augmented Q&A with source citations
- **Images** — extract images from PDFs (PyMuPDF) or scraped pages (HTML parse), optionally captioned with Gemini Vision

## Project layout

```
analyzer/    Domain logic, no Streamlit UI
  client.py        Gemini client factory (cached)
  prompts.py       Prompt templates
  schemas.py       Pydantic models (PageBrief, ImageCaption, etc.)
  extractors.py    PDF text extractors + EXTRACTORS registry
  crawler.py       Playwright URL crawler + HTML media parser
  images.py        PDF image extraction + Gemini Vision captioning
  analysis.py      Page brief generation
  rag.py           Chunking, embedding, cosine search + RAGIndex class

views/       Streamlit UI layer (depends on analyzer, not vice versa)
  state.py         Session-state init, doc registry, doc_text helper
  sidebar.py       Sidebar inputs + crawled-URL list
  extract.py       Extract & Compare view
  brief.py         Page Brief view
  chat.py          Chat / RAG view
  images.py        Images view

app.py       Thin orchestrator — wires sidebar to view router
```
