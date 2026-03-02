# Amazon Business Intelligence Platform

## What This Is

An internal Amazon seller intelligence platform for **Zoviro** (hand sanitizer / body wipes brand). It pulls data from Amazon SP API + Advertising API, runs analysis through independent skills, stores results in a three-tier data warehouse, and outputs token-optimized summaries for LLM consumption (OpenClaw agent or manual review).

## Project Structure

```
amazon-business-intelligence/
├── api/                    # Amazon API clients
│   ├── sp_api_client.py    # Selling Partner API (listings, catalog, reports)
│   ├── ads_api_client.py   # Advertising API v3 (campaigns, keywords, reports)
│   ├── data_fetcher.py     # Unified 7-step data puller
│   ├── auth.py             # CredentialManager (loads .env)
│   ├── exceptions.py       # Typed API exceptions
│   └── .env.template       # 9 credential placeholders
├── config/
│   ├── global.yaml         # Platform settings, timeouts, token limits
│   ├── brands/
│   │   └── zoviro.yaml     # 4 ASINs, keywords, competitor filters, scoring weights
│   └── workflows/
│       ├── daily.yaml      # PPC metrics (8 AM UTC)
│       ├── weekly.yaml     # Competitor + listing analysis (Mon 9 AM)
│       └── monthly.yaml    # Full deep dive + reviews (1st of month)
├── skills/                 # Independent skill modules
│   ├── base.py             # BaseSkill ABC + SkillInput/SkillOutput dataclasses
│   ├── competitor-research/
│   ├── listing-optimization/
│   ├── ppc-optimization/
│   └── review-intelligence/
├── data/                   # Three-tier data warehouse
│   ├── warehouse.py        # raw → processed → summaries (≤2000 tokens)
│   ├── summary_generator.py
│   └── (raw/, processed/, summaries/, snapshots/ created at runtime)
├── workflows/
│   └── orchestrator.py     # YAML-driven workflow runner
├── cli/
│   └── main.py             # CLI entry point
├── reports/                # Generated HTML/MD reports
└── tests/
```

## Credentials / Secrets

**CRITICAL: All secrets stay local. Never commit .env files.**

Credentials are loaded from a `.env` file (not in repo — gitignored). The file requires 9 variables:

```
SP_API_REFRESH_TOKEN, SP_API_CLIENT_ID, SP_API_CLIENT_SECRET,
SP_API_MARKETPLACE_ID (ATVPDKIKX0DER), SP_API_SELLER_ID,
ADS_API_PROFILE_ID (2916579953459482 for US),
ADS_API_CLIENT_ID, ADS_API_CLIENT_SECRET, ADS_API_REFRESH_TOKEN
```

See `api/.env.template` for the full template. The working `.env` currently lives at the project root or `api/.env`.

## Key Conventions

### Import Style
- **Within a package** (e.g., files inside `api/`): use relative imports (`from .sp_api_client import SPAPIClient`)
- **Across packages** (e.g., skill.py importing base): use absolute imports from repo root (`from skills.base import BaseSkill`)
- Repo root must be in `sys.path` — the CLI handles this automatically

### Skills Pattern
Every skill follows the same interface:
```python
class MySkill(BaseSkill):
    def execute(self, inputs: SkillInput) -> SkillOutput
    def validate_inputs(self, inputs: SkillInput) -> bool
    def generate_summary(self, data: dict, max_tokens: int = 2000) -> str
```
- `SkillInput`: asin, brand, config, context, upstream_data (from previous skill in chain)
- `SkillOutput`: status, skill_id, execution_time, timestamp, data, summaries, errors
- Each skill has: `SKILL.md` (docs), `skill.py` (class), `scripts/` (implementation modules)

### Data Warehouse Tiers
1. **raw/** — Direct API responses, timestamped JSON
2. **processed/** — Scored, analyzed, categorized data
3. **summaries/** — Token-optimized text files (≤2000 tokens / ~8000 chars) for LLM consumption

Summaries are the **only** data tier committed to git. Raw and processed are gitignored.

### Workflows
Defined in `config/workflows/*.yaml`. Each workflow chains skills with optional post-actions (save summaries, generate reports, send notifications). The orchestrator supports dry-run mode.

## Amazon API Gotchas

These were discovered through extensive debugging and are critical to preserve:

1. **SP Advertising API v3 requires versioned Content-Type AND Accept headers** — e.g., `application/vnd.spCampaign.v3+json` for campaigns. Both headers must match.
2. **Reports API has a 31-day max date range** — data_fetcher automatically caps to 31 days.
3. **S3 pre-signed URLs reject auth headers** — `download_report()` must NOT send Authorization headers when downloading from S3.
4. **Column name differences from v2 → v3**: `orders7d` → `purchases7d`, `keywordText` → `keyword`, `unitsSold7d` → `unitsSoldClicks7d`.
5. **`keywordBid` can be None** — always use `float(row.get('keywordBid', 0) or 0)`.
6. **Placement reports** use `groupBy: ['campaignPlacement']`, not a `placementClassification` column.
7. **Always clear `__pycache__`** after editing API client files during development.

## CLI Usage

```bash
# From repo root:
python cli/main.py test-api --env-file .env
python cli/main.py pull-data B0CR5D91N2 --days 31
python cli/main.py list-workflows
python cli/main.py run-workflow daily-ppc --dry-run
python cli/main.py list-skills
```

## Our Products (Zoviro)

| ASIN | Product | Category |
|------|---------|----------|
| B0CR5D91N2 | Tea Tree Hand Sanitizer Wipes 20ct (Pack of 10) | Hand Wipes |
| B0CR74VL95 | Jasmine Wipes 80ct (Pack of 6) | Body Wipes |
| B0CRSSGGYY | Lavender Wipes | Body Wipes |
| B0F6MN77BB | Sanitizing Wipes Bulk | Hand Wipes |

Target ACOS: 30% across all products. US marketplace only (ATVPDKIKX0DER).

## Development Notes

- Python 3.10+, dependencies: `requests`, `pyyaml`, `pydantic`
- No external ML libraries — sentiment analysis uses keyword-based NLP
- PPC classification: winner / marginal / bleeder / wasted (based on ACOS vs 30% target)
- Review intelligence parses Helium 10 Chroma CSV exports
- Token-optimized summaries target ≤2000 tokens for OpenClaw agent consumption
