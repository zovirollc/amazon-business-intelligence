#!/usr/bin/env python3
"""
Visual Report Generator — Listing Optimization
Generates an interactive HTML dashboard + MD summary from listing optimization data.
Uses Chart.js for charts, custom CSS for styling (matches competitor research report).
"""

import json
import argparse
import os
from datetime import datetime
import html as html_module


def escape(text):
    """HTML-escape text."""
    return html_module.escape(str(text)) if text else ''


def generate_html_report(gap_analysis, keyword_analysis, our_listing, competitor_listings, output_path):
    """Generate interactive HTML dashboard."""

    # Extract data from JSON files
    overall_score = gap_analysis.get('overall_score', 0)
    scores = gap_analysis.get('scores', {})
    title_score = scores.get('title', {}).get('score', 0)
    bullets_score = scores.get('bullets', {}).get('score', 0)
    images_score = scores.get('images', {}).get('score', 0)
    aplus_score = scores.get('aplus', {}).get('score', 0)
    backend_keywords = gap_analysis.get('backend_keywords', {})
    backend_bytes = backend_keywords.get('total_bytes_used', 0)
    recommendations = gap_analysis.get('recommendations', [])

    # Keywords data
    keywords_list = keyword_analysis.get('keywords', [])

    # Our listing data
    our_asin = gap_analysis.get('our_asin', our_listing.get('asin', 'N/A'))
    our_title = escape(our_listing.get('title', 'N/A'))
    our_brand = escape(our_listing.get('brand', 'N/A'))
    our_price = our_listing.get('price', 0)
    our_image_count = our_listing.get('imageCount', our_listing.get('image_count', 0))
    our_has_aplus = our_listing.get('hasAPlus', our_listing.get('has_a_plus', False))
    our_bullet_count = len(our_listing.get('bullets', []))

    # Competitor data
    competitors = competitor_listings if isinstance(competitor_listings, list) else competitor_listings.get('listings', [])

    # Calculate radar chart data (our score vs competitor average)
    comp_scores = gap_analysis.get('competitor_summary', [])

    # Estimate competitor scores based on their attributes
    comp_title_scores = []
    comp_bullet_scores = []
    comp_image_scores = []
    comp_aplus_scores = []

    for c in comp_scores:
        # Rough scoring based on component attributes
        title_len = c.get('title_length', 0)
        title_score_comp = min(100, max(50, (title_len / 200) * 100))
        comp_title_scores.append(title_score_comp)

        bullet_count = c.get('bullet_count', 0)
        bullet_score_comp = min(100, (bullet_count / 5) * 100)
        comp_bullet_scores.append(bullet_score_comp)

        image_count = c.get('image_count', 0)
        image_score_comp = min(100, (image_count / 7) * 100 * 1.5)
        comp_image_scores.append(image_score_comp)

        aplus_comp = 70 if c.get('has_aplus', False) else 0
        comp_aplus_scores.append(aplus_comp)

    # Calculate averages
    avg_comp_title = sum(comp_title_scores) / len(comp_title_scores) if comp_title_scores else 0
    avg_comp_bullets = sum(comp_bullet_scores) / len(comp_bullet_scores) if comp_bullet_scores else 0
    avg_comp_images = sum(comp_image_scores) / len(comp_image_scores) if comp_image_scores else 0
    avg_comp_aplus = sum(comp_aplus_scores) / len(comp_aplus_scores) if comp_aplus_scores else 0
    avg_comp_backend = 50  # Placeholder

    # Keyword coverage table rows
    keyword_rows = ''
    for kw in keywords_list[:15]:  # Top 15 keywords
        keyword_text = escape(kw.get('keyword', ''))
        search_volume = kw.get('search_volume', 0)
        priority_score = kw.get('priority_score', 0)
        tier = kw.get('tier', 'skip')

        # Determine tier color
        tier_color = 'rank-gold' if tier == 'title_priority' else 'rank-silver' if tier == 'bullet_priority' else ''
        tier_badge = 'Title' if tier == 'title_priority' else 'Bullet' if tier == 'bullet_priority' else 'Backend' if tier == 'backend_priority' else 'Skip'

        keyword_rows += f"""
        <tr class="{tier_color}">
            <td class="kw-cell">{keyword_text}</td>
            <td>{search_volume:,}</td>
            <td><span class="score-badge">{priority_score}</span></td>
            <td><span class="tier-badge tier-{tier.replace('_', '-')}">{tier_badge}</span></td>
        </tr>"""

    # Competitor listing table rows
    comp_table_rows = ''
    for i, c in enumerate(competitors[:10]):  # Top 10 competitors
        brand = escape(c.get('brand', '?'))
        title_len = len(c.get('title', ''))
        bullet_count = len(c.get('bullets', []))
        image_count = c.get('imageCount', c.get('image_count', 0))
        has_aplus = 'Yes' if c.get('hasAPlus', c.get('has_a_plus', False)) else 'No'
        price = float(c.get('price', 0) or 0)

        comp_table_rows += f"""
        <tr>
            <td class="rank-num">#{i+1}</td>
            <td class="brand-cell">{brand}</td>
            <td>{title_len}</td>
            <td>{bullet_count}</td>
            <td>{image_count}</td>
            <td>{has_aplus}</td>
            <td>${price:.2f}</td>
        </tr>"""

    # Action items rows with priority coloring
    action_rows = ''
    for rec in recommendations:
        priority = rec.get('priority', 'Medium')
        priority_class = 'priority-high' if priority == 'High' else 'priority-medium' if priority == 'Medium' else 'priority-low'
        area = escape(rec.get('area', ''))
        action = escape(rec.get('action', ''))
        impact = escape(rec.get('expected_impact', ''))

        action_rows += f"""
        <tr class="{priority_class}">
            <td class="priority-badge">{priority}</td>
            <td>{area}</td>
            <td>{action}</td>
            <td>{impact}</td>
        </tr>"""

    date = datetime.now().strftime('%Y-%m-%d')

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Listing Optimization Report — {date}</title>
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
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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
.kpi-label {{ font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
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
.chart-container {{ position: relative; width: 100%; height: 300px; }}

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

/* Badges */
.score-badge {{
    background: linear-gradient(135deg, var(--accent), var(--accent-2));
    color: white;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    font-weight: 600;
}}

.tier-badge {{
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
}}

.tier-badge.tier-title-priority {{
    background: rgba(245, 158, 11, 0.2);
    color: var(--amber);
}}

.tier-badge.tier-bullet-priority {{
    background: rgba(59, 130, 246, 0.2);
    color: var(--accent);
}}

.tier-badge.tier-backend-priority {{
    background: rgba(139, 92, 246, 0.2);
    color: var(--accent-2);
}}

.tier-badge.tier-skip {{
    background: rgba(107, 114, 128, 0.2);
    color: #9ca3af;
}}

.priority-badge {{
    font-weight: 600;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    text-transform: uppercase;
}}

.priority-high {{
    background: rgba(239, 68, 68, 0.15) !important;
}}

.priority-high .priority-badge {{
    background: rgba(239, 68, 68, 0.3);
    color: var(--red);
}}

.priority-medium {{
    background: rgba(245, 158, 11, 0.08) !important;
}}

.priority-medium .priority-badge {{
    background: rgba(245, 158, 11, 0.3);
    color: var(--amber);
}}

.priority-low {{
    background: rgba(16, 185, 129, 0.08) !important;
}}

.priority-low .priority-badge {{
    background: rgba(16, 185, 129, 0.3);
    color: var(--green);
}}

/* Footer */
.footer {{
    text-align: center;
    padding: 2rem;
    color: var(--text-dim);
    font-size: 0.8rem;
}}

.gap-bar {{
    background: var(--surface-2);
    border-radius: 6px;
    height: 20px;
    position: relative;
    overflow: hidden;
}}

.gap-bar-fill {{
    background: linear-gradient(90deg, var(--accent), var(--accent-2));
    height: 100%;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.7rem;
    font-weight: 600;
    color: white;
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
    <h1>Listing Optimization Report</h1>
    <p class="subtitle">ASIN: {escape(our_asin)} — {our_brand}</p>
    <p class="date">{date}</p>
</div>

<!-- KPI Cards -->
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Overall Score</div>
        <div class="kpi-value blue">{overall_score:.0f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Title Score</div>
        <div class="kpi-value amber">{title_score:.0f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Bullet Score</div>
        <div class="kpi-value cyan">{bullets_score:.0f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Image Score</div>
        <div class="kpi-value green">{images_score:.0f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">A+ Score</div>
        <div class="kpi-value purple">{aplus_score:.0f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Backend Keywords</div>
        <div class="kpi-value blue">{backend_bytes}/250</div>
    </div>
</div>

<!-- Charts -->
<div class="chart-grid">
    <div class="chart-card">
        <h3>Our Score vs Competitor Average</h3>
        <div class="chart-container"><canvas id="radarChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Gap Analysis by Dimension</h3>
        <div class="chart-container"><canvas id="gapChart"></canvas></div>
    </div>
</div>

<!-- Keyword Coverage Table -->
<div class="section">
    <div class="section-title"><span class="icon">🎯</span> Keyword Coverage (Top 15)</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Keyword</th><th>Search Volume</th><th>Priority Score</th><th>Tier</th>
        </tr></thead>
        <tbody>{keyword_rows}</tbody>
    </table>
    </div>
</div>

<!-- Competitor Comparison -->
<div class="section">
    <div class="section-title"><span class="icon">🏆</span> Top 10 Competitors — Listing Comparison</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Rank</th><th>Brand</th><th>Title Length</th><th>Bullet Count</th><th>Image Count</th><th>Has A+</th><th>Price</th>
        </tr></thead>
        <tbody>{comp_table_rows}</tbody>
    </table>
    </div>
</div>

<!-- Action Items -->
<div class="section">
    <div class="section-title"><span class="icon">⚡</span> Prioritized Action Items ({len(recommendations)} items)</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Priority</th><th>Area</th><th>Action</th><th>Expected Impact</th>
        </tr></thead>
        <tbody>{action_rows}</tbody>
    </table>
    </div>
</div>

<div class="footer">
    Generated by Zoviro Listing Optimization Skill &bull; {date}
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

// Radar chart: Our vs Competitor Average
new Chart(document.getElementById('radarChart'), {{
    type: 'radar',
    data: {{
        labels: ['Title', 'Bullets', 'Images', 'A+', 'Backend'],
        datasets: [
            {{
                label: 'Our Listing',
                data: [{title_score}, {bullets_score}, {images_score}, {aplus_score}, 75],
                borderColor: chartColors.amber,
                backgroundColor: 'rgba(245, 158, 11, 0.15)',
                tension: 0.4,
                fill: true,
            }},
            {{
                label: 'Competitor Avg',
                data: [{avg_comp_title:.0f}, {avg_comp_bullets:.0f}, {avg_comp_images:.0f}, {avg_comp_aplus:.0f}, 50],
                borderColor: chartColors.cyan,
                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                tension: 0.4,
                fill: true,
            }}
        ]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
            legend: {{ position: 'bottom', labels: {{ padding: 15 }} }}
        }},
        scales: {{
            r: {{
                beginAtZero: true,
                max: 100,
                ticks: {{ stepSize: 20 }},
                grid: {{ color: 'rgba(42,53,80,0.3)' }}
            }}
        }}
    }}
}});

// Gap analysis bar chart
new Chart(document.getElementById('gapChart'), {{
    type: 'barh',
    data: {{
        labels: ['Title', 'Bullets', 'Images', 'A+', 'Backend'],
        datasets: [
            {{
                label: 'Our Score',
                data: [{title_score}, {bullets_score}, {images_score}, {aplus_score}, 75],
                backgroundColor: chartColors.amber,
                borderRadius: 4,
            }},
            {{
                label: 'Top 10 Avg',
                data: [{avg_comp_title:.0f}, {avg_comp_bullets:.0f}, {avg_comp_images:.0f}, {avg_comp_aplus:.0f}, 50],
                backgroundColor: chartColors.cyan,
                borderRadius: 4,
            }}
        ]
    }},
    options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: true,
        plugins: {{
            legend: {{ position: 'bottom', labels: {{ padding: 15 }} }}
        }},
        scales: {{
            x: {{
                beginAtZero: true,
                max: 100,
                grid: {{ color: 'rgba(42,53,80,0.3)' }}
            }},
            y: {{
                grid: {{ display: false }}
            }}
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


def generate_md_report(gap_analysis, keyword_analysis, our_listing, competitor_listings, output_path):
    """Generate Markdown summary report."""

    overall_score = gap_analysis.get('overall_score', 0)
    scores = gap_analysis.get('scores', {})
    title_score = scores.get('title', {}).get('score', 0)
    bullets_score = scores.get('bullets', {}).get('score', 0)
    images_score = scores.get('images', {}).get('score', 0)
    aplus_score = scores.get('aplus', {}).get('score', 0)

    recommendations = gap_analysis.get('recommendations', [])
    backend_keywords = gap_analysis.get('backend_keywords', {})
    backend_bytes = backend_keywords.get('total_bytes_used', 0)
    selected_backend = backend_keywords.get('selected_for_backend', [])

    # Our listing
    our_asin = gap_analysis.get('our_asin', our_listing.get('asin', 'N/A'))
    our_brand = our_listing.get('brand', 'N/A')
    our_title = our_listing.get('title', 'N/A')

    date = datetime.now().strftime('%Y-%m-%d')

    md = f"""# Listing Optimization Report

**Date:** {date}
**ASIN:** {our_asin}
**Brand:** {our_brand}

## Overall Assessment

| Metric | Score |
|--------|-------|
| **Overall Score** | **{overall_score:.0f}/100** |
| Title Optimization | {title_score:.0f}/100 |
| Bullet Points | {bullets_score:.0f}/100 |
| Images | {images_score:.0f}/100 |
| A+ Content | {aplus_score:.0f}/100 |

## Current Listing

**Title:** {our_title}

## Key Gaps vs Competitors

"""

    # Add gap analysis
    md += "| Dimension | Our Score | Avg Competitor | Gap |\n"
    md += "|-----------|-----------|----------------|-----|\n"

    comp_scores = gap_analysis.get('competitor_summary', [])
    comp_title_scores = []
    comp_bullet_scores = []
    comp_image_scores = []
    comp_aplus_scores = []

    for c in comp_scores:
        title_len = c.get('title_length', 0)
        title_score_comp = min(100, max(50, (title_len / 200) * 100))
        comp_title_scores.append(title_score_comp)

        bullet_count = c.get('bullet_count', 0)
        bullet_score_comp = min(100, (bullet_count / 5) * 100)
        comp_bullet_scores.append(bullet_score_comp)

        image_count = c.get('image_count', 0)
        image_score_comp = min(100, (image_count / 7) * 100 * 1.5)
        comp_image_scores.append(image_score_comp)

        aplus_comp = 70 if c.get('has_aplus', False) else 0
        comp_aplus_scores.append(aplus_comp)

    avg_comp_title = sum(comp_title_scores) / len(comp_title_scores) if comp_title_scores else 0
    avg_comp_bullets = sum(comp_bullet_scores) / len(comp_bullet_scores) if comp_bullet_scores else 0
    avg_comp_images = sum(comp_image_scores) / len(comp_image_scores) if comp_image_scores else 0
    avg_comp_aplus = sum(comp_aplus_scores) / len(comp_aplus_scores) if comp_aplus_scores else 0

    md += f"| Title | {title_score:.0f} | {avg_comp_title:.0f} | {title_score - avg_comp_title:.0f} |\n"
    md += f"| Bullets | {bullets_score:.0f} | {avg_comp_bullets:.0f} | {bullets_score - avg_comp_bullets:.0f} |\n"
    md += f"| Images | {images_score:.0f} | {avg_comp_images:.0f} | {images_score - avg_comp_images:.0f} |\n"
    md += f"| A+ Content | {aplus_score:.0f} | {avg_comp_aplus:.0f} | {aplus_score - avg_comp_aplus:.0f} |\n"
    md += "\n"

    # Action items
    if recommendations:
        md += f"## Action Items ({len(recommendations)} recommended)\n\n"
        md += "| Priority | Area | Action | Impact |\n"
        md += "|----------|------|--------|--------|\n"

        for rec in recommendations:
            priority = rec.get('priority', 'Medium')
            area = rec.get('area', '')
            action = rec.get('action', '')
            impact = rec.get('expected_impact', '')
            md += f"| {priority} | {area} | {action} | {impact} |\n"
        md += "\n"

    # Backend keywords
    if selected_backend:
        md += "## Backend Keywords Selected\n\n"
        md += f"**Bytes Used:** {backend_bytes}/250\n\n"
        md += "| Keyword | Search Volume | Priority Score |\n"
        md += "|---------|---------------|-----------------|\n"
        for kw in selected_backend[:20]:  # Show top 20
            keyword = kw.get('keyword', '')
            sv = kw.get('search_volume', 0)
            priority = kw.get('priority_score', 0)
            md += f"| {keyword} | {sv:,} | {priority} |\n"
        md += "\n"

    md += f"---\n*Generated by Zoviro Listing Optimization Skill — {date}*\n"

    with open(output_path, 'w') as f:
        f.write(md)

    print(f"MD report saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate visual listing optimization report')
    parser.add_argument('--gap-analysis', required=True, help='Path to gap analysis JSON')
    parser.add_argument('--keyword-analysis', required=True, help='Path to keyword analysis JSON')
    parser.add_argument('--our-listing', required=True, help='Path to our listing JSON')
    parser.add_argument('--competitor-listings', required=True, help='Path to competitor listings JSON')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    args = parser.parse_args()

    # Load JSON files
    with open(args.gap_analysis) as f:
        gap_analysis = json.load(f)
    with open(args.keyword_analysis) as f:
        keyword_analysis = json.load(f)
    with open(args.our_listing) as f:
        our_listing = json.load(f)
    with open(args.competitor_listings) as f:
        competitor_listings = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')

    html_path = os.path.join(args.output_dir, f'Listing_Optimization_Report_{date}.html')
    md_path = os.path.join(args.output_dir, f'Listing_Optimization_Report_{date}.md')

    generate_html_report(gap_analysis, keyword_analysis, our_listing, competitor_listings, html_path)
    generate_md_report(gap_analysis, keyword_analysis, our_listing, competitor_listings, md_path)

    print(f"\n✓ Reports generated successfully!")
    print(f"  HTML: {html_path}")
    print(f"  MD:   {md_path}")
