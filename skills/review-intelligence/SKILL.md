# Review Intelligence Skill

## Purpose
Analyze competitor product reviews to extract actionable insights: customer pain points, product strengths/weaknesses, feature demands, and sentiment patterns. Feeds into listing optimization, PPC strategy, and product development decisions.

## Required Inputs
1. **H10 Review Export CSV** — from Helium 10 Review Insights / Chroma extension
   - Columns expected: `ASIN`, `Rating`, `Review Title`, `Review Text`, `Date`, `Verified Purchase`, `Helpful Votes`
   - Can also accept manual review CSVs with similar structure
2. **config.json** — product context (our ASIN, keywords, category)

## Workflow

```
Input (H10 Review CSVs)
    ↓
Step 1: Parse & Clean Reviews
    → parse_reviews.py
    → Normalize columns, deduplicate, validate
    ↓
Step 2: Sentiment & Theme Analysis
    → analyze_reviews.py
    → Sentiment scoring per review
    → Topic/theme extraction (NLP keyword clustering)
    → Pain point identification
    → Feature demand mapping
    ↓
Step 3: Competitive Review Comparison
    → compare_reviews.py
    → Our reviews vs competitor reviews
    → Rating distribution comparison
    → Theme frequency comparison
    → Strength/weakness matrix
    ↓
Step 4: Generate Report
    → generate_review_report.py
    → HTML interactive dashboard + MD summary
    → Actionable insights for listing/PPC/product
```

## Output Files
- `review_analysis_{date}.json` — full analysis data
- `Review_Intelligence_Report_{date}.html` — interactive dashboard
- `Review_Intelligence_Report_{date}.md` — markdown summary

## Data Flow (Downstream)
- **Listing Optimization** → pain points become bullet point angles, feature demands inform title keywords
- **PPC Optimization** → sentiment keywords become targeting opportunities, negative sentiment terms to avoid
- **Competitor Research** → review scores feed into competitor scoring, weakness matrix identifies market gaps
- **Product Development** → feature demand trends, quality issue patterns

## How to Run

### Manual Mode (H10 CSV)
```
Step 1: Export reviews from H10 Review Insights for target ASINs
Step 2: Save CSV files to Downloads/ folder
Step 3: Run parse → analyze → compare → report pipeline
```

### Quick Start
```bash
# Parse H10 review exports
python scripts/parse_reviews.py --input ../../../Downloads/reviews_*.csv --output ../../data/reviews/

# Analyze reviews (sentiment + themes)
python scripts/analyze_reviews.py --input ../../data/reviews/parsed_reviews.json --output ../../data/reviews/

# Compare our reviews vs competitors
python scripts/compare_reviews.py --our-asin B0CR5D91N2 --input ../../data/reviews/review_analysis.json --output ../../data/reviews/

# Generate visual report
python scripts/generate_review_report.py --input ../../data/reviews/ --output-dir ../../../../
```

## Review Themes to Extract
1. **Product Quality** — durability, effectiveness, texture, scent
2. **Packaging** — individual wrapping, resealable, travel-friendly, quantity
3. **Value** — price perception, quantity per pack, cost per wipe
4. **Use Case** — travel, gym, office, medical, childcare
5. **Skin Sensitivity** — irritation, moisturizing, alcohol content, fragrance
6. **Comparison** — vs brand X, vs hand sanitizer liquid, vs soap
7. **Purchase Intent** — repeat purchase, gifting, bulk buying
