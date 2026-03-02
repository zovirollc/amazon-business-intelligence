#!/usr/bin/env python3
"""
Amazon Selling Partner API Client
Handles authentication (LWA OAuth), catalog, listings, and reports endpoints.

Docs: https://developer-docs.amazon.com/sp-api/
"""

import os
import json
import time
import hashlib
import hmac
import datetime
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'requests', '--break-system-packages', '-q'])
    import requests


# ─── Configuration ──────────────────────────────────────────────────────────

MARKETPLACE_US = 'ATVPDKIKX0DER'
ENDPOINT_NA = 'https://sellingpartnerapi-na.amazon.com'
LWA_TOKEN_URL = 'https://api.amazon.com/auth/o2/token'

ENV_PREFIX = 'SP_API_'


class SPAPIClient:
    """Amazon Selling Partner API client with LWA authentication."""

    def __init__(self, refresh_token=None, client_id=None, client_secret=None,
                 marketplace_id=None, seller_id=None, env_file=None):
        """
        Initialize SP API client.
        Credentials loaded from: explicit params > env vars > .env file
        """
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)

        self.refresh_token = refresh_token or os.environ.get(f'{ENV_PREFIX}REFRESH_TOKEN', '')
        self.client_id = client_id or os.environ.get(f'{ENV_PREFIX}CLIENT_ID', '')
        self.client_secret = client_secret or os.environ.get(f'{ENV_PREFIX}CLIENT_SECRET', '')
        self.marketplace_id = marketplace_id or os.environ.get(f'{ENV_PREFIX}MARKETPLACE_ID', MARKETPLACE_US)
        self.seller_id = seller_id or os.environ.get(f'{ENV_PREFIX}SELLER_ID', '')

        self.endpoint = ENDPOINT_NA
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
        """Check that all required credentials are present."""
        missing = []
        if not self.refresh_token:
            missing.append('SP_API_REFRESH_TOKEN')
        if not self.client_id:
            missing.append('SP_API_CLIENT_ID')
        if not self.client_secret:
            missing.append('SP_API_CLIENT_SECRET')
        if missing:
            raise ValueError(f"Missing SP API credentials: {', '.join(missing)}. "
                           f"Set via environment variables or .env file.")

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

    def _headers(self):
        """Build request headers with auth token."""
        return {
            'x-amz-access-token': self._get_access_token(),
            'Content-Type': 'application/json',
        }

    def _request(self, method, path, params=None, json_body=None, retries=3):
        """Make authenticated request with retry logic."""
        url = f"{self.endpoint}{path}"

        for attempt in range(retries):
            try:
                resp = requests.request(
                    method, url,
                    headers=self._headers(),
                    params=params,
                    json=json_body,
                    timeout=30
                )

                # Rate limiting
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 2))
                    print(f"  Rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue

                resp.raise_for_status()
                return resp.json()

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

    # ─── Catalog API ────────────────────────────────────────────────────────

    def get_catalog_item(self, asin, include_data=None):
        """
        Get catalog item details for an ASIN.
        include_data: list of data sets - 'attributes', 'images', 'productTypes',
                      'salesRanks', 'summaries', 'dimensions', 'identifiers'
        """
        if include_data is None:
            include_data = ['attributes', 'images', 'summaries', 'salesRanks']

        params = {
            'marketplaceIds': self.marketplace_id,
            'includedData': ','.join(include_data),
        }
        return self._request('GET', f'/catalog/2022-04-01/items/{asin}', params=params)

    def search_catalog(self, keywords, page_size=20):
        """Search catalog by keywords."""
        params = {
            'marketplaceIds': self.marketplace_id,
            'keywords': keywords,
            'pageSize': page_size,
            'includedData': 'summaries,salesRanks',
        }
        return self._request('GET', '/catalog/2022-04-01/items', params=params)

    # ─── Listings API ───────────────────────────────────────────────────────

    def get_listing(self, sku, seller_id=None, include_data=None):
        """
        Get listing details for a SKU.
        include_data: 'summaries', 'attributes', 'issues', 'offers', 'fulfillmentAvailability'
        """
        if include_data is None:
            include_data = ['summaries', 'attributes', 'issues']

        sid = seller_id or self.seller_id
        if not sid:
            raise ValueError("seller_id required — set SP_API_SELLER_ID env var or pass seller_id param")

        params = {
            'marketplaceIds': self.marketplace_id,
            'includedData': ','.join(include_data),
        }
        return self._request('GET', f'/listings/2021-08-01/items/{sid}/{sku}', params=params)

    def patch_listing(self, sku, patches, seller_id=None):
        """
        Update listing attributes.
        patches: list of JSON Patch operations, e.g.:
        [{"op": "replace", "path": "/attributes/item_name", "value": [{"value": "New Title"}]}]
        """
        sid = seller_id or self.seller_id
        if not sid:
            raise ValueError("seller_id required — set SP_API_SELLER_ID env var or pass seller_id param")

        body = {
            'productType': 'PRODUCT',  # Will need to be set per product
            'patches': patches,
        }
        params = {'marketplaceIds': self.marketplace_id}
        return self._request('PATCH', f'/listings/2021-08-01/items/{sid}/{sku}',
                           params=params, json_body=body)

    # ─── Reports API ────────────────────────────────────────────────────────

    def create_report(self, report_type, start_date=None, end_date=None, report_options=None):
        """
        Create a report request.
        Common report types:
        - GET_FLAT_FILE_ALL_ORDERS_DATA_BY_LAST_UPDATE_GENERAL
        - GET_MERCHANT_LISTINGS_ALL_DATA
        - GET_SALES_AND_TRAFFIC_REPORT (Business Reports)
        - GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT
        """
        body = {
            'reportType': report_type,
            'marketplaceIds': [self.marketplace_id],
        }
        if start_date:
            body['dataStartTime'] = start_date.isoformat() if hasattr(start_date, 'isoformat') else start_date
        if end_date:
            body['dataEndTime'] = end_date.isoformat() if hasattr(end_date, 'isoformat') else end_date
        if report_options:
            body['reportOptions'] = report_options

        return self._request('POST', '/reports/2021-06-30/reports', json_body=body)

    def get_report_status(self, report_id):
        """Check report generation status."""
        return self._request('GET', f'/reports/2021-06-30/reports/{report_id}')

    def get_report_document(self, document_id):
        """Get report document download URL."""
        return self._request('GET', f'/reports/2021-06-30/documents/{document_id}')

    def download_report(self, document_id, output_path):
        """Download a report document to a file."""
        doc = self.get_report_document(document_id)
        if not doc or 'url' not in doc:
            raise ValueError(f"Could not get download URL for document {document_id}")

        resp = requests.get(doc['url'], timeout=60)
        resp.raise_for_status()

        # Handle compression
        content = resp.content
        if doc.get('compressionAlgorithm') == 'GZIP':
            import gzip
            content = gzip.decompress(content)

        with open(output_path, 'wb') as f:
            f.write(content)

        return output_path

    def wait_for_report(self, report_id, timeout=300, poll_interval=10):
        """Wait for report to complete and return document ID."""
        start = time.time()
        while time.time() - start < timeout:
            status = self.get_report_status(report_id)
            processing_status = status.get('processingStatus', '')

            if processing_status == 'DONE':
                return status.get('reportDocumentId')
            elif processing_status in ('CANCELLED', 'FATAL'):
                raise RuntimeError(f"Report {report_id} failed: {processing_status}")

            print(f"  Report status: {processing_status}, waiting {poll_interval}s...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Report {report_id} did not complete within {timeout}s")

    def request_and_download_report(self, report_type, output_path,
                                     start_date=None, end_date=None, report_options=None):
        """Full flow: create report → wait → download."""
        print(f"Requesting report: {report_type}")
        result = self.create_report(report_type, start_date, end_date, report_options)
        report_id = result.get('reportId')
        print(f"  Report ID: {report_id}")

        doc_id = self.wait_for_report(report_id)
        print(f"  Document ID: {doc_id}")

        self.download_report(doc_id, output_path)
        print(f"  Downloaded to: {output_path}")
        return output_path

    # ─── Convenience Methods ────────────────────────────────────────────────

    def get_product_details(self, asin):
        """Get comprehensive product details combining catalog + listing data."""
        catalog = self.get_catalog_item(asin)
        if not catalog:
            return None

        # Extract useful fields
        summaries = catalog.get('summaries', [{}])
        summary = summaries[0] if summaries else {}

        attributes = catalog.get('attributes', {})
        images = catalog.get('images', [{}])
        image_set = images[0].get('images', []) if images else []
        sales_ranks = catalog.get('salesRanks', [{}])

        return {
            'asin': asin,
            'title': summary.get('itemName', ''),
            'brand': summary.get('brand', ''),
            'category': summary.get('browseClassification', {}).get('displayName', ''),
            'product_type': summary.get('productType', ''),
            'image_count': len(image_set),
            'images': [img.get('link', '') for img in image_set],
            'sales_ranks': sales_ranks,
            'marketplace': summary.get('marketplaceId', ''),
            'raw_catalog': catalog,
        }

    def get_all_listings(self, seller_id=None):
        """Download complete listings report."""
        sid = seller_id or self.seller_id or 'default'
        output_path = f'/tmp/listings_{sid}.tsv'
        return self.request_and_download_report(
            'GET_MERCHANT_LISTINGS_ALL_DATA',
            output_path
        )

    def get_business_report(self, start_date, end_date):
        """Download Business Reports (traffic + sales by ASIN)."""
        output_path = f'/tmp/business_report_{start_date}.json'
        return self.request_and_download_report(
            'GET_SALES_AND_TRAFFIC_REPORT',
            output_path,
            start_date=start_date,
            end_date=end_date,
            report_options={'dateGranularity': 'DAY', 'asinGranularity': 'CHILD'}
        )

    def get_brand_analytics_search_terms(self, start_date, end_date):
        """Download Brand Analytics Search Terms report (requires Brand Registry)."""
        output_path = f'/tmp/brand_analytics_{start_date}.json'
        return self.request_and_download_report(
            'GET_BRAND_ANALYTICS_SEARCH_TERMS_REPORT',
            output_path,
            start_date=start_date,
            end_date=end_date,
            report_options={'reportPeriod': 'WEEK'}
        )


# ─── Quick Test ─────────────────────────────────────────────────────────────

def test_connection(env_file=None):
    """Test SP API connection."""
    try:
        client = SPAPIClient(env_file=env_file)
        token = client._get_access_token()
        print(f"✅ SP API connection successful (token: {token[:20]}...)")
        return True
    except Exception as e:
        print(f"❌ SP API connection failed: {e}")
        return False


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Test API connection')
    parser.add_argument('--env-file', default=None, help='Path to .env file')
    parser.add_argument('--get-product', type=str, help='Get product details for ASIN')
    args = parser.parse_args()

    if args.test:
        test_connection(args.env_file)
    elif args.get_product:
        client = SPAPIClient(env_file=args.env_file)
        details = client.get_product_details(args.get_product)
        print(json.dumps(details, indent=2, default=str))
