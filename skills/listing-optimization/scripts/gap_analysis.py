#!/usr/bin/env python3
"""
Gap Analysis Script for Listing Optimization
Compares our listing against competitors to identify improvement areas.
"""

import json
import argparse
import os
import re
from collections import Counter


def score_title(our_listing, competitor_listings, keyword_analysis):
    """Score our title against competitors and keyword coverage."""
    our_title = our_listing.get('title', '')
    title_kws = keyword_analysis.get('top_title_keywords', [])

    # Title length analysis
    our_len = len(our_title)
    comp_lens = [len(c.get('title', '')) for c in competitor_listings if c.get('title')]
    avg_comp_len = sum(comp_lens) / len(comp_lens) if comp_lens else 150

    # Keyword coverage in title
    our_title_lower = our_title.lower()
    kws_in_title = [kw for kw in title_kws if kw.lower() in our_title_lower]
    kw_coverage = len(kws_in_title) / max(len(title_kws), 1)

    # Length score (150-200 chars optimal)
    if 150 <= our_len <= 200:
        length_score = 25
    elif 120 <= our_len <= 220:
        length_score = 18
    elif 80 <= our_len <= 250:
        length_score = 10
    else:
        length_score = 5

    # Keyword score (0-50)
    keyword_score = kw_coverage * 50

    # Structure score: does it follow Brand + Benefit + Type pattern? (0-25)
    has_brand = our_listing.get('brand', '').lower() in our_title_lower
    has_count = bool(re.search(r'\d+\s*(ct|count|pack|pcs|piece)', our_title_lower))
    structure_score = (15 if has_brand else 0) + (10 if has_count else 0)

    total = round(min(100, length_score + keyword_score + structure_score), 1)

    return {
        'score': total,
        'our_title': our_title,
        'our_length': our_len,
        'avg_competitor_length': round(avg_comp_len),
        'optimal_range': '150-200 chars',
        'keywords_covered': kws_in_title,
        'keywords_missing': [kw for kw in title_kws if kw.lower() not in our_title_lower],
        'has_brand': has_brand,
        'has_count_size': has_count,
        'recommendations': []
    }


def score_bullets(our_listing, competitor_listings, keyword_analysis):
    """Score our bullet points against competitors."""
    our_bullets = our_listing.get('bullets', [])
    bullet_kws = keyword_analysis.get('top_bullet_keywords', [])

    # Bullet count
    our_count = len(our_bullets)
    comp_counts = [len(c.get('bullets', [])) for c in competitor_listings]
    avg_comp_count = sum(comp_counts) / len(comp_counts) if comp_counts else 5

    # Average bullet length
    our_avg_len = sum(len(b) for b in our_bullets) / max(our_count, 1)
    comp_bullet_lens = []
    for c in competitor_listings:
        for b in c.get('bullets', []):
            comp_bullet_lens.append(len(b))
    avg_comp_bullet_len = sum(comp_bullet_lens) / len(comp_bullet_lens) if comp_bullet_lens else 200

    # Keyword coverage in bullets
    all_bullets_text = ' '.join(our_bullets).lower()
    kws_in_bullets = [kw for kw in bullet_kws if kw.lower() in all_bullets_text]
    kw_coverage = len(kws_in_bullets) / max(len(bullet_kws), 1)

    # Count score (5 bullets = full score)
    count_score = min(20, our_count * 4)

    # Length score (200-250 chars avg per bullet optimal)
    if 180 <= our_avg_len <= 260:
        length_score = 20
    elif 120 <= our_avg_len <= 300:
        length_score = 12
    else:
        length_score = 5

    # Keyword score
    keyword_score = kw_coverage * 40

    # Benefit-first check (rough heuristic: starts with caps word/phrase)
    benefit_first_count = sum(1 for b in our_bullets if b and (b[0].isupper() or b.startswith('✅') or b.startswith('★')))
    benefit_score = min(20, (benefit_first_count / max(our_count, 1)) * 20)

    total = round(min(100, count_score + length_score + keyword_score + benefit_score), 1)

    return {
        'score': total,
        'our_bullet_count': our_count,
        'avg_competitor_bullet_count': round(avg_comp_count, 1),
        'our_avg_bullet_length': round(our_avg_len),
        'avg_competitor_bullet_length': round(avg_comp_bullet_len),
        'optimal_bullet_length': '200-250 chars',
        'keywords_covered': kws_in_bullets,
        'keywords_missing': [kw for kw in bullet_kws if kw.lower() not in all_bullets_text],
        'benefit_first_ratio': round(benefit_first_count / max(our_count, 1), 2),
        'recommendations': []
    }


def score_images(our_listing, competitor_listings):
    """Score our image count and quality."""
    our_count = our_listing.get('imageCount', our_listing.get('image_count', 0))
    comp_counts = [c.get('imageCount', c.get('image_count', 0)) for c in competitor_listings]
    avg_comp_count = sum(comp_counts) / len(comp_counts) if comp_counts else 7

    # Image count score (7+ is ideal, max 9)
    if our_count >= 7:
        count_score = 60
    elif our_count >= 5:
        count_score = 40
    elif our_count >= 3:
        count_score = 25
    else:
        count_score = 10

    # We can't automatically detect infographics/lifestyle, so give partial score
    # This would need manual review or image analysis
    quality_score = 40 if our_count >= 6 else 20  # placeholder

    total = min(100, count_score + quality_score)

    return {
        'score': total,
        'our_image_count': our_count,
        'avg_competitor_image_count': round(avg_comp_count, 1),
        'optimal_count': '7-9 images',
        'recommendations': []
    }


def score_aplus(our_listing, competitor_listings):
    """Score A+ content presence."""
    has_aplus = our_listing.get('hasAPlus', our_listing.get('has_a_plus', False))
    comp_aplus = sum(1 for c in competitor_listings
                     if c.get('hasAPlus', c.get('has_a_plus', False)))
    comp_aplus_ratio = comp_aplus / len(competitor_listings) if competitor_listings else 0

    if has_aplus:
        score = 70  # Base score for having A+, detailed analysis needs manual review
    else:
        score = 0

    return {
        'score': score,
        'our_has_aplus': has_aplus,
        'competitor_aplus_count': comp_aplus,
        'competitor_aplus_ratio': round(comp_aplus_ratio, 2),
        'recommendations': []
    }


def identify_backend_keywords(keyword_analysis, our_listing):
    """Identify keywords that should go in backend search terms."""
    all_keywords = keyword_analysis.get('keywords', [])
    our_title = our_listing.get('title', '').lower()
    our_bullets = ' '.join(our_listing.get('bullets', [])).lower()
    our_text = our_title + ' ' + our_bullets

    backend_candidates = []
    for kw in all_keywords:
        keyword = kw.get('keyword', '')
        if keyword.lower() not in our_text and kw.get('search_volume', 0) >= 100:
            backend_candidates.append({
                'keyword': keyword,
                'search_volume': kw.get('search_volume', 0),
                'priority_score': kw.get('priority_score', 0)
            })

    # Sort by priority
    backend_candidates.sort(key=lambda x: x['priority_score'], reverse=True)

    # Calculate byte usage (250 bytes max for backend)
    selected = []
    total_bytes = 0
    for kw in backend_candidates:
        kw_bytes = len(kw['keyword'].encode('utf-8')) + 1  # +1 for space
        if total_bytes + kw_bytes <= 249:
            selected.append(kw)
            total_bytes += kw_bytes

    return {
        'candidates': backend_candidates[:50],
        'selected_for_backend': selected,
        'total_bytes_used': total_bytes,
        'max_bytes': 250
    }


def generate_recommendations(title_analysis, bullet_analysis, image_analysis, aplus_analysis):
    """Generate prioritized action items."""
    recs = []

    # Title recommendations
    if title_analysis['score'] < 70:
        if title_analysis['keywords_missing']:
            recs.append({
                'area': 'Title',
                'priority': 'High',
                'action': f"Add missing keywords to title: {', '.join(title_analysis['keywords_missing'][:3])}",
                'expected_impact': 'Improved organic rank for high-volume keywords'
            })
        if title_analysis['our_length'] < 120:
            recs.append({
                'area': 'Title',
                'priority': 'High',
                'action': f"Expand title from {title_analysis['our_length']} to 150-200 chars",
                'expected_impact': 'More keyword coverage without stuffing'
            })

    # Bullet recommendations
    if bullet_analysis['score'] < 70:
        if bullet_analysis['our_bullet_count'] < 5:
            recs.append({
                'area': 'Bullet Points',
                'priority': 'High',
                'action': f"Add {5 - bullet_analysis['our_bullet_count']} more bullet points (currently {bullet_analysis['our_bullet_count']})",
                'expected_impact': 'More content for keyword indexing'
            })
        if bullet_analysis['keywords_missing']:
            recs.append({
                'area': 'Bullet Points',
                'priority': 'Medium',
                'action': f"Integrate missing keywords into bullets: {', '.join(bullet_analysis['keywords_missing'][:5])}",
                'expected_impact': 'Better keyword coverage'
            })

    # Image recommendations
    if image_analysis['score'] < 70:
        if image_analysis['our_image_count'] < 7:
            recs.append({
                'area': 'Images',
                'priority': 'Medium',
                'action': f"Add {7 - image_analysis['our_image_count']} more images (currently {image_analysis['our_image_count']})",
                'expected_impact': 'Higher conversion rate (industry avg +30% with 7+ images)'
            })

    # A+ recommendations
    if not aplus_analysis['our_has_aplus'] and aplus_analysis['competitor_aplus_ratio'] > 0.3:
        recs.append({
            'area': 'A+ Content',
            'priority': 'High',
            'action': f"Add A+ Content ({int(aplus_analysis['competitor_aplus_ratio']*100)}% of competitors have it)",
            'expected_impact': 'Higher conversion rate, brand story, additional indexable text'
        })

    return recs


def run_gap_analysis(our_listing_path, competitor_listings_path, keyword_analysis_path, output_path):
    """Main gap analysis pipeline."""

    with open(our_listing_path) as f:
        our_listing = json.load(f)

    with open(competitor_listings_path) as f:
        comp_data = json.load(f)
    competitor_listings = comp_data if isinstance(comp_data, list) else comp_data.get('listings', [])

    with open(keyword_analysis_path) as f:
        keyword_analysis = json.load(f)

    # Run each analysis dimension
    title = score_title(our_listing, competitor_listings, keyword_analysis)
    bullets = score_bullets(our_listing, competitor_listings, keyword_analysis)
    images = score_images(our_listing, competitor_listings)
    aplus = score_aplus(our_listing, competitor_listings)
    backend = identify_backend_keywords(keyword_analysis, our_listing)

    # Calculate overall score
    overall = round(
        title['score'] * 0.30 +
        bullets['score'] * 0.25 +
        images['score'] * 0.20 +
        aplus['score'] * 0.15 +
        min(100, len(backend['selected_for_backend']) * 5) * 0.10,
        1
    )

    # Generate recommendations
    recommendations = generate_recommendations(title, bullets, images, aplus)

    # Competitor averages summary
    comp_scores = []
    for c in competitor_listings:
        # Quick competitor score
        c_title_len = len(c.get('title', ''))
        c_bullets = len(c.get('bullets', []))
        c_images = c.get('imageCount', c.get('image_count', 0))
        c_aplus = 1 if c.get('hasAPlus', c.get('has_a_plus', False)) else 0
        comp_scores.append({
            'asin': c.get('asin', ''),
            'brand': c.get('brand', ''),
            'title_length': c_title_len,
            'bullet_count': c_bullets,
            'image_count': c_images,
            'has_aplus': bool(c_aplus)
        })

    result = {
        'our_asin': our_listing.get('asin', keyword_analysis.get('our_asin', '')),
        'overall_score': overall,
        'scores': {
            'title': title,
            'bullets': bullets,
            'images': images,
            'aplus': aplus
        },
        'backend_keywords': backend,
        'recommendations': recommendations,
        'competitor_summary': comp_scores
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nGap Analysis Complete:")
    print(f"  Overall Score: {overall}/100")
    print(f"  Title: {title['score']}/100")
    print(f"  Bullets: {bullets['score']}/100")
    print(f"  Images: {images['score']}/100")
    print(f"  A+ Content: {aplus['score']}/100")
    print(f"  Backend keywords selected: {len(backend['selected_for_backend'])} ({backend['total_bytes_used']}/250 bytes)")
    print(f"  Action items: {len(recommendations)}")
    print(f"\nSaved to: {output_path}")

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Listing gap analysis')
    parser.add_argument('--our-listing', required=True)
    parser.add_argument('--competitor-listings', required=True)
    parser.add_argument('--keyword-analysis', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    run_gap_analysis(args.our_listing, args.competitor_listings, args.keyword_analysis, args.output)
