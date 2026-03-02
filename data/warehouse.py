#!/usr/bin/env python3
"""
Data Warehouse
Manages three-tier data storage: raw → processed → summaries.
Provides read/write with automatic path resolution and date-stamping.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class DataWarehouse:
    """Three-tier data warehouse for Amazon business intelligence."""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw"
        self.processed_dir = self.base_dir / "processed"
        self.summaries_dir = self.base_dir / "summaries"
        self.snapshots_dir = self.base_dir / "snapshots"
        
        # Ensure directories exist
        for d in [self.raw_dir, self.processed_dir, self.summaries_dir, self.snapshots_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    # ─── Raw Data ────────────────────────────────────────────────────────
    
    def save_raw(self, brand: str, asin: str, data_type: str, data: Any, date: str = None) -> Path:
        """Save raw API data. Path: raw/{brand}/{asin}/{data_type}_{date}.json"""
        date = date or datetime.now().strftime('%Y-%m-%d')
        path = self.raw_dir / brand / asin
        path.mkdir(parents=True, exist_ok=True)
        
        filepath = path / f"{data_type}_{date}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    
    def load_raw(self, brand: str, asin: str, data_type: str, date: str = None) -> Optional[dict]:
        """Load raw data. Returns None if not found."""
        date = date or datetime.now().strftime('%Y-%m-%d')
        filepath = self.raw_dir / brand / asin / f"{data_type}_{date}.json"
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return None
    
    # ─── Processed Data ──────────────────────────────────────────────────
    
    def save_processed(self, category: str, name: str, data: Any, date: str = None) -> Path:
        """Save processed data. Path: processed/{category}/{name}_{date}.json"""
        date = date or datetime.now().strftime('%Y-%m-%d')
        path = self.processed_dir / category
        path.mkdir(parents=True, exist_ok=True)
        
        filepath = path / f"{name}_{date}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    
    def load_processed(self, category: str, name: str, date: str = None) -> Optional[dict]:
        """Load processed data."""
        date = date or datetime.now().strftime('%Y-%m-%d')
        filepath = self.processed_dir / category / f"{name}_{date}.json"
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return None
    
    def load_latest_processed(self, category: str, name_prefix: str) -> Optional[dict]:
        """Load the most recent processed file matching a name prefix."""
        path = self.processed_dir / category
        if not path.exists():
            return None
        files = sorted(path.glob(f"{name_prefix}_*.json"), reverse=True)
        if files:
            with open(files[0]) as f:
                return json.load(f)
        return None
    
    # ─── Summaries (LLM-ready) ──────────────────────────────────────────
    
    def save_summary(self, name: str, text: str, date: str = None) -> Path:
        """Save token-optimized summary. Path: summaries/{name}_{date}.txt"""
        date = date or datetime.now().strftime('%Y%m%d')
        filepath = self.summaries_dir / f"{name}_{date}.txt"
        with open(filepath, 'w') as f:
            f.write(text)
        return filepath
    
    def load_summary(self, name: str, date: str = None) -> Optional[str]:
        """Load summary text."""
        date = date or datetime.now().strftime('%Y%m%d')
        filepath = self.summaries_dir / f"{name}_{date}.txt"
        if filepath.exists():
            with open(filepath) as f:
                return f.read()
        return None
    
    def load_all_summaries(self, date: str = None) -> Dict[str, str]:
        """Load all summaries for a given date. Returns {name: text}."""
        date = date or datetime.now().strftime('%Y%m%d')
        summaries = {}
        for f in self.summaries_dir.glob(f"*_{date}.txt"):
            name = f.stem.rsplit('_', 1)[0]
            summaries[name] = f.read_text()
        return summaries
    
    # ─── Snapshots ───────────────────────────────────────────────────────
    
    def save_snapshot(self, snapshot_type: str, data: Any, date: str = None) -> Path:
        """Save daily/weekly snapshot for trending."""
        date = date or datetime.now().strftime('%Y-%m-%d')
        filepath = self.snapshots_dir / f"snapshot_{snapshot_type}_{date}.json"
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    
    def load_snapshots(self, snapshot_type: str, limit: int = 30) -> list:
        """Load recent snapshots for trending analysis."""
        files = sorted(self.snapshots_dir.glob(f"snapshot_{snapshot_type}_*.json"), reverse=True)
        snapshots = []
        for f in files[:limit]:
            with open(f) as fh:
                snapshots.append(json.load(fh))
        return snapshots
    
    # ─── Utility ─────────────────────────────────────────────────────────
    
    def list_dates(self, category: str = "processed") -> list:
        """List all dates that have data."""
        base = getattr(self, f"{category}_dir", self.processed_dir)
        dates = set()
        for f in base.rglob("*.json"):
            # Extract date from filename pattern _YYYY-MM-DD.json
            stem = f.stem
            parts = stem.rsplit('_', 1)
            if len(parts) == 2 and len(parts[1]) == 10:
                dates.add(parts[1])
        return sorted(dates, reverse=True)
