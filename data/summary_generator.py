#!/usr/bin/env python3
"""
Summary Generator
Creates token-optimized text summaries from processed data for LLM consumption.
Each summary targets ≤2000 tokens (~8000 characters).
"""

import json
from datetime import datetime
from pathlib import Path


MAX_CHARS = 8000  # ~2000 tokens


def generate_ppc_summary(ppc_data: dict, product_name: str = "", asin: str = "") -> str:
    """Generate PPC performance summary."""
    lines = [
        f"PPC PERFORMANCE SUMMARY — {product_name} ({asin})",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Period: {ppc_data.get('period', 'N/A')}",
        "=" * 50,
        "",
        "KEY METRICS",
        f"  Spend: ${ppc_data.get('total_spend', 0):,.2f}",
        f"  Sales: ${ppc_data.get('total_sales', 0):,.2f}",
        f"  ACOS: {ppc_data.get('overall_acos', 0):.1f}% (target: {ppc_data.get('target_acos', 30)}%)",
        f"  ROAS: {ppc_data.get('roas', 0):.2f}x",
        f"  Unique Search Terms: {ppc_data.get('total_unique_terms', 0)}",
        "",
        "SEARCH TERM CLASSIFICATION",
    ]
    
    classification = ppc_data.get('classification', {})
    for cls_name, count in classification.items():
        lines.append(f"  {cls_name}: {count}")
    
    lines.append("")
    lines.append("TOP WINNERS (by sales)")
    for kw in ppc_data.get('top_winners', [])[:10]:
        name = kw.get('keyword', '') or kw.get('search_term', '')
        lines.append(f"  • {name} — Sales ${kw.get('sales', 0):.2f} | ACOS {kw.get('acos', 0):.1f}%")

    lines.append("")
    lines.append("TOP NEGATIVE CANDIDATES (wasted spend)")
    for kw in ppc_data.get('negative_candidates', [])[:10]:
        name = kw.get('keyword', '') or kw.get('search_term', '')
        lines.append(f"  • {name} — Spend ${kw.get('spend', 0):.2f} | 0 sales")
    
    lines.append("")
    lines.append("RECOMMENDED ACTIONS")
    for action in ppc_data.get('actions', [])[:5]:
        lines.append(f"  → {action}")
    
    text = '\n'.join(lines)
    return text[:MAX_CHARS]


def generate_competitor_summary(competitor_data: dict, asin: str = "") -> str:
    """Generate competitor landscape summary."""
    lines = [
        f"COMPETITOR LANDSCAPE — {asin}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 50,
        "",
        "MARKET OVERVIEW",
        f"  Total competitors found: {competitor_data.get('total_raw', 0)}",
        f"  After dedup + filter: {competitor_data.get('total_filtered', 0)}",
        f"  Keywords searched: {', '.join(competitor_data.get('keywords_used', []))}",
        "",
        "TOP 10 COMPETITORS",
    ]
    
    for i, comp in enumerate(competitor_data.get('top_competitors', [])[:10], 1):
        lines.append(f"  {i}. {comp.get('brand', 'N/A')} — {comp.get('title', '')[:45]}")
        lines.append(f"     BSR #{comp.get('bsr', 'N/A')} | {comp.get('reviews', 0)} reviews | "
                     f"${comp.get('price', 0):.2f} | Score: {comp.get('relevance_score', 0):.1f}")
    
    lines.append("")
    lines.append("NICHE DATA")
    for kw, data in competitor_data.get('niche_data', {}).items():
        lines.append(f"  {kw}: SV {data.get('search_volume', 'N/A')} | Rev ${data.get('revenue', 'N/A')}")
    
    text = '\n'.join(lines)
    return text[:MAX_CHARS]


def generate_review_summary(review_data: dict, asin: str = "") -> str:
    """Generate review intelligence summary."""
    lines = [
        f"REVIEW INTELLIGENCE — {asin}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
        f"Reviews Analyzed: {review_data.get('total_reviews', 0)}",
        "=" * 50,
        "",
        f"Avg Rating: {review_data.get('avg_rating', 0):.1f}★ | Sentiment: {review_data.get('avg_sentiment', 0):+.3f}",
        "",
        "THEME ANALYSIS",
    ]
    
    for theme in review_data.get('themes', [])[:8]:
        emoji = '🟢' if theme.get('sentiment', 0) > 0.1 else ('🔴' if theme.get('sentiment', 0) < -0.1 else '🟡')
        lines.append(f"  {emoji} {theme.get('label', '')}: {theme.get('mentions', 0)} mentions | "
                     f"sentiment {theme.get('sentiment', 0):+.3f}")
    
    lines.append("")
    lines.append("STRENGTHS")
    for s in review_data.get('strengths', [])[:3]:
        lines.append(f"  ✅ {s}")
    
    lines.append("")
    lines.append("WEAKNESSES")
    for w in review_data.get('weaknesses', [])[:3]:
        lines.append(f"  ⚠️ {w}")
    
    lines.append("")
    lines.append("TOP PAIN POINTS")
    for p in review_data.get('pain_points', [])[:5]:
        lines.append(f"  • {p}")
    
    text = '\n'.join(lines)
    return text[:MAX_CHARS]


def generate_daily_snapshot_summary(snapshot: dict) -> str:
    """Generate a compact daily snapshot for trending."""
    lines = [
        f"DAILY SNAPSHOT — {snapshot.get('date', 'N/A')}",
        "=" * 40,
    ]
    
    for asin, metrics in snapshot.get('products', {}).items():
        lines.append(f"\n{asin}:")
        lines.append(f"  Sales: ${metrics.get('sales', 0):,.2f} | Spend: ${metrics.get('spend', 0):,.2f}")
        lines.append(f"  ACOS: {metrics.get('acos', 0):.1f}% | BSR: #{metrics.get('bsr', 'N/A')}")
    
    return '\n'.join(lines)
