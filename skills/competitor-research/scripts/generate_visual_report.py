#!/usr/bin/env python3
"""
Visual Report Generator — Competitor Research
Generates an interactive HTML dashboard + MD summary from competitor data.
Uses Chart.js for charts, custom CSS for styling.
"""

import json
import argparse
import os
from datetime import datetime
import html as html_module


def escape(text):
    """HTML-escape text."""
    return html_module.escape(str(text)) if text else ''


def generate_html_report(merged_data, top_data, niche_data, config, output_path):
    """Generate interactive HTML dashboard."""

    competitors = top_data.get('competitors', [])
    all_competitors = merged_data.get('competitors', [])
    keywords = merged_data.get('keywords_used', [])
    date = merged_data.get('generated_date', datetime.now().strftime('%Y-%m-%d'))

    # Prepare chart data
    brands = [escape(c.get('brand', '?')[:15]) for c in competitors]
    scores = [c.get('relevance_score', 0) for c in competitors]
    prices = [float(c.get('price', 0) or 0) for c in competitors]
    reviews = [int(c.get('review_count', 0) or 0) for c in competitors]
    bsrs = [int(c.get('bsr', 0) or 0) for c in competitors]
    ratings = [float(c.get('rating', 0) or 0) for c in competitors]

    avg_price = sum(prices) / len(prices) if prices else 0
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    avg_reviews = sum(reviews) / len(reviews) if reviews else 0
    avg_bsr = sum(bsrs) / len(bsrs) if bsrs else 0

    # Price distribution buckets
    price_buckets = {'$0-10': 0, '$10-15': 0, '$15-20': 0, '$20-30': 0, '$30+': 0}
    for p in prices:
        if p < 10: price_buckets['$0-10'] += 1
        elif p < 15: price_buckets['$10-15'] += 1
        elif p < 20: price_buckets['$15-20'] += 1
        elif p < 30: price_buckets['$20-30'] += 1
        else: price_buckets['$30+'] += 1

    # Rating distribution
    rating_buckets = {'4.0-4.3': 0, '4.3-4.5': 0, '4.5-4.7': 0, '4.7-4.9': 0, '4.9-5.0': 0}
    for r in ratings:
        if r < 4.3: rating_buckets['4.0-4.3'] += 1
        elif r < 4.5: rating_buckets['4.3-4.5'] += 1
        elif r < 4.7: rating_buckets['4.5-4.7'] += 1
        elif r < 4.9: rating_buckets['4.7-4.9'] += 1
        else: rating_buckets['4.9-5.0'] += 1

    # Niche summary
    niche_rows = ''
    if niche_data:
        for kw_data in niche_data:
            niche_rows += f"""
            <tr>
                <td class="kw-cell">{escape(kw_data.get('keyword', ''))}</td>
                <td>{kw_data.get('search_volume', 'N/A'):,}</td>
                <td>${kw_data.get('revenue', 0):,.0f}</td>
                <td>{kw_data.get('units', 0):,}</td>
                <td>${kw_data.get('avg_price', 0):.2f}</td>
                <td>{kw_data.get('avg_rating', 0)}</td>
            </tr>"""

    # Competitor table rows
    comp_rows = ''
    for i, c in enumerate(competitors):
        rank_class = 'rank-gold' if i < 3 else 'rank-silver' if i < 7 else ''
        comp_rows += f"""
        <tr class="{rank_class}">
            <td class="rank-num">#{i+1}</td>
            <td class="brand-cell">{escape(c.get('brand', ''))}</td>
            <td class="title-cell" title="{escape(c.get('title', ''))}">{escape(c.get('title', '')[:55])}{'...' if len(c.get('title','')) > 55 else ''}</td>
            <td>${float(c.get('price', 0) or 0):.2f}</td>
            <td>{int(c.get('bsr', 0) or 0):,}</td>
            <td><span class="rating-badge">{c.get('rating', 'N/A')}</span></td>
            <td>{int(c.get('review_count', 0) or 0):,}</td>
            <td><span class="score-badge">{c.get('relevance_score', 0)}</span></td>
            <td>{c.get('keyword_frequency', 0)}/3</td>
        </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Competitor Research Report — {date}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #0a0f1a;
    --surface: #111827;
    --surface-2: #1a2235;
    --border: #2a3550;
    --text: #e2e8f0;
    --text-dim: #8892a8;
    --accent: #3b82f6;
    --accent-2: #8b5cf6;
    --green: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --cyan: #06b6d4;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    font-family: 'DM Sans', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
}}

.container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}

/* Header */
.header {{
    background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 50%, #1a1040 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
}}
.header::before {{
    content: '';
    position: absolute;
    top: -50%; right: -20%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    pointer-events: none;
}}
.header h1 {{
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    margin-bottom: 0.5rem;
}}
.header .subtitle {{
    color: var(--text-dim);
    font-size: 0.95rem;
}}
.header .date {{ color: var(--accent); font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }}

/* KPI Cards */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}}
.kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    transition: transform 0.2s, border-color 0.2s;
}}
.kpi-card:hover {{
    transform: translateY(-2px);
    border-color: var(--accent);
}}
.kpi-label {{ font-size: 0.8rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
.kpi-value {{ font-size: 1.8rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
.kpi-value.blue {{ color: var(--accent); }}
.kpi-value.green {{ color: var(--green); }}
.kpi-value.amber {{ color: var(--amber); }}
.kpi-value.cyan {{ color: var(--cyan); }}
.kpi-value.purple {{ color: var(--accent-2); }}

/* Sections */
.section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}}
.section-title {{
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}
.section-title .icon {{ font-size: 1.2rem; }}

/* Charts */
.chart-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}}
.chart-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
}}
.chart-card h3 {{
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--text-dim);
}}
.chart-container {{ position: relative; width: 100%; }}

/* Table */
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
}}
thead th {{
    background: var(--surface-2);
    padding: 0.75rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-dim);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--border);
    position: sticky;
    top: 0;
}}
tbody td {{
    padding: 0.65rem 0.75rem;
    border-bottom: 1px solid rgba(42, 53, 80, 0.5);
    vertical-align: middle;
}}
tbody tr:hover {{ background: rgba(59, 130, 246, 0.05); }}
.rank-gold {{ background: rgba(245, 158, 11, 0.05) !important; }}
.rank-silver {{ background: rgba(59, 130, 246, 0.03) !important; }}
.rank-num {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--accent); }}
.brand-cell {{ font-weight: 600; white-space: nowrap; }}
.title-cell {{ color: var(--text-dim); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.kw-cell {{ font-weight: 600; color: var(--cyan); }}
.score-badge {{
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: white;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
}}
.rating-badge {{
    background: rgba(16, 185, 129, 0.15);
    color: var(--green);
    padding: 0.15rem 0.5rem;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
}}

/* Footer */
.footer {{
    text-align: center;
    padding: 2rem;
    color: var(--text-dim);
    font-size: 0.8rem;
}}

@media (max-width: 900px) {{
    .chart-grid {{ grid-template-columns: 1fr; }}
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
    <h1>Competitor Research Report</h1>
    <p class="subtitle">Hand Wipes Category — Top {len(competitors)} Competitors Analysis</p>
    <p class="date">{date} &bull; Keywords: {', '.join(keywords)}</p>
</div>

<!-- KPI Cards -->
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Total Competitors Found</div>
        <div class="kpi-value blue">{merged_data.get('unique_competitors', len(all_competitors))}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">After Filter</div>
        <div class="kpi-value green">{merged_data.get('after_filter', len(all_competitors))}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg Price (Top 20)</div>
        <div class="kpi-value amber">${avg_price:.2f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg Rating</div>
        <div class="kpi-value cyan">{avg_rating:.1f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg Reviews</div>
        <div class="kpi-value purple">{avg_reviews:,.0f}</div>
    </div>
</div>

<!-- Niche Overview -->
{"" if not niche_data else f'''
<div class="section">
    <div class="section-title"><span class="icon">📊</span> Niche Overview by Keyword</div>
    <table>
        <thead><tr>
            <th>Keyword</th><th>Search Volume</th><th>30-Day Revenue</th><th>Units Sold</th><th>Avg Price</th><th>Avg Rating</th>
        </tr></thead>
        <tbody>{niche_rows}</tbody>
    </table>
</div>
'''}

<!-- Charts -->
<div class="chart-grid">
    <div class="chart-card">
        <h3>Relevance Score — Top 20</h3>
        <div class="chart-container"><canvas id="scoreChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Price Distribution</h3>
        <div class="chart-container"><canvas id="priceDistChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Price vs Reviews (Bubble = Rating)</h3>
        <div class="chart-container"><canvas id="scatterChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Rating Distribution</h3>
        <div class="chart-container"><canvas id="ratingChart"></canvas></div>
    </div>
</div>

<!-- Competitor Table -->
<div class="section">
    <div class="section-title"><span class="icon">🏆</span> Top {len(competitors)} Competitors</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Rank</th><th>Brand</th><th>Product</th><th>Price</th><th>BSR</th><th>Rating</th><th>Reviews</th><th>Score</th><th>Keywords</th>
        </tr></thead>
        <tbody>{comp_rows}</tbody>
    </table>
    </div>
</div>

<div class="footer">
    Generated by Zoviro Competitor Research Skill &bull; {date}
</div>

</div>

<script>
const chartColors = {{
    blue: 'rgba(59, 130, 246, 0.85)',
    purple: 'rgba(139, 92, 246, 0.85)',
    cyan: 'rgba(6, 182, 212, 0.85)',
    green: 'rgba(16, 185, 129, 0.85)',
    amber: 'rgba(245, 158, 11, 0.85)',
    red: 'rgba(239, 68, 68, 0.85)',
    blueFade: 'rgba(59, 130, 246, 0.15)',
}};

Chart.defaults.color = '#8892a8';
Chart.defaults.borderColor = 'rgba(42, 53, 80, 0.5)';
Chart.defaults.font.family = "'DM Sans', sans-serif";

// Score bar chart
new Chart(document.getElementById('scoreChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(brands)},
        datasets: [{{
            data: {json.dumps(scores)},
            backgroundColor: {json.dumps(scores)}.map((s, i) => i < 3 ? chartColors.amber : i < 7 ? chartColors.blue : chartColors.purple),
            borderRadius: 4,
            barPercentage: 0.7,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            y: {{ beginAtZero: true, grid: {{ color: 'rgba(42,53,80,0.3)' }} }},
            x: {{ ticks: {{ maxRotation: 45 }}, grid: {{ display: false }} }}
        }}
    }}
}});

// Price distribution
new Chart(document.getElementById('priceDistChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(list(price_buckets.keys()))},
        datasets: [{{
            data: {json.dumps(list(price_buckets.values()))},
            backgroundColor: [chartColors.green, chartColors.cyan, chartColors.blue, chartColors.amber, chartColors.red],
            borderWidth: 2,
            borderColor: '#111827',
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{
            legend: {{ position: 'bottom', labels: {{ padding: 15 }} }}
        }}
    }}
}});

// Scatter: Price vs Reviews
new Chart(document.getElementById('scatterChart'), {{
    type: 'bubble',
    data: {{
        datasets: [{{
            label: 'Competitors',
            data: {json.dumps([{'x': prices[i], 'y': reviews[i], 'r': max(4, (ratings[i] - 4.0) * 20)} for i in range(len(competitors))])},
            backgroundColor: 'rgba(59, 130, 246, 0.4)',
            borderColor: 'rgba(59, 130, 246, 0.8)',
            borderWidth: 1,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ title: {{ display: true, text: 'Price ($)' }}, grid: {{ color: 'rgba(42,53,80,0.3)' }} }},
            y: {{ title: {{ display: true, text: 'Review Count' }}, grid: {{ color: 'rgba(42,53,80,0.3)' }} }}
        }}
    }}
}});

// Rating distribution
new Chart(document.getElementById('ratingChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(list(rating_buckets.keys()))},
        datasets: [{{
            data: {json.dumps(list(rating_buckets.values()))},
            backgroundColor: [chartColors.red, chartColors.amber, chartColors.cyan, chartColors.green, chartColors.blue],
            borderRadius: 6,
        }}]
    }},
    options: {{
        responsive: true,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            y: {{ beginAtZero: true, grid: {{ color: 'rgba(42,53,80,0.3)' }} }},
            x: {{ grid: {{ display: false }} }}
        }}
    }}
}});
</script>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"HTML report saved to: {output_path}")
    return output_path


def generate_md_report(merged_data, top_data, niche_data, output_path):
    """Generate Markdown summary report."""

    competitors = top_data.get('competitors', [])
    keywords = merged_data.get('keywords_used', [])
    date = merged_data.get('generated_date', datetime.now().strftime('%Y-%m-%d'))

    prices = [float(c.get('price', 0) or 0) for c in competitors]
    ratings = [float(c.get('rating', 0) or 0) for c in competitors]
    reviews = [int(c.get('review_count', 0) or 0) for c in competitors]

    md = f"""# Competitor Research Report

**Date:** {date}
**Keywords:** {', '.join(keywords)}
**Competitors Found:** {merged_data.get('unique_competitors', '?')} unique → {merged_data.get('after_filter', '?')} after filter → Top {len(competitors)} selected

## Market Overview

| Metric | Top {len(competitors)} Average |
|--------|------|
| Price | ${sum(prices)/len(prices):.2f} |
| Rating | {sum(ratings)/len(ratings):.1f} |
| Reviews | {sum(reviews)//len(reviews):,} |

"""

    if niche_data:
        md += "## Niche Data by Keyword\n\n"
        md += "| Keyword | Search Volume | Revenue | Units | Avg Price |\n"
        md += "|---------|--------------|---------|-------|-----------|\n"
        for kw in niche_data:
            md += f"| {kw.get('keyword','')} | {kw.get('search_volume', 'N/A'):,} | ${kw.get('revenue', 0):,.0f} | {kw.get('units', 0):,} | ${kw.get('avg_price', 0):.2f} |\n"
        md += "\n"

    md += f"## Top {len(competitors)} Competitors\n\n"
    md += "| # | Brand | Price | BSR | Rating | Reviews | Score |\n"
    md += "|---|-------|-------|-----|--------|---------|-------|\n"

    for i, c in enumerate(competitors):
        md += f"| {i+1} | {c.get('brand', '')} | ${float(c.get('price', 0) or 0):.2f} | {int(c.get('bsr', 0) or 0):,} | {c.get('rating', '')} | {int(c.get('review_count', 0) or 0):,} | {c.get('relevance_score', 0)} |\n"

    md += f"\n---\n*Generated by Zoviro Competitor Research Skill — {date}*\n"

    with open(output_path, 'w') as f:
        f.write(md)

    print(f"MD report saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate visual competitor research report')
    parser.add_argument('--merged', required=True, help='Path to merged JSON')
    parser.add_argument('--top', required=True, help='Path to top competitors JSON')
    parser.add_argument('--niche', default=None, help='Path to niche data JSON (optional)')
    parser.add_argument('--config', default=None, help='Path to config.json')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    args = parser.parse_args()

    with open(args.merged) as f:
        merged = json.load(f)
    with open(args.top) as f:
        top = json.load(f)
    niche = None
    if args.niche and os.path.exists(args.niche):
        with open(args.niche) as f:
            niche = json.load(f)
    config = {}
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)
    date = merged.get('generated_date', datetime.now().strftime('%Y-%m-%d'))

    html_path = os.path.join(args.output_dir, f'Competitor_Report_{date}.html')
    md_path = os.path.join(args.output_dir, f'Competitor_Report_{date}.md')

    generate_html_report(merged, top, niche, config, html_path)
    generate_md_report(merged, top, niche, md_path)
