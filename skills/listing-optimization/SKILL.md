---
name: listing-optimization
description: "Amazon listing optimization for Zoviro products. Analyzes competitor listings (title, bullets, description, A+ content, images, backend keywords), identifies keyword gaps and content opportunities, then generates optimized listing copy. Uses Helium 10 Cerebro keyword data + competitor research data + Amazon scraping. Trigger on: listing optimization, optimize listing, improve listing, listing copy, title optimization, bullet points, backend keywords, listing audit, listing review, SEO optimization."
---

# Listing Optimization Skill — Zoviro

Analyzes top competitor listings and generates optimized listing copy for any Zoviro product.

## Required Inputs

1. **ASIN** — the Zoviro product ASIN to optimize
2. **Keywords** — 3 primary keywords (same as used in competitor research)
3. **Competitor Research Data** — `top_{date}.json` from the competitor-research skill (must be run first)
4. **Cerebro Keyword Data** (optional but recommended) — exported CSV from H10 Cerebro for our ASIN and/or top competitor ASINs

## Prerequisites

- Competitor Research Skill completed for this ASIN (provides top 15-20 competitors with revenue/BSR data)
- **Data Source (choose one):**
  - **API Mode (recommended)**: SP API credentials configured in `.env` file → runs `data_fetcher.pull_all_data()` for automatic listing data
  - **Browser Mode**: Chrome browser connected + H10 logged in → manual scraping
- H10 Cerebro keyword data (CSV export) — ideally for our ASIN + top 3-5 competitor ASINs

### API Mode Quick Start
```bash
# Test API connection
python keyword-automation/api/data_fetcher.py --test --env-file keyword-automation/api/.env

# Pull listing data for our ASIN + competitors
python keyword-automation/api/data_fetcher.py --pull-all B0CR5D91N2 \
  --competitors B0KNYKQQV B00MH97XVG B0798XNVTS \
  --output-dir keyword-automation/data/listings
```
This replaces Step 1 + Step 2 (scraping).

## Workflow Overview

```
Input (ASIN + Keywords + Competitor Data)
→ Step 1: Scrape Our Current Listing
→ Step 2: Scrape Top 10 Competitor Listings
→ Step 3: Keyword Analysis (Cerebro Data)
→ Step 4: Gap Analysis & Scoring
→ Step 5: Generate Optimized Listing Copy
→ Step 6: Output Report (XLSX with analysis + copy)
```

## Step-by-Step Execution

### Step 1: Scrape Our Current Listing

Navigate to `https://www.amazon.com/dp/{our_ASIN}` and extract:

1. **Title** — full product title (within `<span id="productTitle">`)
2. **Bullet Points** — all feature bullets (within `<div id="feature-bullets">`)
3. **Product Description** — the description section (within `<div id="productDescription">` or A+ content area)
4. **A+ Content** — whether A+ exists, module types used (comparison table, image/text blocks, etc.)
5. **Images** — count of main images, infographic presence, lifestyle vs white background ratio
6. **Price** — current price
7. **Category & Subcategory** — from breadcrumb navigation
8. **Variations** — count and types (size, scent, etc.)

Use JavaScript extraction via `javascript_tool` for efficiency:
```javascript
// Extract listing data from Amazon product page
const data = {
  title: document.querySelector('#productTitle')?.innerText?.trim(),
  bullets: [...document.querySelectorAll('#feature-bullets li span.a-list-item')].map(el => el.innerText.trim()).filter(t => t.length > 5),
  price: document.querySelector('.a-price .a-offscreen')?.innerText?.trim(),
  rating: document.querySelector('#acrPopover')?.title?.match(/[\d.]+/)?.[0],
  reviewCount: document.querySelector('#acrCustomerReviewText')?.innerText?.match(/[\d,]+/)?.[0],
  imageCount: document.querySelectorAll('#altImages .a-button-thumbnail img').length,
  hasAPlus: !!document.querySelector('#aplus, #aplusProductDescription, .aplus-v2'),
  category: [...document.querySelectorAll('#wayfinding-breadcrumbs_feature_div a')].map(a => a.innerText.trim()),
  brand: document.querySelector('#bylineInfo')?.innerText?.replace('Brand: ', '').replace('Visit the ', '').replace(' Store', '').trim()
};
JSON.stringify(data);
```

Save raw data to `data/listings/{asin}_our_listing.json`.

### Step 2: Scrape Top 10 Competitor Listings

From the competitor research `top_{date}.json`, select the top 10 competitors by relevance_score. For each competitor:

1. Navigate to `https://www.amazon.com/dp/{competitor_asin}`
2. Extract same fields as Step 1 using the same JavaScript
3. Wait 3-5 seconds between pages to avoid throttling

Save all competitor listings to `data/listings/{date}_competitor_listings.json`.

Key data to capture per competitor:
- Title structure (word count, keyword placement, format pattern)
- Bullet point count and average length
- Keywords used in title and bullets
- A+ content presence and module types
- Image count and quality indicators
- Price positioning relative to ours

### Step 3: Keyword Analysis

Process Cerebro keyword data to identify:

1. **High-volume keywords** — SV ≥ 500 that we should target in title/bullets
2. **Competitor keyword coverage** — which keywords top competitors rank for that we don't
3. **Keyword placement analysis** — where top competitors place each keyword (title vs bullets vs description vs backend)
4. **Long-tail opportunities** — 3-5 word phrases with good SV but lower competition

Run the keyword analysis script:
```bash
python keyword-automation/skills/listing-optimization/scripts/analyze_keywords.py \
  --cerebro-csv "Downloads/{cerebro_csv_file}" \
  --our-asin "{our_asin}" \
  --competitor-listings "data/listings/{date}_competitor_listings.json" \
  --output "data/listings/{date}_keyword_analysis.json"
```

The script:
- Parses Cerebro CSV for keyword volume, rank, competing products
- Cross-references keywords against competitor title/bullet text
- Calculates a "keyword priority score" = SV × (1 / competition_density) × relevance_multiplier
- Groups keywords into: title-priority, bullet-priority, backend-priority, skip

### Step 4: Gap Analysis & Scoring

Compare our listing against top 10 competitors to identify gaps:

Run the analysis script:
```bash
python keyword-automation/skills/listing-optimization/scripts/gap_analysis.py \
  --our-listing "data/listings/{our_asin}_our_listing.json" \
  --competitor-listings "data/listings/{date}_competitor_listings.json" \
  --keyword-analysis "data/listings/{date}_keyword_analysis.json" \
  --output "data/listings/{date}_gap_analysis.json"
```

Analysis dimensions:
1. **Title Score** (0-100):
   - Keyword coverage: does title contain top 5 keywords?
   - Length optimization: 150-200 chars ideal for mobile + desktop
   - Structure: Brand + Key Benefit + Product Type + Size/Count + Differentiator
   - Readability: natural flow vs keyword stuffing

2. **Bullet Points Score** (0-100):
   - Keyword integration: top 20 keywords distributed across bullets
   - Benefit-first structure: leading with benefit, not feature
   - Length: 200-250 chars per bullet (sweet spot for readability)
   - Count: 5 bullets standard, all used?
   - Unique selling points highlighted

3. **Image Score** (0-100):
   - Image count (7+ ideal)
   - Infographic presence
   - Lifestyle images
   - Size/dimension images

4. **A+ Content Score** (0-100):
   - A+ exists?
   - Module variety (comparison table, brand story, image/text, banner)
   - Keyword presence in A+ text
   - Cross-sell integration

5. **Backend Keywords** (gap identification):
   - Keywords NOT in title/bullets but in Cerebro data
   - Spanish/alternate spellings
   - Common misspellings

6. **Overall Listing Quality Score** = weighted average:
   - Title (30%) + Bullets (25%) + Images (20%) + A+ (15%) + Backend (10%)

### Step 5: Generate Optimized Listing Copy

Based on the gap analysis and keyword priorities, generate:

Run the copy generator:
```bash
python keyword-automation/skills/listing-optimization/scripts/generate_copy.py \
  --gap-analysis "data/listings/{date}_gap_analysis.json" \
  --keyword-analysis "data/listings/{date}_keyword_analysis.json" \
  --our-listing "data/listings/{our_asin}_our_listing.json" \
  --config "keyword-automation/config.json" \
  --output "data/listings/{date}_optimized_copy.json"
```

Output includes:

1. **Optimized Title** (2-3 variations):
   - Version A: Maximum keyword coverage
   - Version B: Most readable/natural
   - Version C: Balanced approach (recommended)
   - Each title includes: char count, keywords included, readability note

2. **Optimized Bullet Points** (5 bullets):
   - Each bullet: benefit-first structure
   - Total keyword coverage across all 5 bullets
   - Suggested emoji/special char usage (if category standard)
   - Character count per bullet

3. **Backend Search Terms** (250 bytes max):
   - Keywords not already in title/bullets
   - Spanish translations of key terms
   - Common misspellings
   - Byte count validation

4. **Product Description** (if no A+ content):
   - HTML-formatted description
   - Keyword-rich but readable

5. **A+ Content Recommendations**:
   - Suggested module layout
   - Text content for each module
   - Comparison table structure (us vs category avg)

### Step 6: Output Report

Run the XLSX generator:
```bash
python keyword-automation/skills/listing-optimization/scripts/generate_listing_xlsx.py \
  --gap-analysis "data/listings/{date}_gap_analysis.json" \
  --keyword-analysis "data/listings/{date}_keyword_analysis.json" \
  --optimized-copy "data/listings/{date}_optimized_copy.json" \
  --our-listing "data/listings/{our_asin}_our_listing.json" \
  --competitor-listings "data/listings/{date}_competitor_listings.json" \
  --output "Listing_Optimization_{product_name}_{date}.xlsx"
```

Output XLSX has 5 sheets:

1. **Listing Scorecard** — our listing score vs top 10 competitor average, per dimension
2. **Keyword Analysis** — all keywords with SV, rank, placement (title/bullet/backend), priority tier
3. **Competitor Listing Comparison** — side-by-side title, bullet, image, A+ for top 10
4. **Optimized Copy** — all generated title variations, bullets, backend keywords, description
5. **Action Items** — prioritized list of changes with expected impact (High/Medium/Low)

Save the final XLSX to the workspace folder.

## Data Flow Integration

This skill depends on and feeds into other skills:

```
Competitor Research (upstream) → provides top competitor list + revenue data
                                    ↓
Listing Optimization (this skill) → generates optimized copy + keyword priorities
                                    ↓
PPC Optimization (downstream) → uses keyword analysis for ad targeting
```

## Error Handling

- If Cerebro data not available, proceed with competitor-only analysis (reduced keyword accuracy)
- If competitor listing returns 404 or unavailable, skip it (minimum 5 competitors needed)
- If our listing doesn't exist yet (new product), generate listing from scratch using competitor patterns
- If A+ content not accessible (requires brand registry), note in report and skip A+ scoring

## Amazon Listing Best Practices Reference

### Title Format (Health & Household)
`Brand Name + Key Benefit + Product Type + [Size/Count] + [Key Feature/Ingredient]`
- Max 200 characters (aim for 150-180)
- Front-load top 2-3 keywords in first 80 chars (mobile cutoff)
- Avoid ALL CAPS (Amazon policy)

### Bullet Point Format
- Lead with BENEFIT in caps, then feature detail
- 200-250 chars per bullet for optimal readability
- Include 3-4 keywords naturally per bullet
- Order: #1 main benefit, #2 key ingredient, #3 usage, #4 quality/safety, #5 value/guarantee

### Backend Search Terms
- 250 bytes max (not characters)
- No punctuation needed (space-separated)
- Don't repeat title/bullet words
- Include: misspellings, Spanish terms, abbreviations, synonyms
