# GraphOne Intelligence Graph — Data Pipeline
**Author:** Sudhanshu Raj Yadav | **Submitted:** August 2026next

A multi-vertical data ingestion pipeline for the AI/venture ecosystem: research papers,
startups, products, jobs, and news — with LLM-based structuring and entity resolution.

## 📊 Output Summary

| Vertical | Records | Notes |
|---|---|---|
| Research Papers | 1,151 | Includes live GitHub star counts |
| Products | 1,100 | LLM-classified pricing model |
| Startups | 1,096 | Derived from Product Hunt maker data |
| Jobs | 175 | Strictly <24hr fresh, 2 job boards |
| News | 26 | Strictly <24hr fresh, 5 RSS sources |
| Entity Mapping Log | 1,096 | Raw → canonical name resolution |

**Live Google Sheet:** https://docs.google.com/spreadsheets/d/1DUeigXMilxhCwlkSZHnsQdPtswxztS5UHmfuJ8H11eI

## 🏗️ Architecture Overview

COLLECTORS → NORMALIZER → LLM ENGINE → ENTITY RESOLVER → STORAGE

1. **Collectors** — async fetchers per vertical, using official APIs/datasets wherever
   possible instead of raw scraping (see Design Decisions below)
2. **Normalizer** — truncates/chunks long text before LLM calls to avoid 413 errors
3. **LLM Engine** — multi-tier fallback chain with exponential backoff + jitter
4. **Entity Resolver** — fuzzy-matches raw names against a canonical seed list
5. **Storage** — CSV → Google Sheets (demo); Postgres + Neo4j recommended for production
   (see architecture.pdf)

## 📁 Repo Structure
src/
papers_pipeline.py # Research papers: HF dataset + arXiv API + GitHub API
products_startups.py # Product Hunt API fetch + startup/product entity building
llm_fallback.py # Multi-tier LLM fallback chain (core orchestration engine)
entity_resolution.py # Canonical entity matching (rapidfuzz)
jobs_news.py # RemoteOK + Arbeitnow (jobs), RSS feeds (news)
sheets_export.py # Google Sheets upload
architecture.pdf
README.md


## ⚙️ Setup

### Requirements
pip install aiohttp requests tenacity rapidfuzz gspread google-auth datasets tiktoken
pip install google-generativeai groq openai feedparser pandas


### API Keys needed
- Gemini API key (aistudio.google.com)
- Groq API key (console.groq.com)
- GitHub Personal Access Token
- Product Hunt API (client_id + client_secret, api.producthunt.com/v2/oauth/applications)
- Google Cloud Service Account JSON (for Sheets export)

### Run order
1. `papers_pipeline.py` — no LLM needed, pulls from pre-existing HF paper↔code dataset
2. `products_startups.py` — fetches Product Hunt data, classifies pricing via LLM
3. `entity_resolution.py` — resolves startup names against canonical seed list
4. `jobs_news.py` — pulls fresh jobs/news, no LLM needed
5. `sheets_export.py` — pushes all CSVs to Google Sheets tabs

## 🔑 Key Design Decisions

**Why Product Hunt instead of scraping YC/Crunchbase directly?**
YC's directory disallows automated access via robots.txt. Rather than circumvent that,
we used Product Hunt's official API (ToS-compliant, structured, rate-limit-documented)
as the source for both Products and Startups — each product's maker/company doubles as
the startup entity. `employeeCount` is honestly left null since Product Hunt doesn't
expose it, rather than hallucinating a value.

**Why arXiv + a pre-linked paper↔code dataset instead of scraping Papers with Code?**
We used the `pwc-archive/links-between-paper-and-code` dataset (HuggingFace) as a seed
list of paper↔GitHub links, then enriched each with live data from the official arXiv
API and GitHub API. This avoids scraping entirely for this vertical while still
satisfying the "every record traces to a real source URL" requirement.

**LLM fallback chain — real-world resilience**
During development we hit, and handled, three distinct real failure modes:
- Deprecated model names (404s) → fixed by switching to current model IDs
- Daily token quota exhaustion (429s) → fixed by rotating providers and reducing
  batch-call volume
- Upstream shared-pool congestion (429s) → fixed with retry + backoff + jitter
This is documented in more detail in `architecture.pdf`.

**Jobs/News freshness**
Both use RSS/JSON APIs with structured publish timestamps rather than scraping +
heuristic date parsing, wherever a reliable source offered it — reducing false
positives on the strict 24-hour freshness requirement.

## ⚠️ Known Limitations (honest disclosure)
- `employeeCount` for startups is null (not exposed by Product Hunt) rather than guessed
- Entity resolution seed list covers 50 well-known startups; long-tail startups are
  left as their raw name (not force-matched)
- Jobs/News counts reflect genuinely fresh (<24h) content at time of run, not padded
  to a target number






























