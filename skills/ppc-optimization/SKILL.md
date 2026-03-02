---
name: ppc-optimization
description: "Amazon PPC advertising optimization for Zoviro products. Analyzes search term reports, builds keyword strategies (exact/phrase/broad), designs campaign structures, identifies wasted spend, recommends bid adjustments, and optimizes ACOS. Uses H10 Cerebro keyword data + Seller Central search term & advertising reports. Trigger on: PPC optimization, PPC strategy, advertising optimization, ACOS optimization, search term report, keyword bidding, campaign structure, ad spend, PPC audit, sponsored products, sponsored brands."
---

# PPC Optimization Skill — Zoviro

Full-stack Amazon PPC optimization: keyword strategy, campaign structure, search term analysis, and ACOS optimization.

## Required Inputs

1. **ASIN** — the Zoviro product ASIN to optimize PPC for
2. **Keywords** — 3 primary keywords (same as competitor research)
3. **Search Term Report** — one of:
   - **API Mode (recommended)**: Ads API auto-pulls search term report → `data_fetcher.get_search_term_report()`
   - **Manual Mode**: CSV from Seller Central → Reports → Advertising Reports → Search Term Report
4. **Cerebro Keyword Data** (CSV from H10) — keyword volumes and competitor ranks
5. **Competitor Research Data** (optional) — `top_{date}.json` from competitor-research skill

## Prerequisites

- **Data Source (choose one):**
  - **API Mode (recommended)**: SP API + Ads API credentials configured in `.env` → fully automated data pull
  - **Manual Mode**: Seller Central access + manual CSV downloads
- H10 Cerebro data for our ASIN and ideally top 3-5 competitor ASINs
- At least 30 days of PPC data (60+ days preferred for trend analysis)

### API Mode Quick Start
```bash
# Test API connections
python keyword-automation/api/data_fetcher.py --test --env-file keyword-automation/api/.env

# Pull PPC data (search terms + campaign structure + performance)
python keyword-automation/api/data_fetcher.py --pull-all B0CR5D91N2 --days 60 \
  --output-dir keyword-automation/data/ppc
```
This replaces manual CSV downloads and provides cleaner, more complete data.

## Workflow Overview

```
Input (ASIN + Keywords + Search Term Report + Cerebro Data)
→ Step 1: Parse & Clean Search Term Report
→ Step 2: Keyword Research & Prioritization (Cerebro)
→ Step 3: Search Term Performance Analysis
→ Step 4: Campaign Structure Design
→ Step 5: Bid Strategy & Budget Allocation
→ Step 6: Negative Keyword Identification
→ Step 7: Output Report (XLSX with full PPC plan)
```

## Step-by-Step Execution

### Step 1: Parse & Clean Search Term Report

Process the Seller Central search term report CSV:

```bash
python keyword-automation/skills/ppc-optimization/scripts/parse_search_terms.py \
  --input "Downloads/{search_term_report}.csv" \
  --output "data/ppc/{date}_search_terms_clean.json"
```

The script:
- Parses Seller Central CSV format (handles multiple campaign/ad group rows)
- Cleans search terms (lowercase, trim, deduplicate)
- Calculates per-term metrics: ACOS, conversion rate, CPC, spend efficiency
- Flags search terms as: converting, high-impression-no-sale, high-spend-no-sale
- Identifies auto-campaign discovered terms worth promoting

Key calculated fields:
- **ACOS** = Spend / Sales × 100
- **Conversion Rate** = Orders / Clicks × 100
- **CPC** = Spend / Clicks
- **Revenue Per Click** = Sales / Clicks
- **Impression Share** (estimated) = Impressions / Search Volume (from Cerebro)

### Step 2: Keyword Research & Prioritization

Merge Cerebro keyword data with search term performance:

```bash
python keyword-automation/skills/ppc-optimization/scripts/keyword_research.py \
  --cerebro-csv "Downloads/{cerebro_csv}" \
  --search-terms "data/ppc/{date}_search_terms_clean.json" \
  --config "keyword-automation/config.json" \
  --output "data/ppc/{date}_keyword_priorities.json"
```

Analysis:
1. **Keyword Opportunity Matrix** — map each keyword by: Search Volume × Competition × Current Performance
2. **Competitor Keyword Gaps** — keywords competitors rank for organically that we only have via PPC (or don't target at all)
3. **Keyword Cannibalization** — same keyword targeted in multiple campaigns/match types inefficiently
4. **Long-tail Discovery** — 3-5 word phrases with good conversion rate from auto campaigns

Priority scoring formula:
```
PPC_Priority = (SV_score × 0.25) + (conversion_score × 0.30) + (competition_score × 0.20) + (relevance_score × 0.25)
```

Keyword tiers:
- **Tier 1 (Exact)**: High volume + proven conversion → exact match, aggressive bid
- **Tier 2 (Phrase)**: Medium volume + relevant → phrase match, moderate bid
- **Tier 3 (Broad)**: Discovery/long-tail → broad match, conservative bid
- **Tier 4 (Negative)**: Irrelevant or unprofitable → add as negatives

### Step 3: Search Term Performance Analysis

Deep analysis of existing PPC performance:

```bash
python keyword-automation/skills/ppc-optimization/scripts/performance_analysis.py \
  --search-terms "data/ppc/{date}_search_terms_clean.json" \
  --keyword-priorities "data/ppc/{date}_keyword_priorities.json" \
  --target-acos 30 \
  --output "data/ppc/{date}_performance_analysis.json"
```

Analysis dimensions:

1. **ACOS Distribution**:
   - Below target ACOS (profitable) — maintain or scale
   - At target ACOS — optimize bids
   - Above target ACOS — reduce bids or pause
   - No sales — evaluate for negatives

2. **Spend Efficiency Quadrants**:
   - High spend + High sales = ✅ Winners (scale up)
   - High spend + Low sales = ⚠️ Bleeders (optimize or cut)
   - Low spend + High sales = 🌟 Hidden gems (increase budget)
   - Low spend + Low sales = 🔍 Monitor (need more data)

3. **Match Type Performance**:
   - Auto vs Manual performance comparison
   - Exact vs Phrase vs Broad efficiency
   - Recommended match type transitions

4. **Time-Based Trends** (if multi-period data available):
   - ACOS trend over time
   - CPC trend (bidding pressure)
   - Conversion rate changes

### Step 4: Campaign Structure Design

Generate recommended campaign architecture:

```bash
python keyword-automation/skills/ppc-optimization/scripts/campaign_structure.py \
  --keyword-priorities "data/ppc/{date}_keyword_priorities.json" \
  --performance "data/ppc/{date}_performance_analysis.json" \
  --product-config "keyword-automation/config.json" \
  --asin "{our_asin}" \
  --output "data/ppc/{date}_campaign_structure.json"
```

Recommended campaign structure for each ASIN:

**Sponsored Products (SP):**
```
Campaign: SP - {Product} - Exact (Top Performers)
  Ad Group 1: Brand Keywords (exact match)
  Ad Group 2: Category Keywords (exact match)
  Ad Group 3: Competitor Targeting (exact match)

Campaign: SP - {Product} - Research (Phrase + Broad)
  Ad Group 1: Category Keywords (phrase match)
  Ad Group 2: Long-tail Keywords (broad match)

Campaign: SP - {Product} - Auto
  Ad Group 1: Close Match
  Ad Group 2: Loose Match
  Ad Group 3: Substitutes
  Ad Group 4: Complements
```

**Sponsored Brands (SB):** (if eligible)
```
Campaign: SB - {Brand} - Category
  Top-of-search headline ad with top 3 products

Campaign: SB - {Brand} - Video
  Product video ad targeting top converting keywords
```

Each campaign includes:
- Daily budget recommendation
- Default bid per ad group
- Keyword list with individual bid suggestions
- Negative keyword list (cross-campaign negatives)

### Step 5: Bid Strategy & Budget Allocation

Calculate optimal bids and budget distribution:

```bash
python keyword-automation/skills/ppc-optimization/scripts/bid_strategy.py \
  --performance "data/ppc/{date}_performance_analysis.json" \
  --keyword-priorities "data/ppc/{date}_keyword_priorities.json" \
  --campaign-structure "data/ppc/{date}_campaign_structure.json" \
  --target-acos 30 \
  --daily-budget 50 \
  --output "data/ppc/{date}_bid_strategy.json"
```

Bid calculation formula:
```
Suggested Bid = (Target ACOS / 100) × Average Selling Price × Conversion Rate
```

With adjustments:
- **Placement modifier**: +20-50% for top-of-search (typically higher conversion)
- **New keyword modifier**: Start at 80% of calculated bid, ramp up with data
- **Competition modifier**: +10-20% for high-competition keywords
- **Time-of-day modifier**: (if sufficient data) adjust for peak conversion hours

Budget allocation:
- 50-60% to Exact match (proven converters)
- 20-25% to Phrase match (expansion)
- 10-15% to Broad/Auto (discovery)
- 5-10% to Sponsored Brands (if applicable)

### Step 6: Negative Keyword Identification

Identify keywords to add as negatives:

```bash
python keyword-automation/skills/ppc-optimization/scripts/negative_keywords.py \
  --search-terms "data/ppc/{date}_search_terms_clean.json" \
  --performance "data/ppc/{date}_performance_analysis.json" \
  --config "keyword-automation/config.json" \
  --output "data/ppc/{date}_negatives.json"
```

Negative keyword sources:
1. **Irrelevant terms**: Search terms with clicks but 0% relevance to product
   - Category mismatches (e.g., "dog wipes" for hand wipes)
   - Wrong product type (e.g., "spray" when selling wipes)
   - Wrong use case (e.g., "industrial" for consumer product)

2. **Unprofitable terms**: >2× target ACOS with 20+ clicks and 0 orders
   - Only add as negative after sufficient data (minimum 15-20 clicks)

3. **Competitor brand terms**: If not intentionally targeting competitors
   - Other brand names appearing in auto campaigns

4. **Cross-campaign negatives**: Prevent keyword cannibalization
   - Exact match winners → add as negative exact in phrase/broad campaigns
   - Prevents lower-match campaigns from stealing impressions

Output: negative keyword list organized by:
- Campaign-level negatives
- Ad group-level negatives
- Negative exact vs negative phrase recommendations

### Step 7: Output Report

Generate comprehensive XLSX report:

```bash
python keyword-automation/skills/ppc-optimization/scripts/generate_ppc_xlsx.py \
  --search-terms "data/ppc/{date}_search_terms_clean.json" \
  --keyword-priorities "data/ppc/{date}_keyword_priorities.json" \
  --performance "data/ppc/{date}_performance_analysis.json" \
  --campaign-structure "data/ppc/{date}_campaign_structure.json" \
  --bid-strategy "data/ppc/{date}_bid_strategy.json" \
  --negatives "data/ppc/{date}_negatives.json" \
  --output "PPC_Optimization_{product_name}_{date}.xlsx"
```

Output XLSX has 7 sheets:

1. **PPC Dashboard** — KPI summary (total spend, sales, ACOS, orders, CPC, CVR), trend indicators, top/bottom 5 keywords
2. **Keyword Strategy** — all keywords with tier, match type, suggested bid, expected impressions, priority score
3. **Search Term Analysis** — full search term report with performance metrics, quadrant classification, recommendations
4. **Campaign Structure** — recommended campaigns, ad groups, keywords per group, budgets, bids
5. **Bid Recommendations** — per-keyword bid adjustments with rationale (increase/decrease/maintain)
6. **Negative Keywords** — organized by campaign with match type (negative exact/phrase)
7. **Action Items** — prioritized list of changes with expected ACOS impact

Save the final XLSX to the workspace folder.

## Data Flow Integration

```
Competitor Research → provides competitor list + market context
       ↓
Listing Optimization → provides keyword priorities + listing quality
       ↓
PPC Optimization (this skill) → uses all keyword data for ad targeting
       ↓
Output: Campaign structure + bid strategy + keyword lists ready for Seller Central upload
```

## Key Metrics & Targets

| Metric | Definition | Target Range |
|--------|-----------|-------------|
| ACOS | Ad Spend / Ad Sales × 100 | 15-35% (varies by margin) |
| TACOS | Total Ad Spend / Total Sales × 100 | 8-15% |
| CVR | Orders / Clicks × 100 | 10-20% for wipes |
| CPC | Spend / Clicks | $0.50-$2.00 typical |
| CTR | Clicks / Impressions × 100 | 0.3-0.5% typical |
| Impression Share | Our Impressions / Total Available | >20% for main keywords |

## Error Handling

- If search term report is too short (<14 days), warn that data may be insufficient for reliable analysis
- If Cerebro data missing, proceed with search term report only (reduced accuracy)
- If no current PPC data exists (new campaign), generate a launch campaign structure from keyword research
- If ACOS target not provided, default to 30% and note in report

## Seller Central Report Download Guide

### Search Term Report
1. Seller Central → Reports → Advertising Reports
2. Report Type: Search term
3. Report Period: Last 60 days (or custom)
4. Generate → Download CSV

### Bulk Operations (for campaign upload)
1. Seller Central → Advertising → Campaign Manager
2. Bulk Operations → Download bulk file
3. This provides current campaign structure for analysis
