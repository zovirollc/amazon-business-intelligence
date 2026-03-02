#!/usr/bin/env python3
"""
Amazon Advertising API Client
Handles authentication, campaign management, keyword operations, and report downloads.

Docs: https://advertising.amazon.com/API/docs/en-us
"""

import os
import json
import time
import gzip
import io

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'requests', '--break-system-packages', '-q'])
    import requests


# ─── Configuration ──────────────────────────────────────────────────────────

LWA_TOKEN_URL = 'https://api.amazon.com/auth/o2/token'
ADS_API_BASE = 'https://advertising-api.amazon.com'

ENV_PREFIX = 'ADS_API_'


class AdsAPIClient:
    """Amazon Advertising API client."""

    def __init__(self, profile_id=None, client_id=None, client_secret=None,
                 refresh_token=None, env_file=None):
        """
        Initialize Ads API client.
        Credentials loaded from: explicit params > env vars > .env file
        """
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)

        self.profile_id = profile_id or os.environ.get(f'{ENV_PREFIX}PROFILE_ID', '')
        self.client_id = client_id or os.environ.get(f'{ENV_PREFIX}CLIENT_ID', '')
        self.client_secret = client_secret or os.environ.get(f'{ENV_PREFIX}CLIENT_SECRET', '')
        self.refresh_token = refresh_token or os.environ.get(f'{ENV_PREFIX}REFRESH_TOKEN', '')

        self.access_token = None
        self.token_expiry = 0

        self._validate_credentials()

    def _load_env_file(self, env_file):
        """Load environment variables from .env file."""
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

    def _validate_credentials(self):
        """Check required credentials."""
        missing = []
        if not self.profile_id:
            missing.append('ADS_API_PROFILE_ID')
        if not self.client_id:
            missing.append('ADS_API_CLIENT_ID')
        if not self.client_secret:
            missing.append('ADS_API_CLIENT_SECRET')
        if not self.refresh_token:
            missing.append('ADS_API_REFRESH_TOKEN')
        if missing:
            raise ValueError(f"Missing Ads API credentials: {', '.join(missing)}")

    # ─── Authentication ─────────────────────────────────────────────────────

    def _get_access_token(self):
        """Get or refresh LWA access token."""
        if self.access_token and time.time() < self.token_expiry - 60:
            return self.access_token

        resp = requests.post(LWA_TOKEN_URL, data={
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        })
        resp.raise_for_status()
        data = resp.json()

        self.access_token = data['access_token']
        self.token_expiry = time.time() + data.get('expires_in', 3600)
        return self.access_token

    def _headers(self, content_type='application/json'):
        """Build request headers. Accept mirrors Content-Type for versioned SP v3 endpoints."""
        return {
            'Authorization': f'Bearer {self._get_access_token()}',
            'Amazon-Advertising-API-ClientId': self.client_id,
            'Amazon-Advertising-API-Scope': self.profile_id,
            'Content-Type': content_type,
            'Accept': content_type,
        }

    def _request(self, method, path, params=None, json_body=None, retries=3, content_type=None):
        """Make authenticated request with retry logic."""
        url = f"{ADS_API_BASE}{path}"

        for attempt in range(retries):
            try:
                resp = requests.request(
                    method, url,
                    headers=self._headers(content_type or 'application/json'),
                    params=params,
                    json=json_body,
                    timeout=30
                )

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 5))
                    print(f"  Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                resp.raise_for_status()
                return resp.json() if resp.content else {}

            except requests.exceptions.HTTPError as e:
                if attempt < retries - 1 and resp.status_code >= 500:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

        return None

    # ─── Profiles ───────────────────────────────────────────────────────────

    def list_profiles(self):
        """List all advertising profiles."""
        return self._request('GET', '/v2/profiles')

    # ─── Campaigns (SP v3) ──────────────────────────────────────────────────

    def list_campaigns(self, state_filter=None, max_results=100):
        """List Sponsored Products campaigns."""
        body = {'maxResults': max_results}
        if state_filter:
            body['stateFilter'] = {'include': [state_filter]}
        return self._request('POST', '/sp/campaigns/list', json_body=body,
                             content_type='application/vnd.spCampaign.v3+json')

    def get_campaign(self, campaign_id):
        """Get campaign details."""
        return self._request('POST', '/sp/campaigns/list',
                           json_body={'campaignIdFilter': {'include': [str(campaign_id)]}},
                           content_type='application/vnd.spCampaign.v3+json')

    # ─── Ad Groups ──────────────────────────────────────────────────────────

    def list_ad_groups(self, campaign_id=None, max_results=100):
        """List ad groups, optionally filtered by campaign."""
        body = {'maxResults': max_results}
        if campaign_id:
            body['campaignIdFilter'] = {'include': [str(campaign_id)]}
        return self._request('POST', '/sp/adGroups/list', json_body=body,
                             content_type='application/vnd.spAdGroup.v3+json')

    # ─── Keywords ───────────────────────────────────────────────────────────

    def list_keywords(self, campaign_id=None, ad_group_id=None, max_results=200):
        """List targeting keywords."""
        body = {'maxResults': max_results}
        if campaign_id:
            body['campaignIdFilter'] = {'include': [str(campaign_id)]}
        if ad_group_id:
            body['adGroupIdFilter'] = {'include': [str(ad_group_id)]}
        return self._request('POST', '/sp/keywords/list', json_body=body,
                             content_type='application/vnd.spKeyword.v3+json')

    def list_negative_keywords(self, campaign_id=None, max_results=200):
        """List negative keywords."""
        body = {'maxResults': max_results}
        if campaign_id:
            body['campaignIdFilter'] = {'include': [str(campaign_id)]}
        return self._request('POST', '/sp/negativeKeywords/list', json_body=body,
                             content_type='application/vnd.spNegativeKeyword.v3+json')

    def create_keywords(self, keywords):
        """
        Create keywords in bulk.
        keywords: list of dicts with campaignId, adGroupId, keywordText, matchType, bid
        """
        return self._request('POST', '/sp/keywords', json_body={'keywords': keywords})

    def create_negative_keywords(self, negatives):
        """
        Create negative keywords.
        negatives: list of dicts with campaignId, adGroupId, keywordText, matchType
        """
        return self._request('POST', '/sp/negativeKeywords',
                           json_body={'negativeKeywords': negatives})

    def update_keyword_bids(self, updates):
        """
        Update keyword bids.
        updates: list of dicts with keywordId, bid
        """
        return self._request('PUT', '/sp/keywords', json_body={'keywords': updates})

    # ─── Reports (v3) ──────────────────────────────────────────────────────

    def create_report(self, report_config):
        """
        Create a Sponsored Products report.

        report_config example for search term report:
        {
            "name": "Search Term Report",
            "startDate": "2026-01-01",
            "endDate": "2026-02-28",
            "configuration": {
                "adProduct": "SPONSORED_PRODUCTS",
                "groupBy": ["searchTerm"],
                "columns": ["searchTerm", "impressions", "clicks", "cost",
                            "sales7d", "orders7d", "unitsSold7d", "acos7d",
                            "campaignName", "adGroupName", "keywordText", "matchType"],
                "reportTypeId": "spSearchTerm",
                "timeUnit": "SUMMARY",
                "format": "GZIP_JSON"
            }
        }
        """
        return self._request('POST', '/reporting/reports', json_body=report_config)

    def get_report_status(self, report_id):
        """Check report status."""
        return self._request('GET', f'/reporting/reports/{report_id}')

    def download_report(self, report_url, output_path):
        """Download report from pre-signed S3 URL — NO auth headers (S3 rejects them)."""
        resp = requests.get(report_url, timeout=120, stream=True)
        resp.raise_for_status()

        content = resp.content

        # Try gzip decompression
        try:
            content = gzip.decompress(content)
        except (gzip.BadGzipFile, OSError):
            pass  # Not gzipped

        with open(output_path, 'wb') as f:
            f.write(content)

        return output_path

    def wait_for_report(self, report_id, timeout=300, poll_interval=10):
        """Wait for report completion and return download URL."""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_report_status(report_id)
            state = status.get('status', '')

            if state == 'COMPLETED':
                return status.get('url')
            elif state == 'FAILED':
                raise RuntimeError(f"Report failed: {status.get('failureReason', 'unknown')}")

            print(f"  Report status: {state}, waiting {poll_interval}s...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Report did not complete within {timeout}s")

    # ─── Convenience Methods ────────────────────────────────────────────────

    def get_search_term_report(self, start_date, end_date, output_path=None):
        """
        Full flow: request search term report → wait → download → parse.
        Returns parsed JSON data.
        Note: max date range is 31 days per API limit.
        """
        # Enforce 31-day max window
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if (end_dt - start_dt).days > 31:
            start_date = (end_dt - timedelta(days=31)).strftime('%Y-%m-%d')
            print(f"  Note: date range capped to 31 days → {start_date} to {end_date}")

        print(f"Requesting search term report: {start_date} to {end_date}")

        config = {
            'name': f'Search Term Report {start_date}',
            'startDate': start_date,
            'endDate': end_date,
            'configuration': {
                'adProduct': 'SPONSORED_PRODUCTS',
                'groupBy': ['searchTerm'],
                'columns': [
                    'searchTerm', 'impressions', 'clicks', 'cost',
                    'sales7d', 'purchases7d', 'unitsSoldClicks7d',
                    'keyword', 'matchType',
                    'campaignId', 'adGroupId', 'adGroupName'
                ],
                'reportTypeId': 'spSearchTerm',
                'timeUnit': 'SUMMARY',
                'format': 'GZIP_JSON'
            }
        }

        result = self.create_report(config)
        report_id = result.get('reportId')
        print(f"  Report ID: {report_id}")

        download_url = self.wait_for_report(report_id)
        print(f"  Report ready, downloading...")

        if not output_path:
            output_path = f'/tmp/search_term_report_{start_date}.json'

        self.download_report(download_url, output_path)
        print(f"  Saved to: {output_path}")

        # Parse JSON
        with open(output_path) as f:
            data = json.load(f)

        return data

    def get_campaign_performance_report(self, start_date, end_date, output_path=None):
        """Get campaign-level performance report."""
        # Enforce 31-day max window
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if (end_dt - start_dt).days > 31:
            start_date = (end_dt - timedelta(days=31)).strftime('%Y-%m-%d')

        print(f"Requesting campaign performance report: {start_date} to {end_date}")

        config = {
            'name': f'Campaign Report {start_date}',
            'startDate': start_date,
            'endDate': end_date,
            'configuration': {
                'adProduct': 'SPONSORED_PRODUCTS',
                'groupBy': ['campaign'],
                'columns': [
                    'campaignName', 'campaignId', 'campaignStatus',
                    'impressions', 'clicks', 'cost',
                    'sales7d', 'purchases7d', 'unitsSoldClicks7d',
                    'campaignBudgetAmount', 'campaignBudgetCurrencyCode'
                ],
                'reportTypeId': 'spCampaigns',
                'timeUnit': 'SUMMARY',
                'format': 'GZIP_JSON'
            }
        }

        result = self.create_report(config)
        report_id = result.get('reportId')
        download_url = self.wait_for_report(report_id)

        if not output_path:
            output_path = f'/tmp/campaign_report_{start_date}.json'

        self.download_report(download_url, output_path)

        with open(output_path) as f:
            return json.load(f)

    def get_keyword_performance_report(self, start_date, end_date, output_path=None):
        """Get keyword-level performance report."""
        # Enforce 31-day max window
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if (end_dt - start_dt).days > 31:
            start_date = (end_dt - timedelta(days=31)).strftime('%Y-%m-%d')

        print(f"Requesting keyword performance report: {start_date} to {end_date}")

        config = {
            'name': f'Keyword Report {start_date}',
            'startDate': start_date,
            'endDate': end_date,
            'configuration': {
                'adProduct': 'SPONSORED_PRODUCTS',
                'groupBy': ['targeting'],
                'columns': [
                    'keyword', 'keywordId', 'matchType',
                    'campaignId', 'adGroupName', 'adGroupId',
                    'impressions', 'clicks', 'cost',
                    'sales7d', 'purchases7d', 'unitsSoldClicks7d',
                    'keywordBid'
                ],
                'reportTypeId': 'spTargeting',
                'timeUnit': 'SUMMARY',
                'format': 'GZIP_JSON'
            }
        }

        result = self.create_report(config)
        report_id = result.get('reportId')
        download_url = self.wait_for_report(report_id)

        if not output_path:
            output_path = f'/tmp/keyword_report_{start_date}.json'

        self.download_report(download_url, output_path)

        with open(output_path) as f:
            return json.load(f)

    def get_placement_report(self, start_date, end_date, output_path=None):
        """Get placement-level performance report (Top of Search vs Rest vs Product Pages)."""
        # Enforce 31-day max window
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if (end_dt - start_dt).days > 31:
            start_date = (end_dt - timedelta(days=31)).strftime('%Y-%m-%d')

        print(f"Requesting placement report: {start_date} to {end_date}")

        config = {
            'name': f'Placement Report {start_date}',
            'startDate': start_date,
            'endDate': end_date,
            'configuration': {
                'adProduct': 'SPONSORED_PRODUCTS',
                'groupBy': ['campaignPlacement'],
                'columns': [
                    'campaignName', 'campaignId',
                    'impressions', 'clicks', 'cost',
                    'sales7d', 'purchases7d', 'unitsSoldClicks7d'
                ],
                'reportTypeId': 'spCampaigns',
                'timeUnit': 'SUMMARY',
                'format': 'GZIP_JSON'
            }
        }

        result = self.create_report(config)
        report_id = result.get('reportId')
        download_url = self.wait_for_report(report_id)

        if not output_path:
            output_path = f'/tmp/placement_report_{start_date}.json'

        self.download_report(download_url, output_path)

        with open(output_path) as f:
            return json.load(f)

    def get_full_account_structure(self):
        """
        Download complete account structure: campaigns → ad groups → keywords.
        Returns nested dict.
        """
        print("Downloading full account structure...")

        campaigns = self.list_campaigns()
        campaign_list = campaigns.get('campaigns', []) if campaigns else []
        print(f"  Found {len(campaign_list)} campaigns")

        structure = []
        for camp in campaign_list:
            camp_id = camp.get('campaignId')
            camp_data = {
                'campaign': camp,
                'ad_groups': []
            }

            ad_groups = self.list_ad_groups(campaign_id=camp_id)
            ag_list = ad_groups.get('adGroups', []) if ad_groups else []

            for ag in ag_list:
                ag_id = ag.get('adGroupId')
                keywords = self.list_keywords(campaign_id=camp_id, ad_group_id=ag_id)
                negatives = self.list_negative_keywords(campaign_id=camp_id)

                camp_data['ad_groups'].append({
                    'ad_group': ag,
                    'keywords': keywords.get('keywords', []) if keywords else [],
                    'negative_keywords': negatives.get('negativeKeywords', []) if negatives else [],
                })

            structure.append(camp_data)
            time.sleep(0.5)  # Rate limit courtesy

        print(f"  Total ad groups: {sum(len(c['ad_groups']) for c in structure)}")
        return structure


# ─── Quick Test ─────────────────────────────────────────────────────────────

def test_connection(env_file=None):
    """Test Ads API connection."""
    try:
        client = AdsAPIClient(env_file=env_file)
        token = client._get_access_token()
        print(f"✅ Ads API connection successful (token: {token[:20]}...)")

        profiles = client.list_profiles()
        if profiles:
            print(f"  Found {len(profiles)} advertising profile(s)")
            for p in profiles:
                print(f"    - {p.get('accountInfo', {}).get('name', 'N/A')} "
                      f"(ID: {p.get('profileId')}, Marketplace: {p.get('accountInfo', {}).get('marketplaceStringId', '')})")
        return True
    except Exception as e:
        print(f"❌ Ads API connection failed: {e}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--env-file', default=None)
    parser.add_argument('--list-campaigns', action='store_true')
    parser.add_argument('--search-term-report', nargs=2, metavar=('START', 'END'),
                       help='Download search term report for date range')
    args = parser.parse_args()

    if args.test:
        test_connection(args.env_file)
    elif args.list_campaigns:
        client = AdsAPIClient(env_file=args.env_file)
        campaigns = client.list_campaigns()
        print(json.dumps(campaigns, indent=2, default=str))
    elif args.search_term_report:
        client = AdsAPIClient(env_file=args.env_file)
        data = client.get_search_term_report(args.search_term_report[0], args.search_term_report[1])
        print(f"Downloaded {len(data)} search term records")
