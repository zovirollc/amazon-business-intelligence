#!/usr/bin/env python3
"""
Step 2: Sentiment & Theme Analysis
Analyzes parsed reviews for sentiment, themes, pain points, and feature demands.
Uses keyword-based NLP (no external ML dependencies).
"""

import os
import json
import re
from collections import Counter, defaultdict
from datetime import datetime


# ─── Sentiment Lexicon ────────────────────────────────────────────────────────
# Tailored for consumer product reviews

POSITIVE_WORDS = {
    'love', 'great', 'excellent', 'perfect', 'amazing', 'wonderful', 'fantastic',
    'awesome', 'best', 'good', 'nice', 'clean', 'fresh', 'soft', 'gentle',
    'moisturizing', 'effective', 'convenient', 'portable', 'recommend',
    'favorite', 'pleased', 'satisfied', 'impressed', 'quality', 'value',
    'works', 'helpful', 'refreshing', 'soothing', 'pleasant', 'sturdy',
    'thick', 'large', 'durable', 'reliable', 'fast', 'easy', 'comfortable',
    'smooth', 'natural', 'organic', 'safe', 'strong', 'powerful', 'versatile',
    'affordable', 'bargain', 'worth', 'repurchase', 'reorder', 'lifesaver',
}

NEGATIVE_WORDS = {
    'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'poor', 'cheap',
    'flimsy', 'thin', 'small', 'tiny', 'dry', 'dried', 'dries', 'harsh',
    'irritating', 'burning', 'rash', 'allergy', 'allergic', 'sticky', 'slimy',
    'chemical', 'stink', 'stinks', 'smell', 'smells', 'odor', 'gross',
    'disappointing', 'disappointed', 'waste', 'useless', 'broke', 'broken',
    'leak', 'leaked', 'leaking', 'ripped', 'torn', 'falling', 'apart',
    'expensive', 'overpriced', 'scam', 'fake', 'return', 'returned', 'refund',
    'defective', 'damaged', 'missing', 'wrong', 'misleading', 'false',
}

INTENSIFIERS = {'very', 'really', 'extremely', 'super', 'incredibly', 'absolutely', 'totally', 'highly'}
NEGATORS = {'not', "n't", 'no', 'never', 'hardly', 'barely', 'neither', "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "couldn't"}


# ─── Theme Definitions ────────────────────────────────────────────────────────
# Each theme has associated keywords for detection

THEMES = {
    'product_quality': {
        'keywords': ['quality', 'effective', 'works', 'clean', 'kills', 'sanitize', 'sanitizing',
                     'antibacterial', 'germ', 'germs', 'bacteria', 'disinfect', 'alcohol'],
        'label': 'Product Quality & Effectiveness',
    },
    'texture_feel': {
        'keywords': ['soft', 'thick', 'thin', 'wet', 'dry', 'moist', 'moisturizing', 'texture',
                     'gentle', 'rough', 'smooth', 'soaked', 'saturated', 'damp'],
        'label': 'Texture & Feel',
    },
    'scent': {
        'keywords': ['smell', 'scent', 'fragrance', 'odor', 'aroma', 'tea tree', 'lavender',
                     'lemon', 'citrus', 'unscented', 'perfume', 'chemical smell', 'fresh'],
        'label': 'Scent & Fragrance',
    },
    'packaging': {
        'keywords': ['package', 'packaging', 'individually', 'wrapped', 'sealed', 'resealable',
                     'lid', 'cap', 'dispenser', 'container', 'pouch', 'canister', 'bag', 'box',
                     'dried out', 'dries out'],
        'label': 'Packaging & Dispensing',
    },
    'size_quantity': {
        'keywords': ['size', 'large', 'small', 'big', 'count', 'quantity', 'pack', 'bulk',
                     'enough', 'generous', 'tiny', 'pieces', 'sheets'],
        'label': 'Size & Quantity',
    },
    'value_price': {
        'keywords': ['price', 'value', 'expensive', 'cheap', 'affordable', 'worth', 'deal',
                     'bargain', 'cost', 'money', 'overpriced', 'budget'],
        'label': 'Value & Price',
    },
    'portability': {
        'keywords': ['travel', 'portable', 'carry', 'purse', 'bag', 'pocket', 'on-the-go',
                     'gym', 'car', 'airplane', 'flight', 'outdoor', 'camping', 'hiking'],
        'label': 'Portability & Travel Use',
    },
    'skin_sensitivity': {
        'keywords': ['sensitive', 'skin', 'irritation', 'irritate', 'rash', 'allergy', 'allergic',
                     'reaction', 'burn', 'burning', 'sting', 'eczema', 'dermatitis', 'hypoallergenic',
                     'safe for', 'kids', 'children', 'baby'],
        'label': 'Skin Sensitivity & Safety',
    },
    'use_case': {
        'keywords': ['office', 'work', 'school', 'hospital', 'medical', 'restaurant', 'food',
                     'grocery', 'shopping', 'cart', 'door', 'handle', 'surface', 'hands',
                     'face', 'body', 'phone', 'desk', 'keyboard'],
        'label': 'Use Cases & Applications',
    },
    'comparison': {
        'keywords': ['better than', 'worse than', 'compared to', 'like', 'similar', 'prefer',
                     'switch', 'switched', 'replacement', 'alternative', 'vs', 'instead of',
                     'purell', 'wet ones', 'clorox', 'lysol', 'germ-x'],
        'label': 'Brand Comparisons',
    },
}


def tokenize(text):
    """Simple word tokenization."""
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def calculate_sentiment(text):
    """Calculate sentiment score for a text (-1 to +1)."""
    if not text:
        return 0

    words = tokenize(text)
    pos_count = 0
    neg_count = 0
    total_words = len(words)

    if total_words == 0:
        return 0

    negate = False
    intensify = False

    for i, word in enumerate(words):
        if word in NEGATORS or word.endswith("n't"):
            negate = True
            continue

        if word in INTENSIFIERS:
            intensify = True
            continue

        multiplier = 1.5 if intensify else 1.0

        if word in POSITIVE_WORDS:
            if negate:
                neg_count += multiplier
            else:
                pos_count += multiplier
        elif word in NEGATIVE_WORDS:
            if negate:
                pos_count += multiplier
            else:
                neg_count += multiplier

        negate = False
        intensify = False

    # Normalize to -1 to +1
    total_sentiment = pos_count + neg_count
    if total_sentiment == 0:
        return 0

    score = (pos_count - neg_count) / total_sentiment
    return round(score, 3)


def detect_themes(text):
    """Detect which themes a review mentions."""
    if not text:
        return []

    text_lower = text.lower()
    detected = []

    for theme_id, theme_def in THEMES.items():
        for keyword in theme_def['keywords']:
            if keyword in text_lower:
                detected.append(theme_id)
                break  # One match per theme is enough

    return detected


def extract_pain_points(reviews):
    """Extract common pain points from negative reviews (1-2 stars)."""
    negative_reviews = [r for r in reviews if r.get('rating', 5) <= 2]
    if not negative_reviews:
        return []

    # Collect common bigrams and trigrams from negative reviews
    phrase_counts = Counter()
    for r in negative_reviews:
        text = f"{r.get('title', '')} {r.get('body', '')}".lower()
        words = tokenize(text)

        # Bigrams
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i+1]}"
            if not all(w in {'the', 'a', 'an', 'is', 'it', 'of', 'to', 'in', 'and', 'for', 'was', 'that', 'this', 'with', 'are', 'but', 'they', 'i', 'my', 'on'} for w in [words[i], words[i+1]]):
                phrase_counts[phrase] += 1

        # Trigrams
        for i in range(len(words) - 2):
            phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
            phrase_counts[phrase] += 1

    # Filter to meaningful phrases mentioned 3+ times
    pain_points = []
    for phrase, count in phrase_counts.most_common(50):
        if count >= 2 and len(phrase) > 5:
            # Check if phrase has at least one non-stopword
            words = phrase.split()
            stopwords = {'the', 'a', 'an', 'is', 'it', 'of', 'to', 'in', 'and', 'for', 'was', 'that', 'this', 'with', 'are', 'but', 'they', 'i', 'my', 'on', 'not', 'have', 'had', 'has', 'be', 'been'}
            if any(w not in stopwords for w in words):
                pain_points.append({'phrase': phrase, 'mentions': count})

        if len(pain_points) >= 20:
            break

    return pain_points


def extract_feature_demands(reviews):
    """Extract feature requests and wishes from reviews."""
    demand_patterns = [
        r'wish (?:it |they |this )?(?:had|was|were|came|would|could)',
        r'would (?:be |have been )?(?:nice|great|better|good) if',
        r'(?:should|could|needs to) (?:be|have|come|include)',
        r'(?:only|main) (?:complaint|issue|problem|concern|downside|drawback)',
        r'(?:too|very) (?:small|thin|dry|wet|expensive|cheap|strong|weak)',
        r"(?:don't|doesn't|didn't) (?:like|work|stay|last|clean)",
        r'(?:not enough|more|bigger|larger|thicker|wetter)',
    ]

    demands = []
    for r in reviews:
        text = f"{r.get('title', '')} {r.get('body', '')}"
        for pattern in demand_patterns:
            matches = re.findall(f'(.{{0,40}}{pattern}.{{0,60}})', text, re.IGNORECASE)
            for match in matches:
                demands.append({
                    'context': match.strip(),
                    'rating': r.get('rating'),
                    'asin': r.get('asin', ''),
                })

    # Deduplicate similar demands
    seen = set()
    unique_demands = []
    for d in demands:
        key = d['context'][:50].lower()
        if key not in seen:
            seen.add(key)
            unique_demands.append(d)

    return unique_demands[:30]  # Top 30


def analyze_reviews(input_path, output_dir):
    """Run full analysis on parsed reviews."""
    print("Loading parsed reviews...")
    with open(input_path) as f:
        data = json.load(f)

    reviews = data['reviews']
    print(f"Analyzing {len(reviews)} reviews...")

    # 1. Sentiment scoring
    print("\n--- Sentiment Analysis ---")
    for r in reviews:
        text = f"{r.get('title', '')} {r.get('body', '')}"
        r['sentiment'] = calculate_sentiment(text)
        r['themes'] = detect_themes(text)

    sentiments = [r['sentiment'] for r in reviews]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

    sentiment_buckets = {
        'very_positive': sum(1 for s in sentiments if s > 0.5),
        'positive': sum(1 for s in sentiments if 0.1 < s <= 0.5),
        'neutral': sum(1 for s in sentiments if -0.1 <= s <= 0.1),
        'negative': sum(1 for s in sentiments if -0.5 <= s < -0.1),
        'very_negative': sum(1 for s in sentiments if s < -0.5),
    }
    print(f"  Avg sentiment: {avg_sentiment:.3f}")
    print(f"  Distribution: {sentiment_buckets}")

    # 2. Theme analysis
    print("\n--- Theme Analysis ---")
    theme_counts = Counter()
    theme_sentiment = defaultdict(list)
    theme_by_asin = defaultdict(lambda: Counter())

    for r in reviews:
        for theme in r['themes']:
            theme_counts[theme] += 1
            theme_sentiment[theme].append(r['sentiment'])
            if r.get('asin'):
                theme_by_asin[r['asin']][theme] += 1

    theme_analysis = {}
    for theme_id, count in theme_counts.most_common():
        sents = theme_sentiment[theme_id]
        theme_analysis[theme_id] = {
            'label': THEMES[theme_id]['label'],
            'mention_count': count,
            'mention_pct': round(count / len(reviews) * 100, 1),
            'avg_sentiment': round(sum(sents) / len(sents), 3) if sents else 0,
            'positive_pct': round(sum(1 for s in sents if s > 0.1) / len(sents) * 100, 1) if sents else 0,
            'negative_pct': round(sum(1 for s in sents if s < -0.1) / len(sents) * 100, 1) if sents else 0,
        }
        print(f"  {THEMES[theme_id]['label']}: {count} mentions ({theme_analysis[theme_id]['mention_pct']}%), "
              f"sentiment: {theme_analysis[theme_id]['avg_sentiment']}")

    # 3. Pain points
    print("\n--- Pain Points ---")
    pain_points = extract_pain_points(reviews)
    for pp in pain_points[:10]:
        print(f"  \"{pp['phrase']}\" ({pp['mentions']} mentions)")

    # 4. Feature demands
    print("\n--- Feature Demands ---")
    feature_demands = extract_feature_demands(reviews)
    for fd in feature_demands[:10]:
        print(f"  [{fd['rating']}★] \"{fd['context'][:80]}...\"")

    # 5. Per-ASIN breakdown
    print("\n--- Per-ASIN Breakdown ---")
    asin_stats = {}
    asin_reviews = defaultdict(list)
    for r in reviews:
        if r.get('asin'):
            asin_reviews[r['asin']].append(r)

    for asin, revs in asin_reviews.items():
        ratings = [r['rating'] for r in revs if r.get('rating')]
        sents = [r['sentiment'] for r in revs]
        asin_stats[asin] = {
            'review_count': len(revs),
            'avg_rating': round(sum(ratings) / len(ratings), 2) if ratings else 0,
            'avg_sentiment': round(sum(sents) / len(sents), 3) if sents else 0,
            'rating_distribution': dict(Counter(int(r) for r in ratings)),
            'top_themes': dict(theme_by_asin[asin].most_common(5)),
            'product_name': next((r.get('product_name', '') for r in revs if r.get('product_name')), ''),
        }
        print(f"  {asin}: {len(revs)} reviews, {asin_stats[asin]['avg_rating']}★, "
              f"sentiment: {asin_stats[asin]['avg_sentiment']}")

    # Build result
    result = {
        'total_reviews': len(reviews),
        'avg_sentiment': round(avg_sentiment, 3),
        'sentiment_distribution': sentiment_buckets,
        'avg_rating': data.get('avg_rating', 0),
        'rating_distribution': data.get('rating_distribution', {}),
        'theme_analysis': theme_analysis,
        'pain_points': pain_points,
        'feature_demands': feature_demands,
        'asin_stats': asin_stats,
        'reviews': reviews,  # Include enriched reviews
        'analyzed_at': datetime.now().isoformat(),
    }

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'review_analysis.json')
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Analysis complete → {output_path}")

    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Analyze Reviews')
    parser.add_argument('--input', type=str, required=True, help='parsed_reviews.json path')
    parser.add_argument('--output', type=str, required=True, help='Output directory')
    args = parser.parse_args()

    analyze_reviews(args.input, args.output)
