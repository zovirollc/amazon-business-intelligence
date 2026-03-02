#!/usr/bin/env python3
"""
Step 4: Generate Visual Review Intelligence Report
Produces HTML interactive dashboard + MD summary.
"""

import os
import json
from datetime import datetime


def generate_html_report(analysis, comparison, output_path):
    """Generate interactive HTML dashboard."""

    our_asin = comparison.get('our_asin', 'N/A')
    our_stats = comparison.get('our_stats', {}) or {}
    theme_analysis = analysis.get('theme_analysis', {})
    theme_comparison = comparison.get('theme_comparison', {})
    pain_points = analysis.get('pain_points', [])
    feature_demands = analysis.get('feature_demands', [])
    strengths = comparison.get('strengths', [])
    weaknesses = comparison.get('weaknesses', [])
    opportunities = comparison.get('opportunities', [])
    rating_comparison = comparison.get('rating_comparison', [])

    # Build chart data
    rating_dist = analysis.get('rating_distribution', {})
    rating_labels = json.dumps([f'{i}★' for i in range(1, 6)])
    rating_values = json.dumps([rating_dist.get(str(i), rating_dist.get(i, 0)) for i in range(1, 6)])

    # Theme chart data
    theme_labels = json.dumps([t['label'][:20] for t in theme_analysis.values()])
    theme_mentions = json.dumps([t['mention_count'] for t in theme_analysis.values()])
    theme_sentiments = json.dumps([t['avg_sentiment'] for t in theme_analysis.values()])

    # Sentiment distribution
    sent_dist = analysis.get('sentiment_distribution', {})
    sent_labels = json.dumps(['Very Positive', 'Positive', 'Neutral', 'Negative', 'Very Negative'])
    sent_values = json.dumps([sent_dist.get('very_positive', 0), sent_dist.get('positive', 0),
                              sent_dist.get('neutral', 0), sent_dist.get('negative', 0),
                              sent_dist.get('very_negative', 0)])

    # Theme comparison (our vs competitors)
    comp_theme_labels = json.dumps([v['label'][:18] for v in theme_comparison.values()])
    comp_our_sent = json.dumps([v['our_sentiment'] for v in theme_comparison.values()])
    comp_comp_sent = json.dumps([v['avg_competitor_sentiment'] for v in theme_comparison.values()])

    # Competitor rating table rows
    rating_rows = ''
    for r in rating_comparison:
        highlight = ' style="background:#1e3a5f;font-weight:600;"' if r['is_ours'] else ''
        badge = ' <span style="color:#3b82f6;font-size:0.7em;">★ OURS</span>' if r['is_ours'] else ''
        name = (r['product_name'][:40] + '...') if len(r.get('product_name', '')) > 40 else r.get('product_name', '')
        rating_rows += f'''<tr{highlight}>
            <td>{r['asin']}{badge}</td>
            <td>{name}</td>
            <td>{r['review_count']}</td>
            <td>{'⭐' * int(r['avg_rating'])} {r['avg_rating']}</td>
            <td style="color:{'#10b981' if r['avg_sentiment'] > 0 else '#ef4444'}">{r['avg_sentiment']:.3f}</td>
        </tr>'''

    # Pain points list
    pain_html = ''
    for pp in pain_points[:15]:
        pain_html += f'<li><span class="highlight">{pp["phrase"]}</span> — {pp["mentions"]} mentions</li>'

    # Feature demands list
    demand_html = ''
    for fd in feature_demands[:10]:
        demand_html += f'<li><span class="rating-badge">{fd.get("rating", "?")}★</span> "{fd["context"][:100]}"</li>'

    # Strengths / Weaknesses / Opportunities
    def insight_cards(items, icon, color):
        html = ''
        for item in items[:5]:
            html += f'''<div class="insight-card" style="border-left:3px solid {color};">
                <span class="insight-icon">{icon}</span>
                <div>
                    <strong>{item['theme']}</strong>
                    <p>{item['insight']}</p>
                </div>
            </div>'''
        return html

    strengths_html = insight_cards(strengths, '✅', '#10b981')
    weaknesses_html = insight_cards(weaknesses, '⚠️', '#ef4444')
    opportunities_html = insight_cards(opportunities, '💡', '#f59e0b')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Review Intelligence Report — {our_asin}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ background:#0a0f1a; color:#e2e8f0; font-family:'DM Sans',sans-serif; padding:24px; }}
    .container {{ max-width:1400px; margin:0 auto; }}
    h1 {{ font-size:1.8rem; font-weight:700; margin-bottom:8px; }}
    h2 {{ font-size:1.2rem; font-weight:600; margin:24px 0 12px; color:#93c5fd; }}
    h3 {{ font-size:1rem; font-weight:500; margin:16px 0 8px; color:#cbd5e1; }}
    .subtitle {{ color:#94a3b8; font-size:0.9rem; margin-bottom:24px; }}
    .grid {{ display:grid; gap:16px; margin-bottom:24px; }}
    .grid-2 {{ grid-template-columns:1fr 1fr; }}
    .grid-3 {{ grid-template-columns:1fr 1fr 1fr; }}
    .grid-4 {{ grid-template-columns:1fr 1fr 1fr 1fr; }}
    .card {{ background:#111827; border-radius:12px; padding:20px; border:1px solid #1e293b; }}
    .kpi {{ text-align:center; }}
    .kpi .value {{ font-size:2rem; font-weight:700; color:#f8fafc; font-family:'JetBrains Mono',monospace; }}
    .kpi .label {{ color:#94a3b8; font-size:0.8rem; margin-top:4px; }}
    .chart-container {{ position:relative; height:300px; }}
    table {{ width:100%; border-collapse:collapse; font-size:0.85rem; }}
    th {{ background:#1e293b; padding:10px 12px; text-align:left; font-weight:600; }}
    td {{ padding:8px 12px; border-bottom:1px solid #1e293b; }}
    tr:hover {{ background:#1a2332; }}
    .highlight {{ background:#1e3a5f; padding:2px 8px; border-radius:4px; font-family:'JetBrains Mono',monospace; font-size:0.85rem; }}
    .rating-badge {{ background:#1e293b; padding:2px 6px; border-radius:4px; font-size:0.8rem; font-family:'JetBrains Mono',monospace; }}
    .insight-card {{ display:flex; gap:12px; padding:12px; margin:8px 0; background:#111827; border-radius:8px; align-items:flex-start; }}
    .insight-icon {{ font-size:1.2rem; flex-shrink:0; }}
    .insight-card p {{ color:#94a3b8; font-size:0.85rem; margin-top:4px; }}
    ul {{ list-style:none; padding:0; }}
    li {{ padding:6px 0; border-bottom:1px solid #1e293b; font-size:0.85rem; }}
    @media(max-width:768px) {{ .grid-2,.grid-3,.grid-4 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="container">
    <h1>📊 Review Intelligence Report</h1>
    <p class="subtitle">ASIN: {our_asin} | {analysis.get('total_reviews', 0)} reviews analyzed | Generated {datetime.now().strftime('%Y-%m-%d')}</p>

    <!-- KPI Cards -->
    <div class="grid grid-4">
        <div class="card kpi"><div class="value">{analysis.get('total_reviews', 0)}</div><div class="label">Total Reviews</div></div>
        <div class="card kpi"><div class="value">{analysis.get('avg_rating', 0)}</div><div class="label">Avg Rating</div></div>
        <div class="card kpi"><div class="value">{analysis.get('avg_sentiment', 0):+.3f}</div><div class="label">Avg Sentiment</div></div>
        <div class="card kpi"><div class="value">#{comparison.get('our_rank', '?')}/{comparison.get('total_products', '?')}</div><div class="label">Rating Rank</div></div>
    </div>

    <!-- Charts Row 1 -->
    <div class="grid grid-2">
        <div class="card">
            <h3>Rating Distribution</h3>
            <div class="chart-container"><canvas id="ratingChart"></canvas></div>
        </div>
        <div class="card">
            <h3>Sentiment Distribution</h3>
            <div class="chart-container"><canvas id="sentimentChart"></canvas></div>
        </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="grid grid-2">
        <div class="card">
            <h3>Theme Mentions & Sentiment</h3>
            <div class="chart-container"><canvas id="themeChart"></canvas></div>
        </div>
        <div class="card">
            <h3>Our Sentiment vs Competitors by Theme</h3>
            <div class="chart-container"><canvas id="compChart"></canvas></div>
        </div>
    </div>

    <!-- Insights -->
    <div class="grid grid-3">
        <div class="card">
            <h2>✅ Strengths</h2>
            {strengths_html if strengths_html else '<p style="color:#94a3b8;">No clear strengths detected (need our review data)</p>'}
        </div>
        <div class="card">
            <h2>⚠️ Weaknesses</h2>
            {weaknesses_html if weaknesses_html else '<p style="color:#94a3b8;">No significant weaknesses detected</p>'}
        </div>
        <div class="card">
            <h2>💡 Opportunities</h2>
            {opportunities_html if opportunities_html else '<p style="color:#94a3b8;">No opportunities detected yet</p>'}
        </div>
    </div>

    <!-- Pain Points & Feature Demands -->
    <div class="grid grid-2">
        <div class="card">
            <h2>🔴 Top Pain Points (from 1-2★ reviews)</h2>
            <ul>{pain_html if pain_html else '<li style="color:#94a3b8;">No pain points extracted</li>'}</ul>
        </div>
        <div class="card">
            <h2>🔵 Feature Demands</h2>
            <ul>{demand_html if demand_html else '<li style="color:#94a3b8;">No feature demands detected</li>'}</ul>
        </div>
    </div>

    <!-- Competitor Rating Table -->
    <div class="card">
        <h2>📋 Product Rating Comparison</h2>
        <table>
            <thead><tr><th>ASIN</th><th>Product</th><th>Reviews</th><th>Rating</th><th>Sentiment</th></tr></thead>
            <tbody>{rating_rows}</tbody>
        </table>
    </div>
</div>

<script>
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#1e293b';
const font = {{ family: "'DM Sans', sans-serif", size: 11 }};

// Rating Distribution
new Chart(document.getElementById('ratingChart'), {{
    type: 'bar',
    data: {{
        labels: {rating_labels},
        datasets: [{{ label: 'Reviews', data: {rating_values},
            backgroundColor: ['#ef4444','#f97316','#eab308','#22c55e','#10b981'],
            borderRadius: 6 }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ display:false }}, font }},
        scales:{{ y:{{ beginAtZero:true, grid:{{ color:'#1e293b' }} }}, x:{{ grid:{{ display:false }} }} }} }}
}});

// Sentiment Distribution
new Chart(document.getElementById('sentimentChart'), {{
    type: 'doughnut',
    data: {{
        labels: {sent_labels},
        datasets: [{{ data: {sent_values},
            backgroundColor: ['#10b981','#22c55e','#94a3b8','#f97316','#ef4444'],
            borderWidth: 0 }}]
    }},
    options: {{ responsive:true, maintainAspectRatio:false, plugins:{{ legend:{{ position:'right', labels:{{ font }} }} }} }}
}});

// Theme Analysis
new Chart(document.getElementById('themeChart'), {{
    type: 'bar',
    data: {{
        labels: {theme_labels},
        datasets: [
            {{ label: 'Mentions', data: {theme_mentions}, backgroundColor: '#3b82f6', borderRadius: 4, yAxisID: 'y' }},
            {{ label: 'Sentiment', data: {theme_sentiments}, type: 'line', borderColor: '#f59e0b',
               backgroundColor: 'transparent', pointRadius: 4, yAxisID: 'y1' }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false,
        scales: {{ y:{{ beginAtZero:true, position:'left', grid:{{ color:'#1e293b' }} }},
                   y1:{{ position:'right', min:-1, max:1, grid:{{ display:false }} }},
                   x:{{ grid:{{ display:false }} }} }},
        plugins:{{ legend:{{ labels:{{ font }} }} }}
    }}
}});

// Comparison Chart
new Chart(document.getElementById('compChart'), {{
    type: 'radar',
    data: {{
        labels: {comp_theme_labels},
        datasets: [
            {{ label: 'Our Product', data: {comp_our_sent}, borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.15)', pointRadius: 4 }},
            {{ label: 'Competitors Avg', data: {comp_comp_sent}, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.1)', pointRadius: 4 }}
        ]
    }},
    options: {{ responsive:true, maintainAspectRatio:false,
        scales: {{ r: {{ min:-1, max:1, ticks:{{ stepSize:0.5 }}, grid:{{ color:'#1e293b' }}, pointLabels:{{ font }} }} }},
        plugins:{{ legend:{{ labels:{{ font }} }} }}
    }}
}});
</script>
</body>
</html>'''

    with open(output_path, 'w') as f:
        f.write(html)
    print(f"  HTML report: {output_path}")


def generate_md_report(analysis, comparison, output_path):
    """Generate markdown summary report."""
    our_asin = comparison.get('our_asin', 'N/A')
    our_stats = comparison.get('our_stats', {}) or {}

    lines = [
        f"# Review Intelligence Report",
        f"",
        f"**ASIN:** {our_asin} | **Reviews Analyzed:** {analysis.get('total_reviews', 0)} | "
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d')}",
        f"",
        f"## Key Metrics",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Reviews | {analysis.get('total_reviews', 0)} |",
        f"| Average Rating | {analysis.get('avg_rating', 0)}★ |",
        f"| Average Sentiment | {analysis.get('avg_sentiment', 0):+.3f} |",
        f"| Our Rating Rank | #{comparison.get('our_rank', '?')}/{comparison.get('total_products', '?')} |",
        f"| Verified Purchases | {analysis.get('verified_count', 0)} |",
        f"",
    ]

    # Theme Analysis
    lines.append("## Theme Analysis")
    lines.append("")
    lines.append("| Theme | Mentions | % | Sentiment |")
    lines.append("|-------|----------|---|-----------|")
    for t_id, t in analysis.get('theme_analysis', {}).items():
        emoji = '🟢' if t['avg_sentiment'] > 0.1 else ('🔴' if t['avg_sentiment'] < -0.1 else '🟡')
        lines.append(f"| {t['label']} | {t['mention_count']} | {t['mention_pct']}% | {emoji} {t['avg_sentiment']:+.3f} |")
    lines.append("")

    # Strengths
    strengths = comparison.get('strengths', [])
    if strengths:
        lines.append("## Strengths")
        lines.append("")
        for s in strengths[:5]:
            lines.append(f"- **{s['theme']}** — {s['insight']} (gap: +{s['gap']:.2f})")
        lines.append("")

    # Weaknesses
    weaknesses = comparison.get('weaknesses', [])
    if weaknesses:
        lines.append("## Weaknesses")
        lines.append("")
        for w in weaknesses[:5]:
            lines.append(f"- **{w['theme']}** — {w['insight']} (gap: {w['gap']:.2f})")
        lines.append("")

    # Opportunities
    opportunities = comparison.get('opportunities', [])
    if opportunities:
        lines.append("## Opportunities")
        lines.append("")
        for o in opportunities[:5]:
            lines.append(f"- **{o['theme']}** — {o['insight']}")
        lines.append("")

    # Pain Points
    pain_points = analysis.get('pain_points', [])
    if pain_points:
        lines.append("## Top Pain Points (1-2★ Reviews)")
        lines.append("")
        for pp in pain_points[:15]:
            lines.append(f"- `{pp['phrase']}` — {pp['mentions']} mentions")
        lines.append("")

    # Feature Demands
    feature_demands = analysis.get('feature_demands', [])
    if feature_demands:
        lines.append("## Feature Demands")
        lines.append("")
        for fd in feature_demands[:10]:
            lines.append(f"- [{fd.get('rating', '?')}★] \"{fd['context'][:100]}\"")
        lines.append("")

    # Rating Comparison
    lines.append("## Product Rating Comparison")
    lines.append("")
    lines.append("| ASIN | Product | Reviews | Rating | Sentiment |")
    lines.append("|------|---------|---------|--------|-----------|")
    for r in comparison.get('rating_comparison', []):
        marker = ' **⭐OURS**' if r['is_ours'] else ''
        name = (r.get('product_name', '')[:35] + '...') if len(r.get('product_name', '')) > 35 else r.get('product_name', '')
        lines.append(f"| {r['asin']}{marker} | {name} | {r['review_count']} | {r['avg_rating']}★ | {r['avg_sentiment']:+.3f} |")
    lines.append("")

    # Actionable Recommendations
    lines.append("## Actionable Recommendations")
    lines.append("")
    lines.append("### For Listing Optimization")
    if pain_points:
        lines.append(f"- Address top pain points in bullet points: `{pain_points[0]['phrase']}`")
    if strengths:
        lines.append(f"- Highlight our strength: {strengths[0]['theme']}")
    if opportunities:
        lines.append(f"- Differentiate on: {opportunities[0]['theme']}")
    lines.append("")
    lines.append("### For PPC Strategy")
    lines.append("- Target keywords related to competitor pain points")
    lines.append("- Use positive theme language in ad copy")
    if weaknesses:
        lines.append(f"- Avoid emphasizing: {weaknesses[0]['theme']}")
    lines.append("")

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"  MD report: {output_path}")


def generate_reports(input_dir, output_dir):
    """Generate both HTML and MD reports."""
    analysis_path = os.path.join(input_dir, 'review_analysis.json')
    comparison_path = os.path.join(input_dir, 'review_comparison.json')

    with open(analysis_path) as f:
        analysis = json.load(f)
    with open(comparison_path) as f:
        comparison = json.load(f)

    date_str = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(output_dir, exist_ok=True)

    html_path = os.path.join(output_dir, f'Review_Intelligence_Report_{date_str}.html')
    md_path = os.path.join(output_dir, f'Review_Intelligence_Report_{date_str}.md')

    generate_html_report(analysis, comparison, html_path)
    generate_md_report(analysis, comparison, md_path)

    print(f"\n{'='*50}")
    print(f"Reports generated:")
    print(f"  {html_path}")
    print(f"  {md_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate Review Intelligence Report')
    parser.add_argument('--input', type=str, required=True, help='Directory with analysis + comparison JSON')
    parser.add_argument('--output-dir', type=str, required=True, help='Output directory for reports')
    args = parser.parse_args()

    generate_reports(args.input, args.output_dir)
