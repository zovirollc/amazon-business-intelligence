#!/usr/bin/env python3
"""
Parse & Clean Seller Central Search Term Report
Processes raw CSV into structured JSON with calculated metrics.
"""

import csv
import json
import argparse
import os
import re


def parse_currency(val):
    """Parse currency string to float."""
    if not val:
        return 0.0
    try:
        return float(str(val).replace('$', '').replace(',', '').replace('%', '').strip())
    except (ValueError, TypeError):
        return 0.0


def parse_int_val(val):
    """Parse integer from string."""
    if not val:
        return 0
    try:
        return int(str(val).replace(',', '').strip())
    except (ValueError, TypeError):
        return 0


def detect_csv_format(headers):
    """Detect which Seller Central report format this is."""
    headers_lower = [h.lower().strip() for h in headers]

    # Standard Search Term Report columns
    if any('customer search term' in h for h in headers_lower):
        return 'search_term_report'
    elif any('search term' in h for h in headers_lower):
        return 'search_term_report'
    elif any('targeting' in h for h in headers_lower):
        return 'targeting_report'
    else:
        return 'unknown'


def find_column(headers, *patterns):
    """Find column index matching any of the given patterns."""
    for i, h in enumerate(headers):
        h_lower = h.lower().strip()
        for pattern in patterns:
            if pattern in h_lower:
                return i
    return None


def parse_search_term_csv(csv_path):
    """Parse Seller Central search term report CSV."""
    rows = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        # Skip potential metadata rows at top
        lines = f.readlines()

    # Find header row (first row with "Campaign" or "Search Term")
    header_idx = 0
    for i, line in enumerate(lines):
        if 'campaign' in line.lower() and ('search' in line.lower() or 'targeting' in line.lower()):
            header_idx = i
            break

    # Parse from header row
    reader = csv.reader(lines[header_idx:])
    headers = next(reader)

    # Map columns
    col_map = {
        'campaign': find_column(headers, 'campaign name', 'campaign'),
        'ad_group': find_column(headers, 'ad group name', 'ad group'),
        'targeting': find_column(headers, 'targeting', 'keyword'),
        'match_type': find_column(headers, 'match type'),
        'search_term': find_column(headers, 'customer search term', 'search term', 'query'),
        'impressions': find_column(headers, 'impressions'),
        'clicks': find_column(headers, 'clicks'),
        'ctr': find_column(headers, 'click-thru', 'ctr'),
        'cpc': find_column(headers, 'cost per click', 'cpc'),
        'spend': find_column(headers, 'spend', 'cost'),
        'sales': find_column(headers, '7 day total sales', 'total sales', 'sales'),
        'acos': find_column(headers, 'total acos', 'acos'),
        'orders': find_column(headers, '7 day total orders', 'total orders', 'orders'),
        'units': find_column(headers, '7 day total units', 'total units', 'units'),
    }

    for row in reader:
        if len(row) < 5:
            continue

        search_term = row[col_map['search_term']].strip() if col_map['search_term'] is not None else ''
        if not search_term or search_term == '*':
            continue

        impressions = parse_int_val(row[col_map['impressions']]) if col_map['impressions'] is not None else 0
        clicks = parse_int_val(row[col_map['clicks']]) if col_map['clicks'] is not None else 0
        spend = parse_currency(row[col_map['spend']]) if col_map['spend'] is not None else 0
        sales = parse_currency(row[col_map['sales']]) if col_map['sales'] is not None else 0
        orders = parse_int_val(row[col_map['orders']]) if col_map['orders'] is not None else 0

        # Calculate metrics
        acos = (spend / sales * 100) if sales > 0 else 0
        cvr = (orders / clicks * 100) if clicks > 0 else 0
        cpc = (spend / clicks) if clicks > 0 else 0
        rpc = (sales / clicks) if clicks > 0 else 0  # revenue per click

        record = {
            'search_term': search_term.lower().strip(),
            'campaign': row[col_map['campaign']].strip() if col_map['campaign'] is not None else '',
            'ad_group': row[col_map['ad_group']].strip() if col_map['ad_group'] is not None else '',
            'targeting': row[col_map['targeting']].strip() if col_map['targeting'] is not None else '',
            'match_type': row[col_map['match_type']].strip() if col_map['match_type'] is not None else '',
            'impressions': impressions,
            'clicks': clicks,
            'spend': round(spend, 2),
            'sales': round(sales, 2),
            'orders': orders,
            'acos': round(acos, 2),
            'cvr': round(cvr, 2),
            'cpc': round(cpc, 2),
            'revenue_per_click': round(rpc, 2),
        }
        rows.append(record)

    return rows


def aggregate_search_terms(rows):
    """Aggregate metrics for duplicate search terms across campaigns."""
    from collections import defaultdict
    aggregated = defaultdict(lambda: {
        'impressions': 0, 'clicks': 0, 'spend': 0, 'sales': 0, 'orders': 0,
        'campaigns': set(), 'match_types': set()
    })

    for row in rows:
        term = row['search_term']
        agg = aggregated[term]
        agg['impressions'] += row['impressions']
        agg['clicks'] += row['clicks']
        agg['spend'] += row['spend']
        agg['sales'] += row['sales']
        agg['orders'] += row['orders']
        agg['campaigns'].add(row['campaign'])
        agg['match_types'].add(row['match_type'])

    results = []
    for term, agg in aggregated.items():
        clicks = agg['clicks']
        sales = agg['sales']
        orders = agg['orders']
        spend = agg['spend']

        results.append({
            'search_term': term,
            'impressions': agg['impressions'],
            'clicks': clicks,
            'spend': round(spend, 2),
            'sales': round(sales, 2),
            'orders': orders,
            'acos': round((spend / sales * 100) if sales > 0 else 0, 2),
            'cvr': round((orders / clicks * 100) if clicks > 0 else 0, 2),
            'cpc': round((spend / clicks) if clicks > 0 else 0, 2),
            'revenue_per_click': round((sales / clicks) if clicks > 0 else 0, 2),
            'campaign_count': len(agg['campaigns']),
            'match_types': list(agg['match_types']),
            'word_count': len(term.split()),
        })

    return sorted(results, key=lambda x: x['spend'], reverse=True)


def classify_search_terms(terms, target_acos=30):
    """Classify each search term into performance categories."""
    for term in terms:
        clicks = term['clicks']
        orders = term['orders']
        acos = term['acos']
        spend = term['spend']

        if orders > 0 and acos <= target_acos:
            term['classification'] = 'winner'  # Profitable
            term['action'] = 'scale_up'
        elif orders > 0 and acos <= target_acos * 1.5:
            term['classification'] = 'marginal'  # Slightly above target
            term['action'] = 'optimize_bid'
        elif orders > 0 and acos > target_acos * 1.5:
            term['classification'] = 'bleeder'  # High ACOS
            term['action'] = 'reduce_bid'
        elif clicks >= 15 and orders == 0:
            term['classification'] = 'wasted_spend'  # Lots of clicks, no sales
            term['action'] = 'consider_negative'
        elif clicks >= 5 and orders == 0:
            term['classification'] = 'under_review'  # Some clicks, no sales yet
            term['action'] = 'monitor'
        elif clicks < 5 and spend < 5:
            term['classification'] = 'insufficient_data'  # Need more impressions
            term['action'] = 'increase_bid'
        else:
            term['classification'] = 'neutral'
            term['action'] = 'monitor'

    return terms


def run_parse(input_path, output_path):
    """Main parsing pipeline."""
    # Parse raw CSV
    raw_rows = parse_search_term_csv(input_path)
    print(f"Parsed {len(raw_rows)} raw rows from search term report")

    # Aggregate by search term
    aggregated = aggregate_search_terms(raw_rows)
    print(f"Aggregated to {len(aggregated)} unique search terms")

    # Classify performance
    classified = classify_search_terms(aggregated)

    # Summary stats
    from collections import Counter
    class_counts = Counter(t['classification'] for t in classified)
    total_spend = sum(t['spend'] for t in classified)
    total_sales = sum(t['sales'] for t in classified)
    overall_acos = (total_spend / total_sales * 100) if total_sales > 0 else 0

    result = {
        'total_unique_terms': len(classified),
        'total_raw_rows': len(raw_rows),
        'total_spend': round(total_spend, 2),
        'total_sales': round(total_sales, 2),
        'overall_acos': round(overall_acos, 2),
        'classification_summary': dict(class_counts),
        'search_terms': classified
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nSearch Term Analysis Summary:")
    print(f"  Total spend: ${total_spend:,.2f}")
    print(f"  Total sales: ${total_sales:,.2f}")
    print(f"  Overall ACOS: {overall_acos:.1f}%")
    print(f"  Winners: {class_counts.get('winner', 0)}")
    print(f"  Bleeders: {class_counts.get('bleeder', 0)}")
    print(f"  Wasted spend: {class_counts.get('wasted_spend', 0)}")
    print(f"\nSaved to: {output_path}")

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse Seller Central Search Term Report')
    parser.add_argument('--input', required=True, help='Path to search term report CSV')
    parser.add_argument('--output', required=True, help='Output JSON path')
    args = parser.parse_args()

    run_parse(args.input, args.output)
