"""
Score and select top competitors from merged data.
Enriches with detailed H10 X-Ray data when available.
"""
import json
import os
import argparse
from datetime import datetime

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def load_merged(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)


def select_top_competitors(merged_data, top_n=20):
    """Select top N competitors by relevance score."""
    competitors = merged_data.get('competitors', [])
    competitors.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    return competitors[:top_n]


def enrich_competitor(competitor, detail_data):
    """Enrich a competitor record with H10 X-Ray detail data."""
    competitor['revenue_30d'] = detail_data.get('revenue_30d')
    competitor['units_30d'] = detail_data.get('units_30d')
    competitor['listing_health_score'] = detail_data.get('listing_health_score')
    competitor['bsr_subcategory'] = detail_data.get('bsr_subcategory')
    competitor['bsr_subcategory_name'] = detail_data.get('bsr_subcategory_name')
    competitor['seller_count'] = detail_data.get('seller_count')
    competitor['fulfillment'] = detail_data.get('fulfillment')
    competitor['image_count'] = detail_data.get('image_count')
    competitor['has_aplus'] = detail_data.get('has_aplus')
    competitor['has_video'] = detail_data.get('has_video')
    competitor['top_keywords'] = detail_data.get('top_keywords', [])
    competitor['price_per_unit'] = detail_data.get('price_per_unit')
    competitor['monthly_bought'] = detail_data.get('monthly_bought')
    competitor['detail_collected'] = True
    return competitor


def save_top_competitors(top_competitors, merged_data, output_path):
    """Save top competitors with metadata."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    result = {
        'generated_date': datetime.now().strftime('%Y-%m-%d'),
        'generated_time': datetime.now().strftime('%H:%M:%S'),
        'source_merged': merged_data.get('generated_date'),
        'total_in_merged': merged_data.get('unique_competitors', 0),
        'top_n_selected': len(top_competitors),
        'competitors': top_competitors
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Selected top {len(top_competitors)} competitors")
    print(f"Saved to: {output_path}")

    for i, c in enumerate(top_competitors[:5]):
        print(f"  #{i+1}: {c['brand']} - {c['title'][:50]}... (score: {c.get('relevance_score', 0)})")

    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Score and select top competitors')
    parser.add_argument('--input', required=True)
    parser.add_argument('--top-n', type=int, default=20)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    input_path = os.path.join(WORKSPACE, args.input) if not os.path.isabs(args.input) else args.input
    output_path = os.path.join(WORKSPACE, args.output) if not os.path.isabs(args.output) else args.output

    merged = load_merged(input_path)
    top = select_top_competitors(merged, args.top_n)
    save_top_competitors(top, merged, output_path)
