#!/usr/bin/env python3
"""
Campaign Structure Designer for PPC Optimization
Generates recommended campaign architecture based on keyword priorities.
"""

import json
import argparse
import os
import math


def design_sp_exact_campaign(tier1_keywords, product_name, target_acos, avg_price):
    """Design Sponsored Products - Exact Match campaign for proven winners."""

    # Group keywords by theme
    brand_kws = []
    category_kws = []
    feature_kws = []

    for kw in tier1_keywords:
        keyword = kw.get('keyword', '')
        if any(term in keyword for term in ['zoviro', 'brand']):
            brand_kws.append(kw)
        elif any(term in keyword for term in ['hand wipe', 'sanitizer', 'antibacterial', 'disinfect']):
            category_kws.append(kw)
        else:
            feature_kws.append(kw)

    # If no brand keywords, merge into category
    if not brand_kws:
        category_kws = tier1_keywords

    campaign = {
        'campaign_name': f'SP - {product_name} - Exact Winners',
        'campaign_type': 'Sponsored Products',
        'targeting_type': 'Manual',
        'match_type': 'Exact',
        'bidding_strategy': 'Dynamic bids - down only',
        'daily_budget': 0,  # Will be calculated
        'ad_groups': []
    }

    if category_kws:
        # Calculate bids
        for kw in category_kws:
            cvr = kw.get('ppc_cvr', 10) / 100
            if cvr > 0:
                suggested_bid = round((target_acos / 100) * avg_price * cvr, 2)
            else:
                suggested_bid = round(kw.get('suggested_bid', 1.0), 2)
            kw['calculated_bid'] = max(0.30, min(suggested_bid, 5.00))

        campaign['ad_groups'].append({
            'ad_group_name': 'Category Keywords',
            'default_bid': round(sum(kw['calculated_bid'] for kw in category_kws) / len(category_kws), 2),
            'keywords': [{
                'keyword': kw['keyword'],
                'match_type': 'exact',
                'bid': kw['calculated_bid'],
                'search_volume': kw.get('search_volume', 0),
                'historical_acos': kw.get('ppc_acos', 0),
                'historical_cvr': kw.get('ppc_cvr', 0),
            } for kw in category_kws]
        })

    if feature_kws:
        for kw in feature_kws:
            cvr = kw.get('ppc_cvr', 10) / 100
            if cvr > 0:
                suggested_bid = round((target_acos / 100) * avg_price * cvr, 2)
            else:
                suggested_bid = round(kw.get('suggested_bid', 0.80), 2)
            kw['calculated_bid'] = max(0.30, min(suggested_bid, 5.00))

        campaign['ad_groups'].append({
            'ad_group_name': 'Feature Keywords',
            'default_bid': round(sum(kw['calculated_bid'] for kw in feature_kws) / len(feature_kws), 2),
            'keywords': [{
                'keyword': kw['keyword'],
                'match_type': 'exact',
                'bid': kw['calculated_bid'],
                'search_volume': kw.get('search_volume', 0),
                'historical_acos': kw.get('ppc_acos', 0),
            } for kw in feature_kws]
        })

    # Calculate budget: sum of (bid × estimated daily clicks) per keyword
    total_daily_spend = sum(
        kw.get('calculated_bid', 1.0) * max(2, kw.get('ppc_clicks', 5) / 30)
        for kw in tier1_keywords
    )
    campaign['daily_budget'] = round(max(10, total_daily_spend * 1.2), 2)

    return campaign


def design_sp_research_campaign(tier2_keywords, tier3_keywords, product_name, target_acos, avg_price):
    """Design Sponsored Products - Research campaign (phrase + broad)."""

    campaign = {
        'campaign_name': f'SP - {product_name} - Research',
        'campaign_type': 'Sponsored Products',
        'targeting_type': 'Manual',
        'bidding_strategy': 'Dynamic bids - down only',
        'daily_budget': 0,
        'ad_groups': []
    }

    # Phrase match ad group
    if tier2_keywords:
        for kw in tier2_keywords:
            cvr = kw.get('ppc_cvr', 8) / 100
            base_bid = round((target_acos / 100) * avg_price * max(cvr, 0.05), 2)
            kw['calculated_bid'] = max(0.25, min(base_bid * 0.85, 4.00))  # 15% lower than exact

        campaign['ad_groups'].append({
            'ad_group_name': 'Phrase Match - Category',
            'default_bid': round(sum(kw['calculated_bid'] for kw in tier2_keywords) / len(tier2_keywords), 2),
            'match_type': 'phrase',
            'keywords': [{
                'keyword': kw['keyword'],
                'match_type': 'phrase',
                'bid': kw['calculated_bid'],
                'search_volume': kw.get('search_volume', 0),
            } for kw in tier2_keywords[:30]]  # Limit to top 30
        })

    # Broad match ad group
    if tier3_keywords:
        for kw in tier3_keywords:
            base_bid = round(kw.get('suggested_bid', 0.60) * 0.7, 2)  # 30% lower
            kw['calculated_bid'] = max(0.20, min(base_bid, 3.00))

        campaign['ad_groups'].append({
            'ad_group_name': 'Broad Match - Discovery',
            'default_bid': round(sum(kw['calculated_bid'] for kw in tier3_keywords[:20]) / min(len(tier3_keywords), 20), 2),
            'match_type': 'broad',
            'keywords': [{
                'keyword': kw['keyword'],
                'match_type': 'broad',
                'bid': kw['calculated_bid'],
                'search_volume': kw.get('search_volume', 0),
            } for kw in tier3_keywords[:20]]  # Limit to top 20
        })

    total_kws = tier2_keywords + tier3_keywords[:20]
    total_daily = sum(kw.get('calculated_bid', 0.5) * 2 for kw in total_kws)
    campaign['daily_budget'] = round(max(8, total_daily), 2)

    return campaign


def design_sp_auto_campaign(product_name, daily_budget_pct=0.15):
    """Design Sponsored Products - Auto campaign for discovery."""

    return {
        'campaign_name': f'SP - {product_name} - Auto',
        'campaign_type': 'Sponsored Products',
        'targeting_type': 'Auto',
        'bidding_strategy': 'Dynamic bids - down only',
        'daily_budget': 0,  # Will be calculated as % of total
        'ad_groups': [
            {
                'ad_group_name': 'Close Match',
                'targeting_type': 'close_match',
                'default_bid': 0.75,
                'note': 'Keywords closely related to your product'
            },
            {
                'ad_group_name': 'Loose Match',
                'targeting_type': 'loose_match',
                'default_bid': 0.50,
                'note': 'Keywords loosely related to your product'
            },
            {
                'ad_group_name': 'Substitutes',
                'targeting_type': 'substitutes',
                'default_bid': 0.60,
                'note': 'Products similar to yours'
            },
            {
                'ad_group_name': 'Complements',
                'targeting_type': 'complements',
                'default_bid': 0.40,
                'note': 'Products frequently bought with yours'
            }
        ],
        'budget_allocation_pct': daily_budget_pct
    }


def run_campaign_structure(keyword_priorities_path, performance_path, config_path, asin, output_path):
    """Main campaign structure generation."""

    with open(keyword_priorities_path) as f:
        kw_data = json.load(f)

    with open(config_path) as f:
        config = json.load(f)

    # Get product info
    product_config = config.get('products', {}).get(asin, {})
    product_name = product_config.get('name', asin)
    # Shorten product name for campaign naming
    short_name = product_name.split('(')[0].strip() if '(' in product_name else product_name[:40]

    # Get average price from performance data or default
    target_acos = 30
    avg_price = 15.00  # Default, should come from product data

    if os.path.exists(performance_path):
        with open(performance_path) as f:
            perf = json.load(f)
        if perf.get('total_sales', 0) > 0 and perf.get('search_terms'):
            # Estimate avg price from sales/orders
            total_orders = sum(t.get('orders', 0) for t in perf['search_terms'])
            if total_orders > 0:
                avg_price = perf['total_sales'] / total_orders

    # Split keywords by tier
    all_kws = kw_data.get('keywords', [])
    tier1 = [kw for kw in all_kws if kw.get('tier') == 'tier_1_exact']
    tier2 = [kw for kw in all_kws if kw.get('tier') == 'tier_2_phrase']
    tier3 = [kw for kw in all_kws if kw.get('tier') == 'tier_3_broad']
    negatives = [kw for kw in all_kws if kw.get('tier') == 'negative_candidate']

    # Design campaigns
    campaigns = []

    if tier1:
        exact_campaign = design_sp_exact_campaign(tier1, short_name, target_acos, avg_price)
        campaigns.append(exact_campaign)

    if tier2 or tier3:
        research_campaign = design_sp_research_campaign(tier2, tier3, short_name, target_acos, avg_price)
        campaigns.append(research_campaign)

    auto_campaign = design_sp_auto_campaign(short_name)
    campaigns.append(auto_campaign)

    # Calculate total budget and set auto campaign budget
    total_manual_budget = sum(c['daily_budget'] for c in campaigns if c['targeting_type'] != 'Auto')
    auto_campaign['daily_budget'] = round(max(5, total_manual_budget * 0.2), 2)

    total_budget = sum(c['daily_budget'] for c in campaigns)

    # Cross-campaign negative keywords
    # Exact match winners should be negative in phrase/broad campaigns
    cross_negatives = [kw['keyword'] for kw in tier1]

    result = {
        'asin': asin,
        'product_name': product_name,
        'target_acos': target_acos,
        'avg_selling_price': round(avg_price, 2),
        'total_daily_budget': round(total_budget, 2),
        'total_monthly_budget': round(total_budget * 30, 2),
        'campaign_count': len(campaigns),
        'campaigns': campaigns,
        'cross_campaign_negatives': {
            'description': 'Add these as negative exact in Research & Auto campaigns to prevent cannibalization',
            'keywords': cross_negatives
        },
        'negative_keyword_candidates': [{
            'keyword': kw['keyword'],
            'reason': f"Spent ${kw.get('ppc_spend', 0):.2f} with {kw.get('ppc_orders', 0)} orders",
            'match_type': 'negative_exact'
        } for kw in negatives],
        'tier_summary': {
            'tier_1_exact': len(tier1),
            'tier_2_phrase': len(tier2),
            'tier_3_broad': len(tier3),
            'negative_candidates': len(negatives)
        }
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nCampaign Structure Designed:")
    print(f"  Campaigns: {len(campaigns)}")
    print(f"  Total daily budget: ${total_budget:.2f}")
    print(f"  Total monthly budget: ${total_budget * 30:.2f}")
    for c in campaigns:
        ag_count = len(c.get('ad_groups', []))
        kw_count = sum(len(ag.get('keywords', [])) for ag in c.get('ad_groups', []))
        print(f"  - {c['campaign_name']}: {ag_count} ad groups, {kw_count} keywords, ${c['daily_budget']}/day")
    print(f"  Cross-campaign negatives: {len(cross_negatives)}")
    print(f"  Negative candidates: {len(negatives)}")
    print(f"\nSaved to: {output_path}")

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Design PPC Campaign Structure')
    parser.add_argument('--keyword-priorities', required=True)
    parser.add_argument('--performance', required=True)
    parser.add_argument('--product-config', required=True)
    parser.add_argument('--asin', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    run_campaign_structure(args.keyword_priorities, args.performance, args.product_config, args.asin, args.output)
