#!/usr/bin/env python3
"""
Keyword Analysis Script for Listing Optimization
Processes Cerebro CSV data + competitor listing text to identify keyword priorities.
"""

import csv
import json
import argparse
import re
import os
from collections import defaultdict


def parse_cerebro_csv(csv_path):
    """Parse H10 Cerebro CSV export into keyword records."""
    keywords = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Cerebro CSV columns vary but typically include:
            # Keyword Phrase, Search Volume, Search Volume Trend,
            # Competing Products, CPR, Position (Organic), Position (Sponsored)
            kw = {}
            for key, val in row.items():
                key_lower = key.strip().lower().replace(' ', '_')
                if 'keyword' in key_lower and 'phrase' in key_lower:
                    kw['keyword'] = val.strip()
                elif key_lower == 'search_volume' or (key_lower.startswith('search_vol') and 'trend' not in key_lower):
                    kw['search_volume'] = parse_int(val)
                elif 'competing' in key_lower and 'product' in key_lower:
                    kw['competing_products'] = parse_int(val)
                elif key_lower == 'cpr' or key_lower == 'cerebro_product_rank':
                    kw['cpr'] = parse_int(val)
                elif 'position' in key_lower and 'organic' in key_lower:
                    kw['organic_rank'] = parse_int(val)
                elif 'position' in key_lower and 'sponsor' in key_lower:
                    kw['sponsored_rank'] = parse_int(val)
                elif key_lower == 'heading' or key_lower == 'word_count':
                    kw['word_count'] = parse_int(val)

            if kw.get('keyword') and kw.get('search_volume', 0) > 0:
                keywords.append(kw)

    return sorted(keywords, key=lambda x: x.get('search_volume', 0), reverse=True)


def parse_int(val):
    """Parse integer from string, handling commas and empty values."""
    if not val:
        return 0
    try:
        return int(str(val).replace(',', '').replace(' ', '').strip())
    except (ValueError, TypeError):
        return 0


def analyze_keyword_placement(keyword, listings):
    """Check where a keyword appears across competitor listings."""
    kw_lower = keyword.lower()
    placement = {
        'in_title': 0,
        'in_bullets': 0,
        'in_description': 0,
        'total_listings': len(listings),
        'listings_with_keyword': 0
    }

    for listing in listings:
        found = False
        title = listing.get('title', '').lower()
        bullets = ' '.join(listing.get('bullets', [])).lower()
        desc = listing.get('description', '').lower()

        if kw_lower in title:
            placement['in_title'] += 1
            found = True
        if kw_lower in bullets:
            placement['in_bullets'] += 1
            found = True
        if kw_lower in desc:
            placement['in_description'] += 1
            found = True
        if found:
            placement['listings_with_keyword'] += 1

    return placement


def calculate_keyword_priority(keyword_data, placement, competitor_count):
    """
    Calculate priority score for a keyword.
    Higher = more important to include in listing.
    """
    sv = keyword_data.get('search_volume', 0)
    competing = keyword_data.get('competing_products', 1)
    organic_rank = keyword_data.get('organic_rank', 0)

    # Base score from search volume (log scale, 0-40)
    import math
    sv_score = min(40, math.log10(max(sv, 1)) * 10) if sv > 0 else 0

    # Competition density score (lower competition = higher score, 0-20)
    if competing > 0:
        comp_score = max(0, 20 - math.log10(competing) * 5)
    else:
        comp_score = 20

    # Competitor usage score (more competitors use it = more important, 0-25)
    if competitor_count > 0:
        usage_ratio = placement.get('listings_with_keyword', 0) / competitor_count
        usage_score = usage_ratio * 25
    else:
        usage_score = 0

    # Current rank bonus (if we already rank, protect it, 0-15)
    rank_score = 0
    if organic_rank and 0 < organic_rank <= 10:
        rank_score = 15
    elif organic_rank and 0 < organic_rank <= 50:
        rank_score = 10
    elif organic_rank and 0 < organic_rank <= 100:
        rank_score = 5

    total = sv_score + comp_score + usage_score + rank_score
    return round(total, 1)


def categorize_keywords(keywords_with_scores):
    """
    Assign keywords to placement tiers:
    - title_priority: top 5-8 keywords for title
    - bullet_priority: next 15-20 keywords for bullet points
    - backend_priority: remaining relevant keywords for backend
    - skip: low priority keywords
    """
    sorted_kws = sorted(keywords_with_scores, key=lambda x: x['priority_score'], reverse=True)

    for i, kw in enumerate(sorted_kws):
        if i < 8 and kw['priority_score'] >= 50:
            kw['tier'] = 'title_priority'
        elif i < 28 and kw['priority_score'] >= 30:
            kw['tier'] = 'bullet_priority'
        elif kw['priority_score'] >= 15:
            kw['tier'] = 'backend_priority'
        else:
            kw['tier'] = 'skip'

    return sorted_kws


def run_analysis(cerebro_csv, our_asin, competitor_listings_path, output_path):
    """Main analysis pipeline."""

    # Load competitor listings
    with open(competitor_listings_path) as f:
        comp_data = json.load(f)
    competitor_listings = comp_data if isinstance(comp_data, list) else comp_data.get('listings', [])

    # Parse Cerebro data
    cerebro_keywords = parse_cerebro_csv(cerebro_csv)
    print(f"Parsed {len(cerebro_keywords)} keywords from Cerebro CSV")

    # Analyze each keyword
    results = []
    for kw_data in cerebro_keywords:
        keyword = kw_data['keyword']
        placement = analyze_keyword_placement(keyword, competitor_listings)
        priority = calculate_keyword_priority(kw_data, placement, len(competitor_listings))

        results.append({
            'keyword': keyword,
            'search_volume': kw_data.get('search_volume', 0),
            'competing_products': kw_data.get('competing_products', 0),
            'organic_rank': kw_data.get('organic_rank', 0),
            'sponsored_rank': kw_data.get('sponsored_rank', 0),
            'word_count': kw_data.get('word_count', len(keyword.split())),
            'competitor_title_usage': placement['in_title'],
            'competitor_bullet_usage': placement['in_bullets'],
            'competitor_total_usage': placement['listings_with_keyword'],
            'priority_score': priority,
            'tier': ''  # will be set by categorize
        })

    # Categorize into tiers
    results = categorize_keywords(results)

    # Summary stats
    title_kws = [r for r in results if r['tier'] == 'title_priority']
    bullet_kws = [r for r in results if r['tier'] == 'bullet_priority']
    backend_kws = [r for r in results if r['tier'] == 'backend_priority']

    output = {
        'our_asin': our_asin,
        'total_keywords_analyzed': len(results),
        'competitor_listings_count': len(competitor_listings),
        'tier_counts': {
            'title_priority': len(title_kws),
            'bullet_priority': len(bullet_kws),
            'backend_priority': len(backend_kws),
            'skip': len(results) - len(title_kws) - len(bullet_kws) - len(backend_kws)
        },
        'top_title_keywords': [r['keyword'] for r in title_kws],
        'top_bullet_keywords': [r['keyword'] for r in bullet_kws[:20]],
        'keywords': results
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nKeyword Analysis Complete:")
    print(f"  Title priority: {len(title_kws)} keywords")
    print(f"  Bullet priority: {len(bullet_kws)} keywords")
    print(f"  Backend priority: {len(backend_kws)} keywords")
    print(f"  Top title keywords: {', '.join(r['keyword'] for r in title_kws[:5])}")
    print(f"\nSaved to: {output_path}")

    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze keywords for listing optimization')
    parser.add_argument('--cerebro-csv', required=True, help='Path to Cerebro CSV export')
    parser.add_argument('--our-asin', required=True, help='Our product ASIN')
    parser.add_argument('--competitor-listings', required=True, help='Path to competitor listings JSON')
    parser.add_argument('--output', required=True, help='Output JSON path')
    args = parser.parse_args()

    run_analysis(args.cerebro_csv, args.our_asin, args.competitor_listings, args.output)
