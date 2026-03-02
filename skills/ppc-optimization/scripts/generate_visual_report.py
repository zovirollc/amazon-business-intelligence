#!/usr/bin/env python3
"""
Visual Report Generator — PPC Optimization
Generates an interactive HTML dashboard + MD summary from PPC campaign data.
Uses Chart.js for charts, custom CSS for styling.
Follows the same design aesthetic as Competitor Research report.
"""

import json
import argparse
import os
from datetime import datetime
import html as html_module


def escape(text):
    """HTML-escape text."""
    return html_module.escape(str(text)) if text else ''


def classify_acos(acos, target=0.30):
    """Classify ACOS level relative to target."""
    ratio = acos / target if target > 0 else 0
    if ratio <= 0.7:
        return 'excellent'
    elif ratio <= 1.0:
        return 'good'
    elif ratio <= 1.3:
        return 'marginal'
    else:
        return 'poor'


def generate_html_report(search_terms_data, keyword_priorities_data, campaign_structure_data, output_path):
    """Generate interactive HTML dashboard."""

    search_terms = search_terms_data.get('search_terms', [])
    total_spend = search_terms_data.get('total_spend', 0)
    total_sales = search_terms_data.get('total_sales', 0)
    overall_acos = search_terms_data.get('overall_acos', 0)
    asin = search_terms_data.get('asin', 'UNKNOWN')
    date = search_terms_data.get('generated_date', datetime.now().strftime('%Y-%m-%d'))

    keywords = keyword_priorities_data.get('keywords', []) if keyword_priorities_data else []
    campaigns = campaign_structure_data.get('campaigns', []) if campaign_structure_data else []

    # Calculate KPIs
    total_orders = sum(term.get('orders', 0) for term in search_terms)
    total_clicks = sum(term.get('clicks', 0) for term in search_terms)
    total_impressions = sum(term.get('impressions', 0) for term in search_terms)
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    avg_cvr = (total_orders / total_clicks * 100) if total_clicks > 0 else 0
    unique_search_terms = len(search_terms)

    # Classification breakdown
    classifications = {}
    for term in search_terms:
        cls = term.get('classification', 'neutral')
        classifications[cls] = classifications.get(cls, 0) + 1

    classification_labels = list(classifications.keys())
    classification_values = list(classifications.values())

    # Keyword tier distribution
    tier_dist = {'tier_1_exact': 0, 'tier_2_phrase': 0, 'tier_3_broad': 0, 'negative_candidate': 0}
    for kw in keywords:
        tier = kw.get('tier', 'unknown')
        if tier in tier_dist:
            tier_dist[tier] += 1

    tier_labels = list(tier_dist.keys())
    tier_values = list(tier_dist.values())

    # Campaign budget allocation
    campaign_labels = [escape(c.get('campaign_name', '')[:30]) for c in campaigns]
    campaign_budgets = [c.get('daily_budget', 0) for c in campaigns]

    # Top 10 winners (lowest ACOS with orders > 0)
    winners = [t for t in search_terms if t.get('orders', 0) > 0 and t.get('classification') == 'winner']
    winners.sort(key=lambda x: x.get('acos', 999))
    top_winners = winners[:10]

    # Top 10 wasted spend (highest spend with 0 orders)
    wasted = [t for t in search_terms if t.get('orders', 0) == 0]
    wasted.sort(key=lambda x: x.get('spend', 0), reverse=True)
    top_wasted = wasted[:10]

    # Negative keywords recommendation
    negative_keywords = [t.get('search_term', '') for t in search_terms if t.get('classification') == 'wasted_spend'][:20]

    # Action items - prioritized by impact
    action_items = []
    for term in search_terms:
        action = term.get('action', '')
        if action:
            classification = term.get('classification', 'neutral')
            priority = 'High' if classification in ['bleeder', 'wasted_spend'] else 'Medium' if classification == 'marginal' else 'Low'
            action_items.append({
                'search_term': term.get('search_term', ''),
                'action': action,
                'priority': priority,
                'classification': classification,
                'acos': term.get('acos', 0)
            })

    # Sort by priority (High > Medium > Low) then by impact (ACOS)
    priority_order = {'High': 0, 'Medium': 1, 'Low': 2}
    action_items.sort(key=lambda x: (priority_order[x['priority']], x['acos']))
    action_items = action_items[:15]  # Top 15 action items

    # Render winner rows
    winner_rows = ''
    for i, term in enumerate(top_winners, 1):
        winner_rows += f"""
        <tr>
            <td class="rank-num">#{i}</td>
            <td class="kw-cell">{escape(term.get('search_term', ''))}</td>
            <td>${float(term.get('spend', 0)):.2f}</td>
            <td>${float(term.get('sales', 0)):.2f}</td>
            <td>{int(term.get('orders', 0))}</td>
            <td>{float(term.get('acos', 0)):.1%}</td>
            <td>${float(term.get('cpc', 0)):.2f}</td>
        </tr>"""

    # Render wasted spend rows
    wasted_rows = ''
    for i, term in enumerate(top_wasted, 1):
        wasted_rows += f"""
        <tr>
            <td class="rank-num">#{i}</td>
            <td class="kw-cell">{escape(term.get('search_term', ''))}</td>
            <td>${float(term.get('spend', 0)):.2f}</td>
            <td>{int(term.get('impressions', 0))}</td>
            <td>{int(term.get('clicks', 0))}</td>
            <td>${float(term.get('cpc', 0)):.2f}</td>
        </tr>"""

    # Render action items
    action_rows = ''
    for item in action_items:
        priority_color = 'high-priority' if item['priority'] == 'High' else 'medium-priority' if item['priority'] == 'Medium' else 'low-priority'
        action_rows += f"""
        <tr class="{priority_color}">
            <td><span class="priority-badge {priority_color.replace('-priority', '')}">{item['priority']}</span></td>
            <td class="kw-cell">{escape(item['search_term'])}</td>
            <td>{escape(item['action'])}</td>
            <td>{escape(item['classification'])}</td>
        </tr>"""

    # Render campaign structure
    campaign_rows = ''
    for i, campaign in enumerate(campaigns, 1):
        ad_groups = campaign.get('ad_groups', [])
        campaign_rows += f"""
        <tr>
            <td class="rank-num">#{i}</td>
            <td class="brand-cell">{escape(campaign.get('campaign_name', ''))}</td>
            <td>${float(campaign.get('daily_budget', 0)):.2f}</td>
            <td>{len(ad_groups)}</td>
            <td style="color: var(--text-dim); font-size: 0.85rem;">{', '.join(escape(ag) for ag in ad_groups[:3])}{'...' if len(ad_groups) > 3 else ''}</td>
        </tr>"""

    # Scatter chart data: search term spend vs sales
    scatter_data = []
    color_map = {
        'winner': '#10b981',
        'marginal': '#f59e0b',
        'bleeder': '#ef4444',
        'wasted_spend': '#8b5cf6',
        'under_review': '#06b6d4',
        'insufficient_data': '#8892a8',
        'neutral': '#3b82f6'
    }
    for term in search_terms[:50]:  # Limit to 50 for readability
        classification = term.get('classification', 'neutral')
        color = color_map.get(classification, '#3b82f6')
        scatter_data.append({
            'x': float(term.get('spend', 0)),
            'y': float(term.get('sales', 0)),
            'r': max(3, int(term.get('orders', 0)) + 3),
            'classification': escape(classification),
            'backgroundColor': color,
            'borderColor': color
        })

    # ACOS gauge indicator
    acos_status = classify_acos(overall_acos)
    acos_class = 'acos-excellent' if acos_status == 'excellent' else 'acos-good' if acos_status == 'good' else 'acos-marginal' if acos_status == 'marginal' else 'acos-poor'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PPC Optimization Report — {date}</title>
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
.kpi-value.red {{ color: var(--red); }}

/* ACOS Gauge */
.acos-gauge {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1.5rem;
    padding: 1.5rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 1.5rem;
}}
.acos-gauge-visual {{
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    border: 4px solid var(--border);
}}
.acos-excellent {{ background: rgba(16, 185, 129, 0.15); color: var(--green); border-color: var(--green); }}
.acos-good {{ background: rgba(6, 182, 212, 0.15); color: var(--cyan); border-color: var(--cyan); }}
.acos-marginal {{ background: rgba(245, 158, 11, 0.15); color: var(--amber); border-color: var(--amber); }}
.acos-poor {{ background: rgba(239, 68, 68, 0.15); color: var(--red); border-color: var(--red); }}

.acos-info {{
    flex: 1;
}}
.acos-info h3 {{
    font-size: 0.95rem;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}}
.acos-info p {{
    font-size: 0.9rem;
    color: var(--text);
    margin-bottom: 0.5rem;
}}
.acos-target {{
    font-size: 0.85rem;
    color: var(--text-dim);
    font-family: 'JetBrains Mono', monospace;
}}

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
.rank-num {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--accent); }}
.brand-cell {{ font-weight: 600; white-space: nowrap; }}
.kw-cell {{ font-weight: 500; color: var(--cyan); }}

/* Priority badges */
.priority-badge {{
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
}}
.priority-badge.high {{
    background: rgba(239, 68, 68, 0.2);
    color: var(--red);
}}
.priority-badge.medium {{
    background: rgba(245, 158, 11, 0.2);
    color: var(--amber);
}}
.priority-badge.low {{
    background: rgba(6, 182, 212, 0.2);
    color: var(--cyan);
}}

tr.high-priority {{ background: rgba(239, 68, 68, 0.05) !important; }}
tr.medium-priority {{ background: rgba(245, 158, 11, 0.03) !important; }}
tr.low-priority {{ background: rgba(6, 182, 212, 0.03) !important; }}

/* Negative keywords list */
.negative-keywords {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
}}
.negative-badge {{
    background: rgba(139, 92, 246, 0.2);
    color: var(--accent-2);
    padding: 0.4rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
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
    .acos-gauge {{ flex-direction: column; }}
    .chart-container {{ height: 250px; }}
}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
    <h1>PPC Optimization Report</h1>
    <p class="subtitle">ASIN {escape(asin)} — Campaign Performance Analysis</p>
    <p class="date">{date}</p>
</div>

<!-- KPI Cards -->
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-label">Total Spend</div>
        <div class="kpi-value blue">${total_spend:,.2f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Total Sales</div>
        <div class="kpi-value green">${total_sales:,.2f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Total Orders</div>
        <div class="kpi-value cyan">{total_orders:,}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg CPC</div>
        <div class="kpi-value amber">${avg_cpc:.2f}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Avg CVR</div>
        <div class="kpi-value purple">{avg_cvr:.2f}%</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Unique Search Terms</div>
        <div class="kpi-value">{{blue}}{unique_search_terms:,}</div>
    </div>
</div>

<!-- ACOS Indicator -->
<div class="acos-gauge">
    <div class="acos-gauge-visual {acos_class}">{overall_acos:.1%}</div>
    <div class="acos-info">
        <h3>Overall ACOS</h3>
        <p>Current: <strong>{overall_acos:.1%}</strong></p>
        <p class="acos-target">Target: 30% | Status: {acos_status.upper()}</p>
        <p style="margin-top: 0.5rem; font-size: 0.8rem;">
            {'✓ Excellent performance — well below target' if acos_status == 'excellent' else '✓ Good performance — within target' if acos_status == 'good' else '⚠ Marginal performance — above target' if acos_status == 'marginal' else '✗ Poor performance — significantly above target'}
        </p>
    </div>
</div>

<!-- Charts -->
<div class="chart-grid">
    <div class="chart-card">
        <h3>Search Term Classification Distribution</h3>
        <div class="chart-container"><canvas id="classificationChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Keyword Tier Distribution</h3>
        <div class="chart-container"><canvas id="tierChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Spend vs Sales (Bubble = Orders)</h3>
        <div class="chart-container"><canvas id="scatterChart"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>Campaign Budget Allocation</h3>
        <div class="chart-container"><canvas id="budgetChart"></canvas></div>
    </div>
</div>

<!-- Top Winners -->
<div class="section">
    <div class="section-title"><span class="icon">🏆</span> Top 10 Winners (Lowest ACOS with Orders)</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Rank</th><th>Search Term</th><th>Spend</th><th>Sales</th><th>Orders</th><th>ACOS</th><th>CPC</th>
        </tr></thead>
        <tbody>{winner_rows}</tbody>
    </table>
    </div>
</div>

<!-- Top Wasted Spend -->
<div class="section">
    <div class="section-title"><span class="icon">⚠️</span> Top 10 Wasted Spend (Highest Spend with 0 Orders)</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Rank</th><th>Search Term</th><th>Spend</th><th>Impressions</th><th>Clicks</th><th>CPC</th>
        </tr></thead>
        <tbody>{wasted_rows}</tbody>
    </table>
    </div>
</div>

<!-- Negative Keywords -->
<div class="section">
    <div class="section-title"><span class="icon">🚫</span> Recommended Negative Keywords</div>
    <p style="font-size: 0.9rem; color: var(--text-dim); margin-bottom: 1rem;">Add these terms to your negative keyword list to reduce wasted spend:</p>
    <div class="negative-keywords">
        {' '.join(f'<span class="negative-badge">{escape(kw)}</span>' for kw in negative_keywords)}
    </div>
</div>

<!-- Campaign Structure -->
<div class="section">
    <div class="section-title"><span class="icon">📋</span> Campaign Structure Overview</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Rank</th><th>Campaign Name</th><th>Daily Budget</th><th>Ad Groups</th><th>Sample Ad Groups</th>
        </tr></thead>
        <tbody>{campaign_rows}</tbody>
    </table>
    </div>
</div>

<!-- Action Items -->
<div class="section">
    <div class="section-title"><span class="icon">✅</span> Prioritized Action Items</div>
    <div style="overflow-x: auto;">
    <table>
        <thead><tr>
            <th>Priority</th><th>Search Term</th><th>Recommended Action</th><th>Classification</th>
        </tr></thead>
        <tbody>{action_rows}</tbody>
    </table>
    </div>
</div>

<div class="footer">
    Generated by Zoviro PPC Optimization Skill &bull; {date}
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
}};

Chart.defaults.color = '#8892a8';
Chart.defaults.borderColor = 'rgba(42, 53, 80, 0.5)';
Chart.defaults.font.family = "'DM Sans', sans-serif";

// Classification doughnut chart
new Chart(document.getElementById('classificationChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(classification_labels)},
        datasets: [{{
            data: {json.dumps(classification_values)},
            backgroundColor: [chartColors.green, chartColors.amber, chartColors.red, chartColors.purple, chartColors.cyan, '#8892a8', chartColors.blue],
            borderWidth: 2,
            borderColor: '#111827',
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ position: 'bottom', labels: {{ padding: 15 }} }}
        }}
    }}
}});

// Keyword tier distribution bar chart
new Chart(document.getElementById('tierChart'), {{
    type: 'bar',
    data: {{
        labels: {json.dumps(tier_labels)},
        datasets: [{{
            data: {json.dumps(tier_values)},
            backgroundColor: [chartColors.green, chartColors.cyan, chartColors.blue, chartColors.purple],
            borderRadius: 4,
            barPercentage: 0.7,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            y: {{ beginAtZero: true, grid: {{ color: 'rgba(42,53,80,0.3)' }} }},
            x: {{ grid: {{ display: false }} }}
        }}
    }}
}});

// Scatter chart: Spend vs Sales
new Chart(document.getElementById('scatterChart'), {{
    type: 'bubble',
    data: {{
        datasets: [{{
            label: 'Search Terms',
            data: {json.dumps(scatter_data)},
            backgroundColor: {json.dumps([d['backgroundColor'] for d in scatter_data])},
            borderColor: {json.dumps([d['borderColor'] for d in scatter_data])},
            borderWidth: 1.5,
            borderAlpha: 0.8,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ title: {{ display: true, text: 'Spend ($)' }}, grid: {{ color: 'rgba(42,53,80,0.3)' }} }},
            y: {{ title: {{ display: true, text: 'Sales ($)' }}, grid: {{ color: 'rgba(42,53,80,0.3)' }} }}
        }}
    }}
}});

// Campaign budget pie chart
new Chart(document.getElementById('budgetChart'), {{
    type: 'doughnut',
    data: {{
        labels: {json.dumps(campaign_labels)},
        datasets: [{{
            data: {json.dumps(campaign_budgets)},
            backgroundColor: [chartColors.blue, chartColors.green, chartColors.amber, chartColors.cyan, chartColors.purple, chartColors.red],
            borderWidth: 2,
            borderColor: '#111827',
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ position: 'bottom', labels: {{ padding: 15 }} }}
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


def generate_md_report(search_terms_data, keyword_priorities_data, campaign_structure_data, output_path):
    """Generate Markdown summary report."""

    search_terms = search_terms_data.get('search_terms', [])
    total_spend = search_terms_data.get('total_spend', 0)
    total_sales = search_terms_data.get('total_sales', 0)
    overall_acos = search_terms_data.get('overall_acos', 0)
    asin = search_terms_data.get('asin', 'UNKNOWN')
    date = search_terms_data.get('generated_date', datetime.now().strftime('%Y-%m-%d'))

    keywords = keyword_priorities_data.get('keywords', []) if keyword_priorities_data else []
    campaigns = campaign_structure_data.get('campaigns', []) if campaign_structure_data else []

    # Calculate KPIs
    total_orders = sum(term.get('orders', 0) for term in search_terms)
    total_clicks = sum(term.get('clicks', 0) for term in search_terms)
    total_impressions = sum(term.get('impressions', 0) for term in search_terms)
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0
    avg_cvr = (total_orders / total_clicks * 100) if total_clicks > 0 else 0

    # Classification breakdown
    classifications = {}
    for term in search_terms:
        cls = term.get('classification', 'neutral')
        classifications[cls] = classifications.get(cls, 0) + 1

    # Top winners
    winners = [t for t in search_terms if t.get('orders', 0) > 0 and t.get('classification') == 'winner']
    winners.sort(key=lambda x: x.get('acos', 999))
    top_winners = winners[:5]

    # Top bleeders
    bleeders = [t for t in search_terms if t.get('classification') == 'bleeder']
    bleeders.sort(key=lambda x: x.get('spend', 0), reverse=True)
    top_bleeders = bleeders[:5]

    md = f"""# PPC Optimization Report

**Date:** {date}
**ASIN:** {asin}
**Overall ACOS:** {overall_acos:.1%}

## Campaign KPIs

| Metric | Value |
|--------|-------|
| Total Spend | ${total_spend:,.2f} |
| Total Sales | ${total_sales:,.2f} |
| Total Orders | {total_orders:,} |
| Total Clicks | {total_clicks:,} |
| Total Impressions | {total_impressions:,} |
| Avg CPC | ${avg_cpc:.2f} |
| Avg CVR | {avg_cvr:.2f}% |
| Unique Search Terms | {len(search_terms)} |

## Classification Breakdown

| Classification | Count |
|---|---|
"""

    for cls in sorted(classifications.keys()):
        md += f"| {cls} | {classifications[cls]} |\n"

    md += f"\n## Top 5 Winners (Lowest ACOS)\n\n"
    md += "| Search Term | Spend | Sales | Orders | ACOS | CPC |\n"
    md += "|---|---|---|---|---|---|\n"
    for term in top_winners:
        md += f"| {term.get('search_term', '')} | ${float(term.get('spend', 0)):.2f} | ${float(term.get('sales', 0)):.2f} | {int(term.get('orders', 0))} | {float(term.get('acos', 0)):.1%} | ${float(term.get('cpc', 0)):.2f} |\n"

    if top_bleeders:
        md += f"\n## Top 5 Bleeders (Highest ACOS)\n\n"
        md += "| Search Term | Spend | Sales | Orders | ACOS |\n"
        md += "|---|---|---|---|---|\n"
        for term in top_bleeders:
            md += f"| {term.get('search_term', '')} | ${float(term.get('spend', 0)):.2f} | ${float(term.get('sales', 0)):.2f} | {int(term.get('orders', 0))} | {float(term.get('acos', 0)):.1%} |\n"

    # Campaign summary
    if campaigns:
        md += f"\n## Campaign Structure ({len(campaigns)} campaigns)\n\n"
        for i, campaign in enumerate(campaigns, 1):
            daily_budget = campaign.get('daily_budget', 0)
            ad_groups = campaign.get('ad_groups', [])
            md += f"**{i}. {campaign.get('campaign_name', '')}**\n"
            md += f"- Daily Budget: ${daily_budget:.2f}\n"
            md += f"- Ad Groups: {len(ad_groups)} ({', '.join(ad_groups[:3])}{'...' if len(ad_groups) > 3 else ''})\n\n"

    # Keywords summary
    if keywords:
        tier_counts = {}
        for kw in keywords:
            tier = kw.get('tier', 'unknown')
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        md += f"## Keyword Tier Distribution ({len(keywords)} keywords)\n\n"
        for tier in sorted(tier_counts.keys()):
            md += f"- {tier}: {tier_counts[tier]}\n"

    md += f"\n---\n*Generated by Zoviro PPC Optimization Skill — {date}*\n"

    with open(output_path, 'w') as f:
        f.write(md)

    print(f"MD report saved to: {output_path}")
    return output_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate visual PPC optimization report')
    parser.add_argument('--search-terms', required=True, help='Path to search terms JSON')
    parser.add_argument('--keyword-priorities', default=None, help='Path to keyword priorities JSON (optional)')
    parser.add_argument('--campaign-structure', default=None, help='Path to campaign structure JSON (optional)')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    args = parser.parse_args()

    with open(args.search_terms) as f:
        search_terms_data = json.load(f)

    keyword_priorities_data = None
    if args.keyword_priorities and os.path.exists(args.keyword_priorities):
        with open(args.keyword_priorities) as f:
            keyword_priorities_data = json.load(f)

    campaign_structure_data = None
    if args.campaign_structure and os.path.exists(args.campaign_structure):
        with open(args.campaign_structure) as f:
            campaign_structure_data = json.load(f)

    os.makedirs(args.output_dir, exist_ok=True)
    date = search_terms_data.get('generated_date', datetime.now().strftime('%Y-%m-%d'))
    asin = search_terms_data.get('asin', 'UNKNOWN')

    html_path = os.path.join(args.output_dir, f'PPC_Optimization_Report_{asin}_{date}.html')
    md_path = os.path.join(args.output_dir, f'PPC_Optimization_Report_{asin}_{date}.md')

    generate_html_report(search_terms_data, keyword_priorities_data, campaign_structure_data, html_path)
    generate_md_report(search_terms_data, keyword_priorities_data, campaign_structure_data, md_path)
