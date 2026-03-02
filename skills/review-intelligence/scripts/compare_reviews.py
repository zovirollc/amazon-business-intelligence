#!/usr/bin/env python3
"""
Step 3: Competitive Review Comparison
Compares our product reviews vs competitors on rating, sentiment, themes,
and generates a strength/weakness matrix.
"""

import os
import json
from collections import defaultdict
from datetime import datetime


def build_comparison(our_asin, analysis_data):
    """
    Build comparative analysis between our product and competitors.
    """
    asin_stats = analysis_data.get('asin_stats', {})
    reviews = analysis_data.get('reviews', [])
    theme_analysis = analysis_data.get('theme_analysis', {})

    if our_asin not in asin_stats:
        print(f"  ⚠️  Our ASIN {our_asin} not found in review data")
        print(f"  Available ASINs: {list(asin_stats.keys())}")
        our_data = None
    else:
        our_data = asin_stats[our_asin]

    competitor_asins = [a for a in asin_stats.keys() if a != our_asin]
    print(f"  Our ASIN: {our_asin} ({our_data['review_count'] if our_data else 0} reviews)")
    print(f"  Competitors: {len(competitor_asins)} ASINs")

    # ─── Rating Comparison ────────────────────────────────────────────────
    rating_comparison = []
    for asin, stats in sorted(asin_stats.items(), key=lambda x: x[1]['avg_rating'], reverse=True):
        rating_comparison.append({
            'asin': asin,
            'product_name': stats.get('product_name', ''),
            'is_ours': asin == our_asin,
            'review_count': stats['review_count'],
            'avg_rating': stats['avg_rating'],
            'avg_sentiment': stats['avg_sentiment'],
            'rating_distribution': stats['rating_distribution'],
        })

    our_rank = next((i + 1 for i, r in enumerate(rating_comparison) if r['is_ours']), None)

    # ─── Theme Comparison Matrix ──────────────────────────────────────────
    # For each theme, compare our mentions vs competitor average
    theme_by_asin = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'sentiments': []}))

    for r in reviews:
        asin = r.get('asin', '')
        for theme in r.get('themes', []):
            theme_by_asin[asin][theme]['count'] += 1
            theme_by_asin[asin][theme]['sentiments'].append(r.get('sentiment', 0))

    theme_comparison = {}
    for theme_id in theme_analysis.keys():
        our_theme = theme_by_asin.get(our_asin, {}).get(theme_id, {'count': 0, 'sentiments': []})
        our_count = our_theme['count']
        our_sent = our_theme['sentiments']

        comp_counts = []
        comp_sents = []
        for asin in competitor_asins:
            ct = theme_by_asin.get(asin, {}).get(theme_id, {'count': 0, 'sentiments': []})
            comp_counts.append(ct['count'])
            comp_sents.extend(ct['sentiments'])

        avg_comp_count = sum(comp_counts) / len(comp_counts) if comp_counts else 0
        avg_comp_sent = sum(comp_sents) / len(comp_sents) if comp_sents else 0
        our_avg_sent = sum(our_sent) / len(our_sent) if our_sent else 0

        theme_comparison[theme_id] = {
            'label': theme_analysis[theme_id]['label'],
            'our_mentions': our_count,
            'our_sentiment': round(our_avg_sent, 3),
            'avg_competitor_mentions': round(avg_comp_count, 1),
            'avg_competitor_sentiment': round(avg_comp_sent, 3),
            'sentiment_gap': round(our_avg_sent - avg_comp_sent, 3),  # Positive = we're better
        }

    # ─── Strength/Weakness Matrix ─────────────────────────────────────────
    strengths = []
    weaknesses = []
    opportunities = []

    for theme_id, comp in theme_comparison.items():
        gap = comp['sentiment_gap']
        our_sent = comp['our_sentiment']
        comp_sent = comp['avg_competitor_sentiment']

        if gap > 0.1 and our_sent > 0:
            strengths.append({
                'theme': comp['label'],
                'theme_id': theme_id,
                'our_sentiment': our_sent,
                'competitor_sentiment': comp_sent,
                'gap': gap,
                'insight': f"Customers rate our {comp['label'].lower()} higher than competitors (+{gap:.2f})",
            })
        elif gap < -0.1 and comp_sent > 0:
            weaknesses.append({
                'theme': comp['label'],
                'theme_id': theme_id,
                'our_sentiment': our_sent,
                'competitor_sentiment': comp_sent,
                'gap': gap,
                'insight': f"Competitors score better on {comp['label'].lower()} ({gap:.2f} gap)",
            })

        # Opportunities: themes where competitors get many negative reviews
        if comp_sent < -0.1 and comp['avg_competitor_mentions'] > 3:
            opportunities.append({
                'theme': comp['label'],
                'theme_id': theme_id,
                'competitor_sentiment': comp_sent,
                'mentions': comp['avg_competitor_mentions'],
                'insight': f"Competitor weakness in {comp['label'].lower()} — opportunity to differentiate",
            })

    strengths.sort(key=lambda x: x['gap'], reverse=True)
    weaknesses.sort(key=lambda x: x['gap'])
    opportunities.sort(key=lambda x: x['competitor_sentiment'])

    # ─── Top Negative Quotes from Competitors ─────────────────────────────
    competitor_complaints = []
    for r in reviews:
        if r.get('asin') != our_asin and r.get('rating', 5) <= 2 and r.get('body'):
            competitor_complaints.append({
                'asin': r['asin'],
                'rating': r['rating'],
                'title': r.get('title', ''),
                'excerpt': r['body'][:200],
                'themes': r.get('themes', []),
                'sentiment': r.get('sentiment', 0),
            })
    competitor_complaints.sort(key=lambda x: x['sentiment'])

    # ─── Top Positive Quotes from Us ──────────────────────────────────────
    our_highlights = []
    for r in reviews:
        if r.get('asin') == our_asin and r.get('rating', 0) >= 4 and r.get('body'):
            our_highlights.append({
                'rating': r['rating'],
                'title': r.get('title', ''),
                'excerpt': r['body'][:200],
                'themes': r.get('themes', []),
                'sentiment': r.get('sentiment', 0),
                'helpful_votes': r.get('helpful_votes', 0),
            })
    our_highlights.sort(key=lambda x: (x['helpful_votes'], x['sentiment']), reverse=True)

    result = {
        'our_asin': our_asin,
        'our_stats': our_data,
        'our_rank': our_rank,
        'total_products': len(asin_stats),
        'rating_comparison': rating_comparison,
        'theme_comparison': theme_comparison,
        'strengths': strengths[:10],
        'weaknesses': weaknesses[:10],
        'opportunities': opportunities[:10],
        'competitor_top_complaints': competitor_complaints[:20],
        'our_top_highlights': our_highlights[:10],
        'compared_at': datetime.now().isoformat(),
    }

    return result


def run_comparison(our_asin, input_path, output_dir):
    """Load analysis data and run comparison."""
    print("Loading review analysis...")
    with open(input_path) as f:
        analysis_data = json.load(f)

    print(f"\n--- Competitive Review Comparison ---")
    result = build_comparison(our_asin, analysis_data)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'review_comparison.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*50}")
    print(f"Comparison Complete:")
    print(f"  Our rating rank: #{result['our_rank']}/{result['total_products']}")
    if result['our_stats']:
        print(f"  Our avg rating: {result['our_stats']['avg_rating']}★")
        print(f"  Our avg sentiment: {result['our_stats']['avg_sentiment']}")

    print(f"\n  Strengths ({len(result['strengths'])}):")
    for s in result['strengths'][:5]:
        print(f"    ✅ {s['insight']}")

    print(f"\n  Weaknesses ({len(result['weaknesses'])}):")
    for w in result['weaknesses'][:5]:
        print(f"    ⚠️  {w['insight']}")

    print(f"\n  Opportunities ({len(result['opportunities'])}):")
    for o in result['opportunities'][:5]:
        print(f"    💡 {o['insight']}")

    print(f"\n  Saved to: {output_path}")
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compare Reviews')
    parser.add_argument('--our-asin', type=str, required=True, help='Our product ASIN')
    parser.add_argument('--input', type=str, required=True, help='review_analysis.json path')
    parser.add_argument('--output', type=str, required=True, help='Output directory')
    args = parser.parse_args()

    run_comparison(args.our_asin, args.input, args.output)
