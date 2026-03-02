---
name: competitor-research
description: "Amazon competitor research automation for Zoviro. Input a Zoviro ASIN + relevant search keywords, automatically discover and analyze 15-20 top competitors, output a structured XLSX document with niche overview, all competitors, top competitor details, and feature comparison. Uses Helium 10 ASIN Grabber and X-Ray via browser automation. Trigger on: competitor research, competitor analysis, find competitors, competitor XLSX, competitive landscape, who are my competitors, ASIN competitor map."
---

# Competitor Research Skill — Zoviro

Automates the full competitor discovery and analysis workflow for any Zoviro ASIN.

## Required Inputs

1. **ASIN** — the Zoviro product ASIN (e.g. B0CR5D91N2)
2. **Keywords** — 3 highly relevant search keywords that a buyer would use to find this exact product type. Keywords must be precise enough to surface direct competitors (not broad category terms).
   - Example ✅: "hand wipes", "hand sanitizer wipes", "hand wipes antibacterial"
   - Example ❌: "wipes", "antibacterial wipes", "body wipes" (too broad, pulls in unrelated categories)

If the ASIN is already in config.json with keywords defined, use those. If the user provides new keywords, update config.json first.

## Prerequisites

- Chrome browser connected via Claude in Chrome (zoviro research profile)
- Helium 10 account logged in with X-Ray Chrome extension active
- Config file at `keyword-automation/config.json` with product definitions
- Downloads folder accessible at the VM workspace path

## Workflow Overview

```
Input (ASIN + 3 Keywords) → Config Lookup → Amazon Search (per keyword) → H10 ASIN Grabber Export
→ Merge & Deduplicate & Filter → Score & Rank → Top 15-20 Detail Scrape → Generate XLSX
```

## Step-by-Step Execution

### Step 1: Config Lookup & Keyword Validation

Read `keyword-automation/config.json` to find the input ASIN's product info:
- Product name, category
- Primary keywords (provided by user or from config — must be 3 precise keywords)
- Competitor filter settings (title_exclude, title_boost)
- Chrome profile download path

**Critical**: If keywords are not provided and not in config, ask the user. Do NOT proceed with generic or broad keywords — keyword precision is the #1 factor in competitor accuracy.

If the ASIN is not in config, add it with the user-provided keywords and set up appropriate competitor_filter settings based on the product category.

### Step 2: Amazon Search + ASIN Grabber Export

For each primary keyword (typically 3):

1. Navigate to `https://www.amazon.com/s?k={keyword}` in the connected Chrome tab
2. Wait for page load and H10 X-Ray injection (the coral-colored summary bar appears)
3. Click **"Download ASINs"** button in the H10 X-Ray summary bar
4. The ASIN Grabber modal opens showing all products (100-150+)
5. Click **"Export"** → **"...as a CSV file"**
6. Wait for CSV to auto-download to the Downloads folder
7. Close the ASIN Grabber modal
8. Note: the CSV filename pattern is `asinGrabber{date}.csv`

Also capture the niche summary data visible in the H10 bar:
- Search Volume, Average BSR, Average Price, Average Rating, Page 1 Products count

Repeat for each keyword. Between keywords, wait 2-3 seconds to avoid rate limiting.

### Step 3: Merge and Deduplicate

Run the merge script:
```bash
python keyword-automation/skills/competitor-research/scripts/merge_asin_csvs.py \
  --downloads-dir "Downloads" \
  --our-asins "B0CR5D91N2,B0CR74VL95,B0CRSSGGYY,B0F6MN77BB" \
  --output "keyword-automation/data/competitors/merged_{date}.json"
```

This script:
- Finds all `asinGrabber*.csv` files from today in the Downloads folder
- Merges them, deduplicates by ASIN
- Removes Zoviro's own ASINs
- Tracks which keywords each competitor appeared in (keyword_frequency)
- Calculates a relevance_score based on: keyword_frequency, BSR, review count

### Step 4: Score and Select Top Competitors

Run the scoring script:
```bash
python keyword-automation/skills/competitor-research/scripts/score_competitors.py \
  --input "keyword-automation/data/competitors/merged_{date}.json" \
  --top-n 20 \
  --output "keyword-automation/data/competitors/top_{date}.json"
```

Scoring formula:
- keyword_frequency_score (0-40): how many search keywords this product appeared in
- bsr_score (0-25): lower BSR = higher score (log scale)
- review_score (0-20): more reviews = more established competitor
- rating_score (0-15): higher rating = stronger competitor

Select top 15-20 by score.

### Step 5: Detailed Data Collection (H10 X-Ray per product)

For each of the top 15-20 competitors:

1. Navigate to `https://www.amazon.com/dp/{ASIN}`
2. Wait for page load + H10 X-Ray data injection
3. Read the H10 Product Summary bar at top of product page which contains:
   - BSR (overall category + subcategory rank)
   - 30-Day Revenue and Unit Sales
   - Current Rating and review count
   - Listing Health Score
   - Top Keywords
4. Also extract from the Amazon page:
   - Full product title
   - Brand name
   - Price and price-per-unit
   - Fulfillment type (look for "Ships from Amazon" / "Sold by" section)
   - Number of product images (count image thumbnails on left)
   - Whether A+ Content exists (scroll to "Product description" section)
   - "Frequently bought together" products (potential complementary competitors)

The H10 data is inside DOM elements injected by the extension. Use `read_page` or `javascript_tool` to extract structured data from the H10 summary widget.

Key H10 DOM selectors (may vary by extension version):
- The Product Summary bar appears near the top with class containing "h10"
- Revenue/sales appear after clicking "Show Full Details" if not visible
- BSR shows as "Health & Hous... #21,369" format

Rate limiting: wait 3-5 seconds between product pages to avoid Amazon throttling.

### Step 6: Generate XLSX

Run the XLSX generator:
```bash
python keyword-automation/skills/competitor-research/scripts/generate_xlsx.py \
  --merged "keyword-automation/data/competitors/merged_{date}.json" \
  --detailed "keyword-automation/data/competitors/top_{date}.json" \
  --our-asin "{input_asin}" \
  --config "keyword-automation/config.json" \
  --output "Competitor_Research_{product_name}_{date}.xlsx"
```

Output XLSX has 4 sheets (see references/xlsx_structure.md for details):
1. **Niche Overview** — market-level summary per keyword searched
2. **All Competitors** — full deduplicated list (300-500 rows)
3. **Top Competitors** — detailed top 15-20 with revenue, units, LHS
4. **Feature Comparison** — side-by-side Zoviro vs Top 5

Save the final XLSX to the workspace folder so the user can access it.

## Error Handling

- If H10 X-Ray doesn't load on a page, wait 5 seconds and refresh. If still missing, skip that product and note it in the output.
- If ASIN Grabber export fails, try the XLSX export option instead.
- If a product page returns 404 or "Currently unavailable", skip it.
- If fewer than 10 competitors found after merge, expand to 4-5 keywords.

### Step 7 (Optional): Review Intelligence

If deeper competitor analysis is needed, use the **Review Intelligence** skill to analyze competitor product reviews:

1. Export reviews from H10 Review Insights / Chroma for our ASIN + top 5-10 competitor ASINs
2. Save review CSV files to Downloads folder
3. Run the review pipeline:

```bash
# Parse all review CSVs
python keyword-automation/skills/review-intelligence/scripts/parse_reviews.py \
  --input "Downloads/reviews_*.csv" \
  --output "keyword-automation/data/reviews/"

# Analyze sentiment + themes
python keyword-automation/skills/review-intelligence/scripts/analyze_reviews.py \
  --input "keyword-automation/data/reviews/parsed_reviews.json" \
  --output "keyword-automation/data/reviews/"

# Compare our reviews vs competitors
python keyword-automation/skills/review-intelligence/scripts/compare_reviews.py \
  --our-asin "{input_asin}" \
  --input "keyword-automation/data/reviews/review_analysis.json" \
  --output "keyword-automation/data/reviews/"

# Generate visual report
python keyword-automation/skills/review-intelligence/scripts/generate_review_report.py \
  --input "keyword-automation/data/reviews/" \
  --output-dir "./"
```

Review insights feed into:
- **Listing Optimization**: pain points → bullet point angles, feature demands → title keywords
- **PPC Optimization**: sentiment keywords → targeting opportunities
- **Product Development**: quality issues, feature gaps, trend identification

## Data Flow (Downstream Skills)

```
Competitor Research
    ├── → Listing Optimization (competitor listings + keywords)
    ├── → PPC Optimization (competitor ASIN targeting)
    ├── → Review Intelligence (competitor review analysis)
    └── → Future: Trend Analysis, Demand Forecasting, New Product Discovery
```

## Output Files

- `keyword-automation/data/competitors/merged_{date}.json` — raw merged competitor data
- `keyword-automation/data/competitors/top_{date}.json` — top competitors with detailed data
- `keyword-automation/data/reviews/review_analysis.json` — review sentiment & themes (if Step 7 run)
- `keyword-automation/data/reviews/review_comparison.json` — our vs competitor review comparison
- `Competitor_Research_{product}_{date}.xlsx` — final deliverable (saved to workspace)
- `Review_Intelligence_Report_{date}.html` — interactive review dashboard
- `Review_Intelligence_Report_{date}.md` — review summary
