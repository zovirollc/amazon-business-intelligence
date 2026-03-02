#!/usr/bin/env python3
"""
Credential Management
Loads API credentials from environment variables or .env file.
NEVER stores secrets in code or config files.
"""
import os
from pathlib import Path


class CredentialManager:
    """
    Load credentials from:
    1. Environment variables (highest priority)
    2. .env file in project root or specified path
    """
    
    def __init__(self, env_file=None):
        self.env_file = env_file
        if env_file and os.path.exists(env_file):
            self._load_env_file(env_file)
    
    def _load_env_file(self, path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
    
    @staticmethod
    def get_sp_api_creds() -> dict:
        return {
            'refresh_token': os.environ.get('SP_API_REFRESH_TOKEN', ''),
            'client_id': os.environ.get('SP_API_CLIENT_ID', ''),
            'client_secret': os.environ.get('SP_API_CLIENT_SECRET', ''),
            'marketplace_id': os.environ.get('SP_API_MARKETPLACE_ID', 'ATVPDKIKX0DER'),
            'seller_id': os.environ.get('SP_API_SELLER_ID', ''),
        }
    
    @staticmethod
    def get_ads_api_creds() -> dict:
        return {
            'profile_id': os.environ.get('ADS_API_PROFILE_ID', ''),
            'client_id': os.environ.get('ADS_API_CLIENT_ID', ''),
            'client_secret': os.environ.get('ADS_API_CLIENT_SECRET', ''),
            'refresh_token': os.environ.get('ADS_API_REFRESH_TOKEN', ''),
        }
    
    @staticmethod
    def validate():
        missing = []
        for key in ['SP_API_REFRESH_TOKEN', 'SP_API_CLIENT_ID', 'SP_API_CLIENT_SECRET',
                     'ADS_API_PROFILE_ID', 'ADS_API_CLIENT_ID', 'ADS_API_CLIENT_SECRET', 'ADS_API_REFRESH_TOKEN']:
            if not os.environ.get(key):
                missing.append(key)
        return missing
