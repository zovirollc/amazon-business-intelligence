#!/usr/bin/env python3
"""
Listing Copy Generator for Listing Optimization
Generates optimized title, bullets, backend keywords based on gap analysis.

NOTE: This script generates structured data and templates.
The actual copy writing should be done by Claude using the analysis data,
as AI-generated marketing copy requires contextual judgment.
"""

import json
import argparse
import os


def generate_title_templates(gap_analysis, keyword_analysis, our_listing, config):
    """Generate title optimization templates with keyword placement guides."""
    title_data = gap_analysis['scores']['title']
    title_kws = keyword_analysis.get('top_title_keywords', [])

    brand = our_listing.get('brand', config.get('brand', 'Zoviro'))
    current_title = title_data.get('our_title', '')

    # Extract product attributes from current title
    templates = {
        'current': {
            'title': current_title,
            'char_count': len(current_title),
            'keywords_included': title_data.get('keywords_covered', []),
            'keywords_missing': title_data.get('keywords_missing', [])
        },
        'guidelines': {
            'max_chars': 200,
            'optimal_range': '150-200 chars',
            'mobile_cutoff': '80 chars (first 80 chars show on mobile)',
            'format': 'Brand + Key Benefit + Product Type + [Size/Count] + [Key Feature]',
            'rules': [
                'Front-load top 2-3 keywords in first 80 characters',
                'Include size/count for clear product identification',
                'Avoid ALL CAPS except brand name abbreviations',
                'Use pipes (|) or dashes (-) as separators, not commas',
                'Include the product type explicitly (e.g., "Hand Sanitizer Wipes")'
            ],
            'must_include_keywords': title_kws[:5],
            'should_include_keywords': title_kws[5:8],
            'nice_to_have_keywords': title_kws[8:]
        },
        'competitor_patterns': []
    }

    return templates


def generate_bullet_templates(gap_analysis, keyword_analysis, our_listing):
    """Generate bullet point optimization templates."""
    bullet_data = gap_analysis['scores']['bullets']
    bullet_kws = keyword_analysis.get('top_bullet_keywords', [])

    current_bullets = our_listing.get('bullets', [])

    # Distribute keywords across 5 bullets
    kw_per_bullet = max(3, len(bullet_kws) // 5)
    bullet_keyword_assignments = []
    for i in range(5):
        start = i * kw_per_bullet
        end = start + kw_per_bullet
        assigned = bullet_kws[start:end] if start < len(bullet_kws) else []
        bullet_keyword_assignments.append(assigned)

    templates = {
        'current_bullets': current_bullets,
        'current_count': len(current_bullets),
        'guidelines': {
            'total_bullets': 5,
            'optimal_length': '200-250 chars per bullet',
            'format': 'BENEFIT HEADLINE — Supporting detail with keyword integration',
            'bullet_themes': [
                {'position': 1, 'theme': 'Main Benefit / Primary Use Case', 'keywords': bullet_keyword_assignments[0]},
                {'position': 2, 'theme': 'Key Ingredient / Technology', 'keywords': bullet_keyword_assignments[1]},
                {'position': 3, 'theme': 'How To Use / Versatility', 'keywords': bullet_keyword_assignments[2]},
                {'position': 4, 'theme': 'Quality / Safety / Certifications', 'keywords': bullet_keyword_assignments[3]},
                {'position': 5, 'theme': 'Value / Guarantee / What\'s Included', 'keywords': bullet_keyword_assignments[4]},
            ],
            'rules': [
                'Lead each bullet with a benefit, not a feature',
                'Capitalize the first phrase/benefit as a scannable headline',
                'Include 3-4 keywords naturally per bullet',
                'Avoid repeating keywords already in the title',
                'Use numbers and specifics (e.g., "kills 99.9%", "200 wipes")',
                'Address common customer questions/concerns'
            ]
        },
        'keywords_covered': bullet_data.get('keywords_covered', []),
        'keywords_missing': bullet_data.get('keywords_missing', [])
    }

    return templates


def generate_backend_keywords(gap_analysis):
    """Generate backend search term recommendations."""
    backend = gap_analysis.get('backend_keywords', {})

    return {
        'selected_keywords': backend.get('selected_for_backend', []),
        'bytes_used': backend.get('total_bytes_used', 0),
        'max_bytes': 250,
        'guidelines': {
            'format': 'Space-separated, no punctuation, no repeated words from title/bullets',
            'include': [
                'Synonyms and alternate spellings',
                'Common misspellings of product type',
                'Spanish translations of key terms',
                'Abbreviations (e.g., "antibac" for "antibacterial")',
                'Related use cases not mentioned in bullets'
            ],
            'exclude': [
                'Words already in title or bullets (Amazon ignores duplicates)',
                'Brand names (yours or competitors)',
                'Subjective claims (best, amazing, top-rated)',
                'ASINs or SKU numbers'
            ]
        },
        'suggested_additions': {
            'spanish_terms': [],  # To be filled based on product category
            'misspellings': [],
            'abbreviations': []
        }
    }


def generate_aplus_recommendations(gap_analysis, our_listing):
    """Generate A+ content module recommendations."""
    aplus_data = gap_analysis['scores']['aplus']

    if aplus_data['our_has_aplus']:
        return {
            'status': 'A+ content exists — manual review recommended',
            'competitor_adoption': f"{int(aplus_data['competitor_aplus_ratio'] * 100)}% of competitors have A+",
            'recommendations': [
                'Review for keyword integration in A+ text blocks',
                'Ensure comparison table includes top 3 selling points',
                'Add brand story module if not present',
                'Include cross-sell modules for other Zoviro products'
            ]
        }
    else:
        return {
            'status': 'No A+ content — HIGH PRIORITY to add',
            'competitor_adoption': f"{int(aplus_data['competitor_aplus_ratio'] * 100)}% of competitors have A+",
            'suggested_modules': [
                {'module': 'Brand Story', 'purpose': 'Build trust with Zoviro brand narrative'},
                {'module': 'Comparison Table', 'purpose': 'Us vs category average — highlight advantages'},
                {'module': 'Image + Text (x3)', 'purpose': 'Feature deep-dives with lifestyle images'},
                {'module': 'Product Gallery', 'purpose': 'Additional product images and use cases'},
            ],
            'text_guidelines': 'A+ text is indexable for SEO — include keywords naturally'
        }


def run_copy_generation(gap_analysis_path, keyword_analysis_path, our_listing_path, config_path, output_path):
    """Main copy generation pipeline."""

    with open(gap_analysis_path) as f:
        gap_analysis = json.load(f)

    with open(keyword_analysis_path) as f:
        keyword_analysis = json.load(f)

    with open(our_listing_path) as f:
        our_listing = json.load(f)

    with open(config_path) as f:
        config = json.load(f)

    # Generate templates for each section
    title_templates = generate_title_templates(gap_analysis, keyword_analysis, our_listing, config)
    bullet_templates = generate_bullet_templates(gap_analysis, keyword_analysis, our_listing)
    backend = generate_backend_keywords(gap_analysis)
    aplus = generate_aplus_recommendations(gap_analysis, our_listing)

    result = {
        'our_asin': gap_analysis.get('our_asin', ''),
        'overall_score': gap_analysis.get('overall_score', 0),
        'title': title_templates,
        'bullet_points': bullet_templates,
        'backend_search_terms': backend,
        'aplus_content': aplus,
        'recommendations': gap_analysis.get('recommendations', []),
        'note': 'This file contains structured analysis and templates. Use Claude to generate the actual optimized copy based on these guidelines and keyword priorities.'
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nCopy Generation Templates Complete:")
    print(f"  Title keywords to include: {len(title_templates['guidelines']['must_include_keywords'])}")
    print(f"  Bullet keywords to distribute: {len(keyword_analysis.get('top_bullet_keywords', []))}")
    print(f"  Backend keywords: {backend['bytes_used']}/250 bytes")
    print(f"  A+ status: {aplus['status']}")
    print(f"\nSaved to: {output_path}")

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate optimized listing copy templates')
    parser.add_argument('--gap-analysis', required=True)
    parser.add_argument('--keyword-analysis', required=True)
    parser.add_argument('--our-listing', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    run_copy_generation(args.gap_analysis, args.keyword_analysis, args.our_listing, args.config, args.output)
