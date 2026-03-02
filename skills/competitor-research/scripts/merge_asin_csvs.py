"""
Merge and deduplicate ASIN Grabber CSV exports.
Combines multiple keyword search exports into a single competitor list.
"""
import csv
import json
import os
import glob
import argparse
import math
from datetime import datetime

WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def find_asin_grabber_csvs(downloads_dir, date_filter=None):
    """Find all asinGrabber CSV files in downloads directory."""
    pattern = os.path.join(downloads_dir, "asinGrabber*.csv")
    files = glob.glob(pattern)
    if date_filter:
        files = [f for f in files if date_filter in f]
    return sorted(files, key=os.path.getmtime, reverse=True)


def parse_csv(filepath, keyword_source=None):
    """Parse a single ASIN Grabber CSV into product dicts."""
    products = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            asin = row.get('ASIN', '').strip()
            if not asin or len(asin) != 10:
                continue

            price_str = row.get('Price $', row.get('Price', '0'))
            price = _parse_price(price_str)
            bsr = _parse_int(row.get('BSR', '0'))
            rating = _parse_float(row.get('Ratings', '0'))
            reviews = _parse_int(row.get('Review Count', '0'))

            products.append({
                'asin': asin,
                'title': row.get('Product Details', '').strip(),
                'brand': row.get('Brand', '').strip(),
                'price': price,
                'bsr': bsr,
                'rating': rating,
                'review_count': reviews,
                'url': row.get('URL', '').strip(),
                'image_url': row.get('Image URL', '').strip(),
                'origin': row.get('Origin', '').strip(),
                'keyword_sources': [keyword_source] if keyword_source else [],
            })
    return products


def filter_products(products, filter_config):
    """Filter products based on title keywords and subcategory exclusions.

    filter_config = {
        'title_exclude_keywords': ['baby', 'pet', ...],
        'exclude_subcategories': ['Baby Wipes', 'Pet Wipes', ...],
    }
    Returns (kept, removed) tuple.
    """
    if not filter_config:
        return products, []

    exclude_kws = [kw.lower() for kw in filter_config.get('title_exclude_keywords', [])]
    exclude_subcats = [s.lower() for s in filter_config.get('exclude_subcategories', [])]

    kept = []
    removed = []
    for p in products:
        title_lower = p.get('title', '').lower()
        brand_lower = p.get('brand', '').lower()

        # Check title exclude keywords
        excluded = False
        for kw in exclude_kws:
            if kw in title_lower or kw in brand_lower:
                excluded = True
                p['_filter_reason'] = f'title_exclude: {kw}'
                break

        if excluded:
            removed.append(p)
        else:
            kept.append(p)

    return kept, removed


def merge_products(all_products, our_asins=None):
    """Merge products from multiple CSVs, deduplicate by ASIN."""
    if our_asins is None:
        our_asins = set()
    else:
        our_asins = set(our_asins)

    merged = {}
    for product in all_products:
        asin = product['asin']
        if asin in our_asins:
            continue

        if asin in merged:
            existing = merged[asin]
            for kw in product.get('keyword_sources', []):
                if kw and kw not in existing['keyword_sources']:
                    existing['keyword_sources'].append(kw)
            existing['keyword_frequency'] = len(existing['keyword_sources'])
            if product['bsr'] > 0 and (existing['bsr'] == 0 or product['bsr'] < existing['bsr']):
                existing['bsr'] = product['bsr']
            if product['price'] > 0 and existing['price'] == 0:
                existing['price'] = product['price']
            if product['review_count'] > existing['review_count']:
                existing['review_count'] = product['review_count']
                existing['rating'] = product['rating']
        else:
            product['keyword_frequency'] = len(product.get('keyword_sources', []))
            merged[asin] = product

    return list(merged.values())


def calculate_relevance(products, boost_config=None):
    """Calculate relevance score for each product.

    boost_config = {
        'title_boost_keywords': ['tea tree', 'body', ...],
        'title_boost_weight': 20  # max points from title matching
    }

    Scoring formula (total up to 120 with boost):
      - freq_score:  0-40  (keyword frequency across searches)
      - bsr_score:   0-25  (log-scale BSR, lower = better)
      - review_score: 0-20  (log-scale review count)
      - rating_score: 0-15  (star rating)
      - title_boost:  0-N   (title keyword matching, default max 20)
    """
    if not products:
        return products

    max_freq = max(p['keyword_frequency'] for p in products) or 1
    max_reviews = max(p['review_count'] for p in products) or 1
    bsr_values = [p['bsr'] for p in products if p['bsr'] > 0]
    min_bsr = min(bsr_values) if bsr_values else 1
    max_bsr = max(bsr_values) if bsr_values else 1

    # Title boost setup
    boost_keywords = []
    boost_weight = 0
    if boost_config:
        boost_keywords = [kw.lower() for kw in boost_config.get('title_boost_keywords', [])]
        boost_weight = boost_config.get('title_boost_weight', 20)

    for p in products:
        freq_score = (p['keyword_frequency'] / max_freq) * 40
        if p['bsr'] > 0 and max_bsr > min_bsr:
            bsr_normalized = 1 - (math.log(p['bsr']) - math.log(min_bsr)) / (math.log(max_bsr) - math.log(min_bsr))
            bsr_score = max(0, bsr_normalized) * 25
        else:
            bsr_score = 0
        review_score = min(1, math.log(p['review_count'] + 1) / math.log(max_reviews + 1)) * 20
        rating_score = (p['rating'] / 5.0) * 15 if p['rating'] > 0 else 0

        # Title keyword boost
        title_boost = 0
        if boost_keywords and boost_weight > 0:
            title_lower = p.get('title', '').lower()
            matches = sum(1 for kw in boost_keywords if kw in title_lower)
            match_ratio = min(1.0, matches / max(len(boost_keywords) * 0.3, 1))
            title_boost = match_ratio * boost_weight
            p['title_match_count'] = matches

        p['relevance_score'] = round(freq_score + bsr_score + review_score + rating_score + title_boost, 1)

    products.sort(key=lambda x: x['relevance_score'], reverse=True)
    return products


def _parse_price(s):
    if not s:
        return 0.0
    s = str(s).replace('$', '').replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def _parse_int(s):
    if not s:
        return 0
    s = str(s).replace(',', '').replace('#', '').strip()
    try:
        return int(float(s))
    except ValueError:
        return 0


def _parse_float(s):
    if not s:
        return 0.0
    s = str(s).replace(',', '').strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def run_merge(downloads_dir, our_asins_str, output_path, keyword_labels=None):
    """Main merge function."""
    our_asins = [a.strip() for a in our_asins_str.split(',') if a.strip()] if our_asins_str else []

    csv_files = find_asin_grabber_csvs(downloads_dir)
    if not csv_files:
        print(f"No asinGrabber CSV files found in {downloads_dir}")
        return None

    print(f"Found {len(csv_files)} ASIN Grabber CSV files")

    all_products = []
    for i, csv_file in enumerate(csv_files):
        keyword = keyword_labels[i] if keyword_labels and i < len(keyword_labels) else f"search_{i+1}"
        products = parse_csv(csv_file, keyword_source=keyword)
        print(f"  {os.path.basename(csv_file)}: {len(products)} products (keyword: {keyword})")
        all_products.extend(products)

    merged = merge_products(all_products, our_asins)
    merged = calculate_relevance(merged)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    result = {
        'generated_date': datetime.now().strftime('%Y-%m-%d'),
        'generated_time': datetime.now().strftime('%H:%M:%S'),
        'csv_files_merged': len(csv_files),
        'total_raw_products': len(all_products),
        'unique_competitors': len(merged),
        'our_asins_excluded': our_asins,
        'competitors': merged
    }

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\nMerged: {len(all_products)} raw → {len(merged)} unique competitors")
    print(f"Saved to: {output_path}")
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge ASIN Grabber CSV exports')
    parser.add_argument('--downloads-dir', required=True)
    parser.add_argument('--our-asins', default='')
    parser.add_argument('--output', required=True)
    parser.add_argument('--keywords', nargs='*', help='Keyword labels for each CSV')
    args = parser.parse_args()

    downloads = os.path.join(WORKSPACE, args.downloads_dir) if not os.path.isabs(args.downloads_dir) else args.downloads_dir
    output = os.path.join(WORKSPACE, args.output) if not os.path.isabs(args.output) else args.output

    run_merge(downloads, args.our_asins, output, args.keywords)
