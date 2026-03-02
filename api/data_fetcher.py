#!/usr/bin/env python3
"""
Unified Data Fetcher
High-level data fetching layer that abstracts SP API + Ads API into
skill-friendly data structures. Each method returns clean JSON ready
for consumption by listing-optimization and ppc-optimization skills.
"""

import os
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path

from .sp_api_client import SPAPIClient
from .ads_api_client import AdsAPIClient


class DataFetcher:
    """
    Unified data fetcher combining SP API + Ads API.
    Provides skill-ready data structures.
    """

    def __init__(self, env_file=None):
        """Initialize both API clients."""
        self.sp = SPAPIClient(env_file=env_file)
        self.ads = AdsAPIClient(env_file=env_file)
        self.cache_dir = '/tmp/api_cache'
        os.makedirs(self.cache_dir, exist_ok=True)

    # ─── Product & Listing Data ─────────────────────────────────────────────

    def get_our_listing(self, asin):
        """
        Get our product listing data — used by listing-optimization skill.
        Returns format compatible with Step 1 scrape output.
        """
        print(f"Fetching listing data for {asin}...")

        catalog = self.sp.get_catalog_item(asin, include_data=[
            'attributes', 'images', 'summaries', 'salesRanks'
        ])

        if not catalog:
            raise ValueError(f"Could not find catalog data for {asin}")

        summaries = catalog.get('summaries', [{}])
        summary = summaries[0] if summaries else {}

        attributes = catalog.get('attributes', {})
        images = catalog.get('images', [{}])
        image_list = images[0].get('images', []) if images else []
        sales_ranks = catalog.get('salesRanks', [])

        # Extract bullet points from attributes
        bullets = []
        bullet_attrs = attributes.get('bullet_point', [])
        if bullet_attrs:
            for bp in bullet_attrs:
                value = bp.get('value', '')
                if value:
                    bullets.append(value)

        # Extract title
        title = summary.get('itemName', '')
        if not title:
            title_attrs = attributes.get('item_name', [])
            if title_attrs:
                title = title_attrs[0].get('value', '')

        # Extract price
        price = ''
        price_attrs = attributes.get('list_price', [])
        if price_attrs:
            price = price_attrs[0].get('value', '')

        # Extract brand
        brand = summary.get('brand', '')

        # Extract category
        category_parts = []
        browse = summary.get('browseClassification', {})
        if browse:
            category_parts = [browse.get('displayName', '')]

        # BSR
        bsr = None
        if sales_ranks:
            for rank_set in sales_ranks:
                for rank in rank_set.get('ranks', []):
                    if rank.get('title'):
                        bsr = rank.get('value')
                        break

        listing = {
            'asin': asin,
            'title': title,
            'brand': brand,
            'bullets': bullets,
            'price': price,
            'rating': None,  # Not available via catalog API, needs scraping
            'reviewCount': None,
            'imageCount': len(image_list),
            'images': [img.get('link', '') for img in image_list],
            'hasAPlus': None,  # Not detectable via API
            'category': category_parts,
            'bsr': bsr,
            'source': 'sp_api',
            'fetched_at': datetime.now().isoformat(),
        }

        return listing

    def get_competitor_listings(self, asins):
        """
        Get listing data for multiple ASINs — used by listing-optimization skill.
        Returns list of listings in same format as get_our_listing.
        """
        print(f"Fetching listings for {len(asins)} competitors...")
        listings = []

        for i, asin in enumerate(asins):
            try:
                listing = self.get_our_listing(asin)
                listings.append(listing)
                print(f"  [{i+1}/{len(asins)}] {asin}: {listing['brand']} - {listing['title'][:50]}...")
            except Exception as e:
                print(f"  [{i+1}/{len(asins)}] {asin}: ERROR - {e}")
                listings.append({'asin': asin, 'error': str(e)})

            # Rate limit: 2 requests/sec for catalog API
            import time
            time.sleep(0.5)

        return {'listings': listings, 'fetched_at': datetime.now().isoformat()}

    # ─── PPC Data ───────────────────────────────────────────────────────────

    def get_search_term_report(self, days_back=60, output_dir=None):
        """
        Get search term report — used by ppc-optimization skill.
        Returns data in same format as parse_search_terms.py output.
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        if not output_dir:
            output_dir = self.cache_dir

        output_path = os.path.join(output_dir, f'search_term_report_{start_date}_{end_date}.json')

        # Fetch from API
        raw_data = self.ads.get_search_term_report(start_date, end_date, output_path)

        # Convert to skill-compatible format
        search_terms = []
        for row in raw_data:
            impressions = int(row.get('impressions', 0))
            clicks = int(row.get('clicks', 0))
            spend = float(row.get('cost', 0))
            sales = float(row.get('sales7d', 0))
            orders = int(row.get('purchases7d', row.get('orders7d', 0)))  # API uses purchases7d

            acos = (spend / sales * 100) if sales > 0 else 0
            cvr = (orders / clicks * 100) if clicks > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0
            rpc = (sales / clicks) if clicks > 0 else 0

            search_terms.append({
                'search_term': row.get('searchTerm', '').lower().strip(),
                'campaign': row.get('campaignName', ''),
                'ad_group': row.get('adGroupName', ''),
                'targeting': row.get('keyword', row.get('keywordText', '')),  # API uses 'keyword'
                'match_type': row.get('matchType', ''),
                'impressions': impressions,
                'clicks': clicks,
                'spend': round(spend, 2),
                'sales': round(sales, 2),
                'orders': orders,
                'acos': round(acos, 2),
                'cvr': round(cvr, 2),
                'cpc': round(cpc, 2),
                'revenue_per_click': round(rpc, 2),
                'campaign_id': row.get('campaignId', ''),
                'ad_group_id': row.get('adGroupId', ''),
            })

        # Sort by spend descending
        search_terms.sort(key=lambda x: x['spend'], reverse=True)

        total_spend = sum(t['spend'] for t in search_terms)
        total_sales = sum(t['sales'] for t in search_terms)
        overall_acos = (total_spend / total_sales * 100) if total_sales > 0 else 0

        result = {
            'report_period': {'start': start_date, 'end': end_date, 'days': days_back},
            'total_unique_terms': len(search_terms),
            'total_spend': round(total_spend, 2),
            'total_sales': round(total_sales, 2),
            'overall_acos': round(overall_acos, 2),
            'search_terms': search_terms,
            'source': 'ads_api',
            'fetched_at': datetime.now().isoformat(),
        }

        # Save
        result_path = os.path.join(output_dir, f'search_terms_clean_{end_date}.json')
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\nSearch Term Report:")
        print(f"  Period: {start_date} to {end_date}")
        print(f"  Unique terms: {len(search_terms)}")
        print(f"  Total spend: ${total_spend:,.2f}")
        print(f"  Total sales: ${total_sales:,.2f}")
        print(f"  Overall ACOS: {overall_acos:.1f}%")
        print(f"  Saved to: {result_path}")

        return result

    def get_campaign_structure(self, output_dir=None):
        """
        Get current campaign structure — campaigns, ad groups, keywords.
        Used by ppc-optimization skill for analysis.
        """
        if not output_dir:
            output_dir = self.cache_dir

        structure = self.ads.get_full_account_structure()

        # Flatten for easier analysis
        campaigns = []
        for camp_data in structure:
            camp = camp_data['campaign']
            for ag_data in camp_data['ad_groups']:
                ag = ag_data['ad_group']
                for kw in ag_data.get('keywords', []):
                    campaigns.append({
                        'campaign_name': camp.get('name', ''),
                        'campaign_id': camp.get('campaignId', ''),
                        'campaign_status': camp.get('state', ''),
                        'campaign_budget': camp.get('budget', {}).get('budget', 0),
                        'ad_group_name': ag.get('name', ''),
                        'ad_group_id': ag.get('adGroupId', ''),
                        'ad_group_bid': ag.get('defaultBid', 0),
                        'keyword': kw.get('keywordText', ''),
                        'keyword_id': kw.get('keywordId', ''),
                        'match_type': kw.get('matchType', ''),
                        'keyword_bid': kw.get('bid', 0),
                        'keyword_state': kw.get('state', ''),
                    })

        result = {
            'total_campaigns': len(structure),
            'total_ad_groups': sum(len(c['ad_groups']) for c in structure),
            'total_keywords': len(campaigns),
            'keywords': campaigns,
            'raw_structure': structure,
            'fetched_at': datetime.now().isoformat(),
        }

        output_path = os.path.join(output_dir, f'campaign_structure_{datetime.now().strftime("%Y-%m-%d")}.json')
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"\nCampaign Structure:")
        print(f"  Campaigns: {result['total_campaigns']}")
        print(f"  Ad Groups: {result['total_ad_groups']}")
        print(f"  Keywords: {result['total_keywords']}")
        print(f"  Saved to: {output_path}")

        return result

    def get_campaign_performance(self, days_back=30, output_dir=None):
        """Get campaign-level performance metrics."""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        if not output_dir:
            output_dir = self.cache_dir

        data = self.ads.get_campaign_performance_report(start_date, end_date)
        output_path = os.path.join(output_dir, f'campaign_performance_{end_date}.json')

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return data

    def get_keyword_performance(self, days_back=30, output_dir=None):
        """
        Get keyword-level performance — used by ppc-optimization skill.
        Returns per-keyword impressions, clicks, spend, sales, ACOS, bids.
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        if not output_dir:
            output_dir = self.cache_dir

        raw_data = self.ads.get_keyword_performance_report(start_date, end_date)

        keywords = []
        for row in raw_data:
            impressions = int(row.get('impressions', 0))
            clicks = int(row.get('clicks', 0))
            spend = float(row.get('cost', 0))
            sales = float(row.get('sales7d', 0))
            orders = int(row.get('purchases7d', 0))
            bid = float(row.get('keywordBid', 0) or 0)

            acos = (spend / sales * 100) if sales > 0 else 0
            cvr = (orders / clicks * 100) if clicks > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0

            keywords.append({
                'keyword': row.get('keyword', row.get('keywordText', '')),
                'keyword_id': row.get('keywordId', ''),
                'match_type': row.get('matchType', ''),
                'campaign_id': row.get('campaignId', ''),
                'ad_group': row.get('adGroupName', ''),
                'ad_group_id': row.get('adGroupId', ''),
                'impressions': impressions,
                'clicks': clicks,
                'spend': round(spend, 2),
                'sales': round(sales, 2),
                'orders': orders,
                'acos': round(acos, 2),
                'cvr': round(cvr, 2),
                'cpc': round(cpc, 2),
                'bid': round(bid, 2),
            })

        keywords.sort(key=lambda x: x['spend'], reverse=True)

        result = {
            'report_period': {'start': start_date, 'end': end_date},
            'total_keywords': len(keywords),
            'total_spend': round(sum(k['spend'] for k in keywords), 2),
            'total_sales': round(sum(k['sales'] for k in keywords), 2),
            'keywords': keywords,
            'source': 'ads_api',
            'fetched_at': datetime.now().isoformat(),
        }

        output_path = os.path.join(output_dir, f'keyword_performance_{end_date}.json')
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\nKeyword Performance:")
        print(f"  Keywords: {len(keywords)}")
        print(f"  Total spend: ${result['total_spend']:,.2f}")
        print(f"  Total sales: ${result['total_sales']:,.2f}")
        print(f"  Saved to: {output_path}")

        return result

    def get_placement_performance(self, days_back=30, output_dir=None):
        """
        Get placement-level performance — Top of Search vs Rest vs Product Pages.
        Critical for bid adjustment strategy.
        """
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        if not output_dir:
            output_dir = self.cache_dir

        raw_data = self.ads.get_placement_report(start_date, end_date)

        placements = {}
        for row in raw_data:
            placement = row.get('campaignPlacement', row.get('placementClassification', 'UNKNOWN'))
            campaign = row.get('campaignName', '')
            impressions = int(row.get('impressions', 0))
            clicks = int(row.get('clicks', 0))
            spend = float(row.get('cost', 0))
            sales = float(row.get('sales7d', 0))

            key = f"{campaign}|{placement}"
            if key not in placements:
                placements[key] = {
                    'campaign': campaign,
                    'campaign_id': row.get('campaignId', ''),
                    'placement': placement,
                    'impressions': 0, 'clicks': 0, 'spend': 0, 'sales': 0,
                }
            placements[key]['impressions'] += impressions
            placements[key]['clicks'] += clicks
            placements[key]['spend'] += spend
            placements[key]['sales'] += sales

        # Calculate derived metrics
        placement_list = []
        for p in placements.values():
            p['acos'] = round((p['spend'] / p['sales'] * 100) if p['sales'] > 0 else 0, 2)
            p['cpc'] = round((p['spend'] / p['clicks']) if p['clicks'] > 0 else 0, 2)
            p['ctr'] = round((p['clicks'] / p['impressions'] * 100) if p['impressions'] > 0 else 0, 2)
            p['spend'] = round(p['spend'], 2)
            p['sales'] = round(p['sales'], 2)
            placement_list.append(p)

        # Aggregate by placement type
        summary = {}
        for p in placement_list:
            pt = p['placement']
            if pt not in summary:
                summary[pt] = {'impressions': 0, 'clicks': 0, 'spend': 0, 'sales': 0}
            summary[pt]['impressions'] += p['impressions']
            summary[pt]['clicks'] += p['clicks']
            summary[pt]['spend'] += p['spend']
            summary[pt]['sales'] += p['sales']

        for pt in summary:
            s = summary[pt]
            s['acos'] = round((s['spend'] / s['sales'] * 100) if s['sales'] > 0 else 0, 2)
            s['cpc'] = round((s['spend'] / s['clicks']) if s['clicks'] > 0 else 0, 2)

        result = {
            'report_period': {'start': start_date, 'end': end_date},
            'placement_summary': summary,
            'by_campaign': placement_list,
            'source': 'ads_api',
            'fetched_at': datetime.now().isoformat(),
        }

        output_path = os.path.join(output_dir, f'placement_performance_{end_date}.json')
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\nPlacement Performance:")
        for pt, s in summary.items():
            print(f"  {pt}: Spend ${s['spend']:,.2f} | Sales ${s['sales']:,.2f} | ACOS {s['acos']}%")
        print(f"  Saved to: {output_path}")

        return result

    # ─── Business Reports (SP API) ──────────────────────────────────────────

    def get_business_report(self, days_back=30, output_dir=None):
        """
        Get Business Report (traffic & sales by ASIN) from SP API.
        Provides sessions, page views, units ordered, total sales per ASIN.
        """
        end_date = datetime.now().strftime('%Y-%m-%dT00:00:00Z')
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%dT00:00:00Z')

        if not output_dir:
            output_dir = self.cache_dir

        output_path = os.path.join(output_dir, f'business_report_{datetime.now().strftime("%Y-%m-%d")}.json')
        self.sp.request_and_download_report(
            'GET_SALES_AND_TRAFFIC_REPORT',
            output_path,
            start_date=start_date,
            end_date=end_date,
            report_options={'dateGranularity': 'DAY', 'asinGranularity': 'CHILD'}
        )

        with open(output_path) as f:
            return json.load(f)

    # ─── Convenience: Full Data Pull ────────────────────────────────────────

    def pull_all_data(self, asin, competitor_asins=None, days_back=60, output_dir=None):
        """
        Pull ALL data needed for listing-optimization + ppc-optimization in one call.

        Returns dict with:
        - our_listing: our product listing data
        - competitor_listings: competitor listing data (if competitor_asins provided)
        - search_terms: PPC search term report
        - campaign_structure: current campaign structure
        - campaign_performance: campaign performance data
        - keyword_performance: keyword-level performance (spend, sales, ACOS, bids)
        - placement_performance: Top of Search vs Rest vs Product Pages
        """
        if not output_dir:
            output_dir = self.cache_dir

        print(f"=== Full Data Pull for {asin} ===\n")

        results = {}

        # 1. Our listing
        print("--- Step 1: Our Listing ---")
        try:
            results['our_listing'] = self.get_our_listing(asin)
            print(f"  ✅ Got listing: {results['our_listing']['title'][:60]}...\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            results['our_listing'] = None

        # 2. Competitor listings
        if competitor_asins:
            print("--- Step 2: Competitor Listings ---")
            try:
                results['competitor_listings'] = self.get_competitor_listings(competitor_asins)
                valid = sum(1 for l in results['competitor_listings']['listings'] if 'error' not in l)
                print(f"  ✅ Got {valid}/{len(competitor_asins)} competitor listings\n")
            except Exception as e:
                print(f"  ❌ Failed: {e}\n")
                results['competitor_listings'] = None
        else:
            results['competitor_listings'] = None

        # 3. Search term report
        print("--- Step 3: Search Term Report ---")
        try:
            results['search_terms'] = self.get_search_term_report(days_back, output_dir)
            print(f"  ✅ Got {results['search_terms']['total_unique_terms']} search terms\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            results['search_terms'] = None

        # 4. Campaign structure
        print("--- Step 4: Campaign Structure ---")
        try:
            results['campaign_structure'] = self.get_campaign_structure(output_dir)
            print(f"  ✅ Got {results['campaign_structure']['total_campaigns']} campaigns\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            results['campaign_structure'] = None

        # 5. Campaign performance
        print("--- Step 5: Campaign Performance ---")
        try:
            results['campaign_performance'] = self.get_campaign_performance(days_back, output_dir)
            print(f"  ✅ Got campaign performance data\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            results['campaign_performance'] = None

        # 6. Keyword performance
        print("--- Step 6: Keyword Performance ---")
        try:
            results['keyword_performance'] = self.get_keyword_performance(days_back, output_dir)
            print(f"  ✅ Got {results['keyword_performance']['total_keywords']} keywords\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            results['keyword_performance'] = None

        # 7. Placement performance
        print("--- Step 7: Placement Performance ---")
        try:
            results['placement_performance'] = self.get_placement_performance(days_back, output_dir)
            placements = results['placement_performance']['placement_summary']
            print(f"  ✅ Got {len(placements)} placement types\n")
        except Exception as e:
            print(f"  ❌ Failed: {e}\n")
            results['placement_performance'] = None

        # Save summary
        summary_path = os.path.join(output_dir, f'data_pull_summary_{datetime.now().strftime("%Y-%m-%d")}.json')
        summary = {
            'asin': asin,
            'days_back': days_back,
            'data_available': {k: v is not None for k, v in results.items()},
            'fetched_at': datetime.now().isoformat(),
        }
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"=== Data Pull Complete ===")
        for k, v in results.items():
            status = '✅' if v else '❌'
            print(f"  {status} {k}")

        return results


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Unified Data Fetcher')
    parser.add_argument('--env-file', default=None)
    parser.add_argument('--test', action='store_true', help='Test both API connections')
    parser.add_argument('--pull-all', type=str, metavar='ASIN', help='Pull all data for ASIN')
    parser.add_argument('--competitors', type=str, nargs='*', help='Competitor ASINs')
    parser.add_argument('--days', type=int, default=60, help='Days back for reports')
    parser.add_argument('--output-dir', type=str, default=None)
    args = parser.parse_args()

    if args.test:
        from .sp_api_client import test_connection as test_sp
        from .ads_api_client import test_connection as test_ads
        print("Testing SP API...")
        test_sp(args.env_file)
        print("\nTesting Ads API...")
        test_ads(args.env_file)
    elif args.pull_all:
        fetcher = DataFetcher(env_file=args.env_file)
        fetcher.pull_all_data(args.pull_all, args.competitors, args.days, args.output_dir)
