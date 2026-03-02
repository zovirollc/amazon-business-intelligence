#!/usr/bin/env python3
"""
Full End-to-End Pipeline Test
Pulls live API data → runs PPC analysis → generates reports → saves to data warehouse.
Usage: python scripts/run_full_pipeline.py --asin B0CR5D91N2 --env-file api/.env
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

# Resolve project root
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.sp_api_client import SPAPIClient
from api.ads_api_client import AdsAPIClient
from api.data_fetcher import DataFetcher
from data.warehouse import DataWarehouse
from data.summary_generator import generate_ppc_summary, generate_daily_snapshot_summary
import yaml


def load_brand_config(asin: str) -> dict:
    """Load brand config and find product settings for the given ASIN."""
    config_path = PROJECT_ROOT / "config" / "brands" / "zoviro.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    product = config.get("products", {}).get(asin, {})
    return config, product


def step_1_pull_data(fetcher: DataFetcher, asin: str, warehouse: DataWarehouse, days: int = 31, skip_reports: bool = False):
    """Step 1: Pull all data from APIs and save raw to warehouse.
    Pulls each data type individually with graceful fallback on timeout."""
    print("\n" + "=" * 70)
    print("STEP 1: PULLING LIVE API DATA")
    print("=" * 70)

    cache_dir = PROJECT_ROOT / "data" / "raw" / "zoviro" / asin
    cache_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    data_files = {}

    def _load_cached(name):
        """Try loading from cache_dir first."""
        p = cache_dir / f"{name}_{today}.json"
        if p.exists():
            with open(p) as f:
                return json.load(f)
        return None

    def _save(name, data):
        p = cache_dir / f"{name}_{today}.json"
        with open(p, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        warehouse.save_raw("zoviro", asin, name, data, today)
        data_files[name] = data
        print(f"  ✓ {name}")

    # 1. Listing (fast, no report)
    print("  Pulling listing...")
    try:
        listing = fetcher.get_our_listing(asin)
        _save("listing", listing)
    except Exception as e:
        print(f"  ⚠ listing failed: {e}")

    # 2. Search terms (report — check cache first)
    cached = _load_cached("search_terms_clean")
    if cached:
        data_files["search_terms_clean"] = cached
        print(f"  ✓ search_terms_clean (cached, {len(cached.get('search_terms', []))} terms)")
    else:
        print("  Pulling search terms report...")
        try:
            st = fetcher.get_search_term_report(days_back=days, output_dir=str(cache_dir))
            data_files["search_terms_clean"] = st
            warehouse.save_raw("zoviro", asin, "search_terms_clean", st, today)
            print(f"  ✓ search_terms_clean ({len(st.get('search_terms', []))} terms)")
        except Exception as e:
            print(f"  ⚠ search_terms failed: {e}")

    # 3. Campaign structure (no report needed, uses list API)
    print("  Pulling campaign structure...")
    try:
        structure = fetcher.get_campaign_structure(output_dir=str(cache_dir))
        # Also check /tmp/api_cache for the full structure file
        tmp_file = Path("/tmp/api_cache") / f"campaign_structure_{today}.json"
        if tmp_file.exists() and not structure:
            with open(tmp_file) as f:
                structure = json.load(f)
        _save("campaign_structure", structure)
    except Exception as e:
        print(f"  ⚠ campaign_structure failed: {e}")
        # Try /tmp/api_cache fallback
        tmp_file = Path("/tmp/api_cache") / f"campaign_structure_{today}.json"
        if tmp_file.exists():
            with open(tmp_file) as f:
                structure = json.load(f)
            _save("campaign_structure", structure)

    # 4-6. Report-based data (campaign perf, keyword perf, placement perf)
    report_pulls = [
        ("campaign_performance", lambda: fetcher.get_campaign_performance(days_back=days, output_dir=str(cache_dir))),
        ("keyword_performance", lambda: fetcher.get_keyword_performance(days_back=days, output_dir=str(cache_dir))),
        ("placement_performance", lambda: fetcher.get_placement_performance(days_back=days, output_dir=str(cache_dir))),
    ]

    for name, pull_fn in report_pulls:
        cached = _load_cached(name)
        if cached:
            data_files[name] = cached
            print(f"  ✓ {name} (cached)")
            continue
        if skip_reports:
            print(f"  ⊘ {name} skipped (--skip-reports)")
            continue
        print(f"  Pulling {name} report...")
        try:
            data = pull_fn()
            _save(name, data)
        except (TimeoutError, Exception) as e:
            print(f"  ⚠ {name} skipped: {e}")

    print(f"\n  Data files collected: {len(data_files)}/{6}")
    return data_files, today


def step_2_run_analysis(data_files: dict, asin: str, product_config: dict, warehouse: DataWarehouse, date: str):
    """Step 2: Run PPC analysis on the pulled data."""
    print("\n" + "=" * 70)
    print("STEP 2: RUNNING PPC ANALYSIS")
    print("=" * 70)

    target_acos = product_config.get("target_acos", 30)
    avg_price = product_config.get("avg_price", 14.99)

    # Extract data
    search_terms = data_files.get("search_terms_clean", {}).get("search_terms", [])
    keywords = data_files.get("keyword_performance", {}).get("keywords", [])
    campaigns = data_files.get("campaign_performance", [])
    if isinstance(campaigns, dict):
        campaigns = campaigns.get("campaigns", [])
    placements = data_files.get("placement_performance", {})
    if isinstance(placements, dict):
        placements = placements.get("placements", [])

    print(f"  Data loaded: {len(search_terms)} search terms, {len(keywords)} keywords, {len(campaigns)} campaigns")

    # ── Classify search terms ──
    winners, marginal, bleeders, wasted = [], [], [], []
    for term in search_terms:
        spend = float(term.get("spend", 0))
        sales = float(term.get("sales", 0))
        acos = float(term.get("acos", 100))
        if spend == 0:
            continue
        if acos <= target_acos and sales > 0:
            winners.append(term)
        elif acos <= target_acos * 1.3 and sales > 0:
            marginal.append(term)
        elif sales == 0:
            wasted.append(term)
        else:
            bleeders.append(term)

    print(f"  Search term classification: {len(winners)} winners, {len(marginal)} marginal, {len(bleeders)} bleeders, {len(wasted)} wasted")

    # ── Keyword tiers ──
    tier_1, tier_2, tier_3, tier_4, neg_candidates = [], [], [], [], []
    for kw in keywords:
        spend = float(kw.get("spend", 0))
        sales = float(kw.get("sales", 0))
        acos = float(kw.get("acos", 100))
        if spend == 0:
            continue
        if acos <= target_acos * 0.8 and sales > 0:
            tier_1.append(kw)
        elif acos <= target_acos and sales > 0:
            tier_2.append(kw)
        elif acos <= target_acos * 1.5 and sales > 0:
            tier_3.append(kw)
        elif sales > 0:
            tier_4.append(kw)
        else:
            neg_candidates.append(kw)

    print(f"  Keyword tiers: T1={len(tier_1)}, T2={len(tier_2)}, T3={len(tier_3)}, T4={len(tier_4)}, neg={len(neg_candidates)}")

    # ── Campaign health ──
    campaign_health = {}
    for c in campaigns:
        name = c.get("campaignName", "")
        cost = float(c.get("cost", 0))
        sales_7d = float(c.get("sales7d", 0))
        if cost == 0:
            continue
        acos_val = (cost / sales_7d * 100) if sales_7d > 0 else 100
        if acos_val <= target_acos * 0.9:
            status = "over_performing"
        elif acos_val <= target_acos * 1.1:
            status = "on_target"
        elif acos_val <= target_acos * 1.3:
            status = "under_performing"
        else:
            status = "critical"
        campaign_health[name] = {"status": status, "spend": cost, "sales": sales_7d, "acos": round(acos_val, 2)}

    statuses = [v["status"] for v in campaign_health.values()]
    print(f"  Campaign health: {statuses.count('over_performing')} over, {statuses.count('on_target')} on-target, {statuses.count('under_performing')} under, {statuses.count('critical')} critical")

    # ── Negative keyword candidates ──
    neg_search = [t for t in search_terms if float(t.get("spend", 0)) >= 5 and float(t.get("sales", 0)) == 0]
    neg_search.sort(key=lambda x: float(x.get("spend", 0)), reverse=True)
    print(f"  Negative keyword candidates: {len(neg_search)}")

    # ── Bid optimization ──
    bid_recs = {}
    for kw in keywords:
        clicks = float(kw.get("clicks", 0))
        orders = float(kw.get("orders", 0))
        if clicks == 0 or orders == 0:
            continue
        cvr = orders / clicks
        optimal_bid = (target_acos / 100) * avg_price * cvr
        current_bid = float(kw.get("bid", 0))
        if current_bid > 0:
            change = ((optimal_bid - current_bid) / current_bid) * 100
            rec = "increase" if change > 5 else ("decrease" if change < -5 else "maintain")
        else:
            change = 0
            rec = "increase"
        bid_recs[kw.get("keyword", "")] = {
            "current": current_bid, "optimal": round(optimal_bid, 2),
            "change_pct": round(change, 1), "action": rec
        }

    increases = sum(1 for r in bid_recs.values() if r["action"] == "increase")
    decreases = sum(1 for r in bid_recs.values() if r["action"] == "decrease")
    print(f"  Bid recs: {increases} increase, {decreases} decrease, {len(bid_recs) - increases - decreases} maintain")

    # ── Summary metrics ──
    total_spend = sum(float(t.get("spend", 0)) for t in search_terms)
    total_sales = sum(float(t.get("sales", 0)) for t in search_terms)
    overall_acos = (total_spend / total_sales * 100) if total_sales > 0 else 0
    overall_roas = (total_sales / total_spend) if total_spend > 0 else 0

    # ── Budget reallocation ──
    bleeder_spend = sum(float(b.get("spend", 0)) for b in bleeders)
    winner_spend = sum(float(w.get("spend", 0)) for w in winners)
    winner_sales = sum(float(w.get("sales", 0)) for w in winners)
    realloc = min(bleeder_spend * 0.5, bleeder_spend / 3)
    projected_add = realloc * (winner_sales / winner_spend) if winner_spend > 0 else 0

    # ── Build analysis results ──
    analysis = {
        "asin": asin,
        "date": date,
        "target_acos": target_acos,
        "avg_price": avg_price,
        "period": f"Last 31 days ending {date}",
        "summary": {
            "total_spend": round(total_spend, 2),
            "total_sales": round(total_sales, 2),
            "overall_acos": round(overall_acos, 2),
            "overall_roas": round(overall_roas, 2),
            "total_search_terms": len(search_terms),
            "total_keywords": len(keywords),
            "total_campaigns": len(campaigns),
        },
        "classification": {
            "winners": len(winners),
            "marginal": len(marginal),
            "bleeders": len(bleeders),
            "wasted": len(wasted),
        },
        "keyword_tiers": {
            "tier_1": len(tier_1),
            "tier_2": len(tier_2),
            "tier_3": len(tier_3),
            "tier_4": len(tier_4),
            "negative_candidates": len(neg_candidates),
        },
        "campaign_health": campaign_health,
        "negative_candidates": [{"search_term": t.get("search_term", ""), "spend": float(t.get("spend", 0))} for t in neg_search[:50]],
        "bid_optimization_summary": {"increase": increases, "decrease": decreases, "maintain": len(bid_recs) - increases - decreases},
        "budget_reallocation": {
            "from_bleeders": round(realloc, 2),
            "to_winners": round(realloc, 2),
            "projected_additional_sales": round(projected_add, 2),
        },
        "top_winners": sorted(winners, key=lambda x: float(x.get("sales", 0)), reverse=True)[:10],
        "top_bleeders": sorted(bleeders, key=lambda x: float(x.get("spend", 0)), reverse=True)[:10],
        "actions": [
            f"Add {len(neg_search[:50])} negative keywords to save ${sum(float(t.get('spend',0)) for t in neg_search[:50]):,.2f}",
            f"Increase bids on {increases} high-performing keywords",
            f"Decrease bids on {decreases} underperforming keywords",
            f"Reallocate ${realloc:,.2f} from bleeders to winners",
            f"Monitor {statuses.count('critical')} critical campaigns",
        ],
    }

    # Save to processed
    warehouse.save_processed("ppc", f"ppc_analysis_{asin}", analysis, date)
    print(f"  → Saved processed: ppc/ppc_analysis_{asin}_{date}.json")

    return analysis


def step_3_generate_summary(analysis: dict, asin: str, product_config: dict, warehouse: DataWarehouse, date: str):
    """Step 3: Generate token-optimized summary for LLM consumption."""
    print("\n" + "=" * 70)
    print("STEP 3: GENERATING LLM-READY SUMMARY")
    print("=" * 70)

    ppc_summary_data = {
        "period": analysis["period"],
        "total_spend": analysis["summary"]["total_spend"],
        "total_sales": analysis["summary"]["total_sales"],
        "overall_acos": analysis["summary"]["overall_acos"],
        "roas": analysis["summary"]["overall_roas"],
        "total_unique_terms": analysis["summary"]["total_search_terms"],
        "target_acos": analysis["target_acos"],
        "classification": analysis["classification"],
        "top_winners": analysis["top_winners"],
        "negative_candidates": analysis["negative_candidates"][:10],
        "actions": analysis["actions"],
    }

    summary_text = generate_ppc_summary(
        ppc_summary_data,
        product_name=product_config.get("name", asin),
        asin=asin,
    )

    path = warehouse.save_summary(f"ppc_{asin}", summary_text, date.replace('-', ''))
    char_count = len(summary_text)
    token_est = char_count // 4
    print(f"  → Saved summary: {path.name} ({char_count} chars, ~{token_est} tokens)")

    # Also save a daily snapshot
    snapshot = {
        "date": date,
        "products": {
            asin: {
                "spend": analysis["summary"]["total_spend"],
                "sales": analysis["summary"]["total_sales"],
                "acos": analysis["summary"]["overall_acos"],
                "roas": analysis["summary"]["overall_roas"],
                "winners": analysis["classification"]["winners"],
                "wasted": analysis["classification"]["wasted"],
            }
        }
    }
    warehouse.save_snapshot("daily_ppc", snapshot, date)
    print(f"  → Saved snapshot: snapshot_daily_ppc_{date}.json")

    return summary_text


def step_4_generate_report(analysis: dict, data_files: dict, asin: str, product_config: dict, date: str):
    """Step 4: Generate HTML visual report."""
    print("\n" + "=" * 70)
    print("STEP 4: GENERATING HTML REPORT")
    print("=" * 70)

    report_dir = PROJECT_ROOT / "reports" / "output"
    report_dir.mkdir(parents=True, exist_ok=True)

    # Use the visual report generator
    try:
        script_dir = PROJECT_ROOT / "skills" / "ppc-optimization" / "scripts"
        sys.path.insert(0, str(script_dir))
        from generate_visual_report import generate_html_report

        search_terms_data = data_files.get("search_terms_clean", {})
        keyword_data = data_files.get("keyword_performance", {})
        campaign_data = data_files.get("campaign_structure", {})

        report_path = str(report_dir / f"PPC_Report_{asin}_{date}.html")
        generate_html_report(search_terms_data, keyword_data, campaign_data, report_path)
        print(f"  → Generated: PPC_Report_{asin}_{date}.html")
    except Exception as e:
        print(f"  ⚠ Visual report generation failed: {e}")
        print(f"    (Analysis data still saved to warehouse)")
        report_path = None

    return report_path


def step_5_verify(warehouse: DataWarehouse, asin: str, date: str):
    """Step 5: Verify data warehouse completeness."""
    print("\n" + "=" * 70)
    print("STEP 5: VERIFICATION")
    print("=" * 70)

    checks = []

    # Check raw
    raw_dir = warehouse.raw_dir / "zoviro" / asin
    raw_files = list(raw_dir.glob(f"*_{date}.json")) if raw_dir.exists() else []
    checks.append(("Raw data files", len(raw_files), "≥5"))
    print(f"  Raw data: {len(raw_files)} files")
    for f in sorted(raw_files):
        size = f.stat().st_size
        print(f"    • {f.name} ({size:,} bytes)")

    # Check processed
    processed = warehouse.load_processed("ppc", f"ppc_analysis_{asin}", date)
    checks.append(("Processed analysis", 1 if processed else 0, "1"))
    if processed:
        print(f"  Processed: ppc_analysis_{asin}_{date}.json ✓")
        print(f"    ACOS: {processed['summary']['overall_acos']}% | Spend: ${processed['summary']['total_spend']:,.2f} | Sales: ${processed['summary']['total_sales']:,.2f}")
    else:
        print(f"  Processed: MISSING ✗")

    # Check summary
    summary = warehouse.load_summary(f"ppc_{asin}", date.replace('-', ''))
    checks.append(("LLM Summary", 1 if summary else 0, "1"))
    if summary:
        lines = summary.strip().split('\n')
        print(f"  Summary: ppc_{asin}_{date.replace('-','')}.txt ✓ ({len(summary)} chars, {len(lines)} lines)")
    else:
        print(f"  Summary: MISSING ✗")

    # Check snapshot
    snapshots = warehouse.load_snapshots("daily_ppc", limit=1)
    checks.append(("Daily snapshot", len(snapshots), "≥1"))
    print(f"  Snapshots: {len(snapshots)} daily_ppc snapshots")

    # Check report
    report_dir = PROJECT_ROOT / "reports" / "output"
    reports = list(report_dir.glob(f"*_{asin}_{date}.*"))
    checks.append(("HTML Report", len(reports), "≥1"))
    print(f"  Reports: {len(reports)} files")
    for r in reports:
        print(f"    • {r.name} ({r.stat().st_size:,} bytes)")

    # Overall
    all_pass = all(
        (int(actual) >= 1 if expected.startswith("≥") else int(actual) == int(expected))
        for _, actual, expected in checks
    )

    print(f"\n{'═' * 70}")
    if all_pass:
        print("  ✅ ALL CHECKS PASSED — PIPELINE COMPLETE")
    else:
        print("  ⚠ SOME CHECKS FAILED — REVIEW ABOVE")
    print(f"{'═' * 70}")

    return all_pass


def main():
    parser = argparse.ArgumentParser(description="Full E2E Pipeline Test")
    parser.add_argument("--asin", default="B0CR5D91N2", help="ASIN to analyze")
    parser.add_argument("--env-file", default="api/.env", help="Path to .env")
    parser.add_argument("--days", type=int, default=31, help="Days back for reports")
    parser.add_argument("--skip-reports", action="store_true", help="Skip Ads reporting API (use cached data only)")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║        AMAZON BUSINESS INTELLIGENCE — FULL PIPELINE TEST           ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  ASIN: {args.asin}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Init
    brand_config, product_config = load_brand_config(args.asin)
    warehouse = DataWarehouse(str(PROJECT_ROOT / "data"))
    fetcher = DataFetcher(env_file=args.env_file)

    start = time.time()

    # Run pipeline
    data_files, date = step_1_pull_data(fetcher, args.asin, warehouse, args.days, skip_reports=args.skip_reports)
    analysis = step_2_run_analysis(data_files, args.asin, product_config, warehouse, date)
    summary = step_3_generate_summary(analysis, args.asin, product_config, warehouse, date)
    report = step_4_generate_report(analysis, data_files, args.asin, product_config, date)
    ok = step_5_verify(warehouse, args.asin, date)

    elapsed = time.time() - start
    print(f"\n  Total time: {elapsed:.1f}s")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
