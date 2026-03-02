#!/usr/bin/env python3
"""
Step 1: Parse & Clean H10 Review Export CSVs
Normalizes columns, deduplicates, validates, and outputs unified JSON.
"""

import os
import json
import csv
import re
import hashlib
from datetime import datetime
from pathlib import Path


# ─── Column Mapping ──────────────────────────────────────────────────────────
# H10 Review Insights exports may have varying column names; map them

COLUMN_MAP = {
    # ASIN
    'asin': 'asin', 'product asin': 'asin', 'parent asin': 'asin',
    # Rating
    'rating': 'rating', 'star rating': 'rating', 'stars': 'rating', 'overall': 'rating',
    # Title
    'review title': 'title', 'title': 'title', 'headline': 'title', 'summary': 'title',
    # Body
    'review text': 'body', 'review body': 'body', 'review': 'body',
    'body': 'body', 'text': 'body', 'comment': 'body',
    # Date
    'date': 'date', 'review date': 'date', 'reviewed on': 'date',
    # Verified
    'verified purchase': 'verified', 'verified': 'verified',
    # Helpful
    'helpful votes': 'helpful_votes', 'helpful': 'helpful_votes',
    'found helpful': 'helpful_votes',
    # Reviewer
    'reviewer': 'reviewer', 'author': 'reviewer', 'name': 'reviewer',
    # Product
    'product name': 'product_name', 'product title': 'product_name',
}


def detect_columns(headers):
    """Map CSV headers to normalized field names."""
    mapping = {}
    for i, h in enumerate(headers):
        normalized = h.strip().lower()
        if normalized in COLUMN_MAP:
            mapping[COLUMN_MAP[normalized]] = i
    return mapping


def parse_date(date_str):
    """Try multiple date formats."""
    if not date_str:
        return None
    date_str = date_str.strip()

    formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y',
        '%B %d, %Y', '%b %d, %Y',
        '%d %B %Y', '%d %b %Y',
        '%Y-%m-%dT%H:%M:%S',
    ]
    # Strip "Reviewed in the United States on " prefix
    date_str = re.sub(r'^Reviewed in .+ on ', '', date_str)

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return date_str  # Return as-is if no format matches


def parse_rating(val):
    """Extract numeric rating from various formats."""
    if not val:
        return None
    val = str(val).strip()
    # "5.0 out of 5 stars" or "4.0" or "4"
    match = re.search(r'(\d+\.?\d*)', val)
    if match:
        return float(match.group(1))
    return None


def parse_verified(val):
    """Parse verified purchase field."""
    if not val:
        return False
    val = str(val).strip().lower()
    return val in ('true', 'yes', '1', 'verified purchase', 'verified')


def review_hash(asin, title, body):
    """Generate unique hash for deduplication."""
    text = f"{asin}|{(title or '').strip()[:100]}|{(body or '').strip()[:200]}"
    return hashlib.md5(text.encode()).hexdigest()


def parse_csv_file(filepath):
    """Parse a single H10 review CSV file."""
    reviews = []
    filepath = Path(filepath)

    if not filepath.exists():
        print(f"  ⚠️  File not found: {filepath}")
        return reviews

    print(f"  Parsing: {filepath.name}")

    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        # Try to detect delimiter
        sample = f.read(4096)
        f.seek(0)

        dialect = csv.Sniffer().sniff(sample, delimiters=',\t|')
        reader = csv.reader(f, dialect)

        headers = next(reader)
        col_map = detect_columns(headers)

        if not col_map:
            print(f"    ⚠️  Could not detect columns, skipping")
            return reviews

        found_cols = list(col_map.keys())
        print(f"    Detected columns: {', '.join(found_cols)}")

        for row_num, row in enumerate(reader, start=2):
            try:
                review = {
                    'asin': row[col_map['asin']].strip() if 'asin' in col_map and col_map['asin'] < len(row) else '',
                    'rating': parse_rating(row[col_map['rating']] if 'rating' in col_map and col_map['rating'] < len(row) else ''),
                    'title': row[col_map['title']].strip() if 'title' in col_map and col_map['title'] < len(row) else '',
                    'body': row[col_map['body']].strip() if 'body' in col_map and col_map['body'] < len(row) else '',
                    'date': parse_date(row[col_map['date']] if 'date' in col_map and col_map['date'] < len(row) else ''),
                    'verified': parse_verified(row[col_map['verified']] if 'verified' in col_map and col_map['verified'] < len(row) else ''),
                    'helpful_votes': int(row[col_map['helpful_votes']]) if 'helpful_votes' in col_map and col_map['helpful_votes'] < len(row) and row[col_map['helpful_votes']].strip().isdigit() else 0,
                    'reviewer': row[col_map['reviewer']].strip() if 'reviewer' in col_map and col_map['reviewer'] < len(row) else '',
                    'product_name': row[col_map['product_name']].strip() if 'product_name' in col_map and col_map['product_name'] < len(row) else '',
                    'source_file': filepath.name,
                }

                # Skip rows with no meaningful content
                if not review['body'] and not review['title']:
                    continue

                review['hash'] = review_hash(review['asin'], review['title'], review['body'])
                reviews.append(review)

            except (IndexError, ValueError) as e:
                continue  # Skip malformed rows

    print(f"    Parsed {len(reviews)} reviews")
    return reviews


def parse_all_csvs(input_paths, output_dir):
    """Parse multiple CSV files, deduplicate, and save unified JSON."""
    all_reviews = []
    seen_hashes = set()

    for path in input_paths:
        reviews = parse_csv_file(path)
        for r in reviews:
            if r['hash'] not in seen_hashes:
                seen_hashes.add(r['hash'])
                all_reviews.append(r)

    # Sort by date descending
    all_reviews.sort(key=lambda x: x.get('date', '') or '', reverse=True)

    # Stats
    asins = set(r['asin'] for r in all_reviews if r['asin'])
    ratings = [r['rating'] for r in all_reviews if r['rating'] is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    rating_dist = {}
    for r in ratings:
        star = int(r)
        rating_dist[star] = rating_dist.get(star, 0) + 1

    result = {
        'total_reviews': len(all_reviews),
        'unique_asins': len(asins),
        'asins': sorted(asins),
        'avg_rating': round(avg_rating, 2),
        'rating_distribution': rating_dist,
        'verified_count': sum(1 for r in all_reviews if r['verified']),
        'date_range': {
            'earliest': min((r['date'] for r in all_reviews if r.get('date')), default=None),
            'latest': max((r['date'] for r in all_reviews if r.get('date')), default=None),
        },
        'reviews': all_reviews,
        'parsed_at': datetime.now().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'parsed_reviews.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Review Parse Complete:")
    print(f"  Total reviews: {result['total_reviews']}")
    print(f"  Unique ASINs: {result['unique_asins']}")
    print(f"  Avg rating: {result['avg_rating']}")
    print(f"  Rating dist: {rating_dist}")
    print(f"  Date range: {result['date_range']['earliest']} to {result['date_range']['latest']}")
    print(f"  Saved to: {output_path}")

    return result


if __name__ == '__main__':
    import argparse
    import glob

    parser = argparse.ArgumentParser(description='Parse H10 Review CSVs')
    parser.add_argument('--input', type=str, nargs='+', required=True,
                       help='CSV file paths (supports glob patterns)')
    parser.add_argument('--output', type=str, required=True,
                       help='Output directory')
    args = parser.parse_args()

    # Expand glob patterns
    input_files = []
    for pattern in args.input:
        matches = glob.glob(pattern)
        if matches:
            input_files.extend(matches)
        else:
            input_files.append(pattern)

    parse_all_csvs(input_files, args.output)
