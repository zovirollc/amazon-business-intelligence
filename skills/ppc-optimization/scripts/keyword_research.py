#!/usr/bin/env python3
"""
Keyword Research & Prioritization for PPC
Merges Cerebro keyword data with search term performance to build a prioritized keyword list.
"""

import csv
import json
import argparse
import os
import math


def parse_cerebro_csv(csv_path):
    """Parse H10 Cerebro CSV export."""
    keywords = {}
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            kw = {}
            keyword = ''
            for key, val in row.items():
                key_lower = key.strip().lower().replace(' ', '_')
                if 'keyword' in key_lower and 'phrase' in key_lower:
                    keyword = val.strip().lower()
                elif key_lower == 'search_volume' or (key_lower.startswith('search_vol') and 'trend' not in key_lower):
                    kw['search_volume'] = parse_int(val)
                elif 'competing' in key_lower and 'product' in key_lower:
                    kw['competing_products'] = parse_int(val)
                elif 'position' in key_lower and 'organic' in key_lower:
                    kw['organic_rank'] = parse_int(val)
                elif 'position' in key_lower and 'sponsor' in key_lower:
                    kw['sponsored_rank'] = parse_int(val)
                elif key_lower == 'cpr':
                    kw['cpr'] = parse_int(val)
                elif 'suggested' in key_lower and 'bid' in key_lower:
                    kw['suggested_bid'] = parse_float(val)

            if keyword and kw.get('search_volume', 0) > 0:
                kw['keyword'] = keyword
                keywords[keyword] = kw

    return keywords


def parse_int(val):
    if not val:
        return 0
    try:
        return int(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0


def parse_float(val):
    if not val:
        return 0.0
    try:
        return float(str(val).replace('$', '').replace(',', '').strip())
    except (ValueError, TypeError):
        return 0.0


def merge_keyword_data(cerebro_keywords, search_terms):
    """Merge Cerebro keyword data with actual search term performance."""
    merged = {}

    # Start with all Cerebro keywords
    for kw, data in cerebro_keywords.items():
        merged[kw] = {
            **data,
            'source': 'cerebro',
            'has_ppc_data': False,
            'ppc_impressions': 0,
            'ppc_clicks': 0,
            'ppc_spend': 0,
            'ppc_sales': 0,
            'ppc_orders': 0,
            'ppc_acos': 0,
            'ppc_cvr': 0,
        }

    # Overlay search term performance
    for term in search_terms:
        kw = term['search_term']
        if kw in merged:
            merged[kw]['has_ppc_data'] = True
            merged[kw]['ppc_impressions'] = term['impressions']
            merged[kw]['ppc_clicks'] = term['clicks']
            merged[kw]['ppc_spend'] = term['spend']
            merged[kw]['ppc_sales'] = term['sales']
            merged[kw]['ppc_orders'] = term['orders']
            merged[kw]['ppc_acos'] = term['acos']
            merged[kw]['ppc_cvr'] = term['cvr']
            merged[kw]['ppc_classification'] = term.get('classification', '')
        else:
            # Search term not in Cerebro — discovered via auto/broad
            merged[kw] = {
                'keyword': kw,
                'search_volume': 0,  # Unknown
                'competing_products': 0,
                'organic_rank': 0,
                'sponsored_rank': 0,
                'source': 'ppc_discovered',
                'has_ppc_data': True,
                'ppc_impressions': term['impressions'],
                'ppc_clicks': term['clicks'],
                'ppc_spend': term['spend'],
                'ppc_sales': term['sales'],
                'ppc_orders': term['orders'],
                'ppc_acos': term['acos'],
                'ppc_cvr': term['cvr'],
                'ppc_classification': term.get('classification', ''),
            }

    return merged


def calculate_ppc_priority(kw_data, target_acos=30):
    """
    Calculate PPC priority score.
    Higher = more important to target/scale.
    """
    sv = kw_data.get('search_volume', 0)
    competing = kw_data.get('competing_products', 1)
    has_ppc = kw_data.get('has_ppc_data', False)
    ppc_cvr = kw_data.get('ppc_cvr', 0)
    ppc_acos = kw_data.get('ppc_acos', 0)
    ppc_orders = kw_data.get('ppc_orders', 0)

    # Search Volume score (0-25)
    sv_score = min(25, math.log10(max(sv, 1)) * 6) if sv > 0 else 5  # 5 for unknown SV

    # Conversion score (0-30) — proven converters get highest priority
    if has_ppc and ppc_orders > 0:
        if ppc_cvr >= 15:
            cvr_score = 30
        elif ppc_cvr >= 10:
            cvr_score = 25
        elif ppc_cvr >= 5:
            cvr_score = 18
        else:
            cvr_score = 10
    elif has_ppc and ppc_orders == 0:
        cvr_score = 2  # Had impressions but no conversion
    else:
        cvr_score = 10  # Unknown — moderate default

    # Competition score (0-20) — lower competition = higher score
    if competing > 0:
        comp_score = max(0, 20 - math.log10(competing) * 5)
    else:
        comp_score = 10

    # ACOS efficiency score (0-25)
    if has_ppc and ppc_orders > 0:
        if ppc_acos <= target_acos * 0.5:
            acos_score = 25  # Very profitable
        elif ppc_acos <= target_acos:
            acos_score = 20  # Within target
        elif ppc_acos <= target_acos * 1.5:
            acos_score = 10  # Slightly above target
        else:
            acos_score = 3  # Well above target
    elif has_ppc and ppc_orders == 0:
        acos_score = 0  # No sales
    else:
        acos_score = 12  # Unknown

    total = sv_score + cvr_score + comp_score + acos_score
    return round(total, 1)


def assign_match_type(kw_data, priority_score):
    """Determine recommended match type based on data."""
    has_ppc = kw_data.get('has_ppc_data', False)
    ppc_orders = kw_data.get('ppc_orders', 0)
    ppc_acos = kw_data.get('ppc_acos', 0)
    sv = kw_data.get('search_volume', 0)
    word_count = len(kw_data.get('keyword', '').split())

    # Proven converters → exact match
    if has_ppc and ppc_orders >= 3 and ppc_acos <= 40:
        return 'exact'

    # Good volume + moderate data → phrase match
    if sv >= 500 or (has_ppc and ppc_orders >= 1):
        return 'phrase'

    # Long-tail or discovery → broad
    if word_count >= 3 or not has_ppc:
        return 'broad'

    return 'phrase'  # default


def assign_tier(kw_data, priority_score, match_type):
    """Assign keyword to a tier."""
    ppc_classification = kw_data.get('ppc_classification', '')

    if ppc_classification == 'wasted_spend':
        return 'negative_candidate'

    if match_type == 'exact' and priority_score >= 60:
        return 'tier_1_exact'
    elif match_type in ('exact', 'phrase') and priority_score >= 40:
        return 'tier_2_phrase'
    elif priority_score >= 20:
        return 'tier_3_broad'
    else:
        return 'tier_4_monitor'


def run_keyword_research(cerebro_csv, search_terms_path, config_path, output_path):
    """Main keyword research pipeline."""

    # Load data
    cerebro_keywords = parse_cerebro_csv(cerebro_csv)
    print(f"Parsed {len(cerebro_keywords)} keywords from Cerebro")

    with open(search_terms_path) as f:
        search_data = json.load(f)
    search_terms = search_data.get('search_terms', [])
    print(f"Loaded {len(search_terms)} search terms from PPC data")

    with open(config_path) as f:
        config = json.load(f)

    # Merge data sources
    merged = merge_keyword_data(cerebro_keywords, search_terms)
    print(f"Merged to {len(merged)} unique keywords")

    # Calculate priorities and assign match types
    results = []
    for kw, data in merged.items():
        priority = calculate_ppc_priority(data)
        match_type = assign_match_type(data, priority)
        tier = assign_tier(data, priority, match_type)

        results.append({
            **data,
            'ppc_priority_score': priority,
            'recommended_match_type': match_type,
            'tier': tier,
        })

    results.sort(key=lambda x: x['ppc_priority_score'], reverse=True)

    # Summary
    from collections import Counter
    tier_counts = Counter(r['tier'] for r in results)

    output = {
        'total_keywords': len(results),
        'cerebro_keywords': len(cerebro_keywords),
        'ppc_discovered_keywords': sum(1 for r in results if r['source'] == 'ppc_discovered'),
        'tier_counts': dict(tier_counts),
        'keywords': results
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nKeyword Research Complete:")
    print(f"  Tier 1 (Exact): {tier_counts.get('tier_1_exact', 0)}")
    print(f"  Tier 2 (Phrase): {tier_counts.get('tier_2_phrase', 0)}")
    print(f"  Tier 3 (Broad): {tier_counts.get('tier_3_broad', 0)}")
    print(f"  Tier 4 (Monitor): {tier_counts.get('tier_4_monitor', 0)}")
    print(f"  Negative candidates: {tier_counts.get('negative_candidate', 0)}")
    print(f"\nSaved to: {output_path}")

    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PPC Keyword Research & Prioritization')
    parser.add_argument('--cerebro-csv', required=True)
    parser.add_argument('--search-terms', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    run_keyword_research(args.cerebro_csv, args.search_terms, args.config, args.output)
