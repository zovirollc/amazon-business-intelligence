#!/usr/bin/env python3
"""
Comprehensive PPC Analysis Script for Amazon Advertising
Product: B0CR5D91N2 (Hand Sanitizer Wipe)
Date: 2026-03-02
Target ACOS: 30%
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
from statistics import mean, median

class PPCAnalyzer:
    def __init__(self, data_dir="/tmp/api_cache"):
        self.data_dir = data_dir
        self.date = "2026-03-02"
        self.target_acos = 30
        self.avg_price = 14.99
        self.min_spend_threshold = 5.0
        
        # Data containers
        self.search_terms = []
        self.keywords = []
        self.campaigns = []
        self.campaign_structure = {}
        self.placements = []
        
        # Analysis results
        self.analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "date": self.date,
            "product_id": "B0CR5D91N2",
            "target_acos": self.target_acos,
            "avg_price": self.avg_price,
            "search_term_classification": {},
            "keyword_performance_tiers": {},
            "campaign_health": {},
            "negative_keyword_candidates": [],
            "bid_optimization": {},
            "budget_recommendations": {},
            "summary_metrics": {}
        }
    
    def load_data(self):
        """Load all data files"""
        print("Loading data files...")
        
        # Load search terms
        with open(os.path.join(self.data_dir, f"search_terms_clean_{self.date}.json")) as f:
            data = json.load(f)
            self.search_terms = data.get("search_terms", [])
            print(f"  - Loaded {len(self.search_terms)} search terms")
        
        # Load keywords
        with open(os.path.join(self.data_dir, f"keyword_performance_{self.date}.json")) as f:
            data = json.load(f)
            self.keywords = data.get("keywords", [])
            print(f"  - Loaded {len(self.keywords)} keywords")
        
        # Load campaigns (this is a list)
        with open(os.path.join(self.data_dir, f"campaign_performance_{self.date}.json")) as f:
            data = json.load(f)
            self.campaigns = data if isinstance(data, list) else data.get("campaigns", [])
            print(f"  - Loaded {len(self.campaigns)} campaigns")
        
        # Load campaign structure
        with open(os.path.join(self.data_dir, f"campaign_structure_{self.date}.json")) as f:
            self.campaign_structure = json.load(f)
            num_campaigns = len(self.campaign_structure.get("campaigns", []))
            print(f"  - Loaded campaign structure with {num_campaigns} campaigns")
        
        # Load placements
        with open(os.path.join(self.data_dir, f"placement_performance_{self.date}.json")) as f:
            data = json.load(f)
            self.placements = data.get("placements", []) if isinstance(data, dict) else data
            print(f"  - Loaded {len(self.placements)} placement records")
    
    def classify_search_terms(self):
        """Classify search terms as winner/marginal/bleeder/wasted"""
        print("\nClassifying search terms...")
        
        winners = []
        marginal = []
        bleeders = []
        wasted = []
        
        for term in self.search_terms:
            search_term = term.get("search_term", "")
            spend = float(term.get("spend", 0))
            sales = float(term.get("sales", 0))
            acos = float(term.get("acos", 100))
            
            if spend == 0:
                continue
            
            if acos <= self.target_acos and sales > 0:
                classification = "winner"
                winners.append(term)
            elif acos <= (self.target_acos * 1.3) and sales > 0:
                classification = "marginal"
                marginal.append(term)
            elif sales == 0:
                classification = "wasted"
                wasted.append(term)
            else:
                classification = "bleeder"
                bleeders.append(term)
            
            self.analysis_results["search_term_classification"][search_term] = {
                "classification": classification,
                "spend": spend,
                "sales": sales,
                "acos": acos,
                "impressions": term.get("impressions", 0),
                "clicks": term.get("clicks", 0),
                "conversions": term.get("conversions", 0)
            }
        
        print(f"  - Winners (ACOS <= {self.target_acos}%): {len(winners)}")
        print(f"  - Marginal (ACOS <= {self.target_acos*1.3}%): {len(marginal)}")
        print(f"  - Bleeders (ACOS > {self.target_acos*1.3}%): {len(bleeders)}")
        print(f"  - Wasted (no sales): {len(wasted)}")
        
        return {
            "winners": winners,
            "marginal": marginal,
            "bleeders": bleeders,
            "wasted": wasted
        }
    
    def rank_keywords_by_performance(self):
        """Rank keywords into performance tiers based on ROI"""
        print("\nRanking keywords by performance...")
        
        tier_1 = []
        tier_2 = []
        tier_3 = []
        tier_4 = []
        negative_candidates = []
        
        for keyword in self.keywords:
            keyword_text = keyword.get("keyword", "")
            spend = float(keyword.get("spend", 0))
            sales = float(keyword.get("sales", 0))
            acos = float(keyword.get("acos", 100))
            bid = float(keyword.get("bid", 0))
            match_type = keyword.get("match_type", "EXACT")
            
            if spend == 0:
                continue
            
            roi = ((sales - spend) / spend * 100) if spend > 0 else 0
            
            # Determine tier based on ACOS and match type
            if acos <= self.target_acos * 0.8:
                tier = "tier_1_exact" if match_type == "EXACT" else "tier_1_phrase"
                tier_1.append((keyword, roi, acos))
            elif acos <= self.target_acos:
                tier = "tier_2_phrase" if match_type == "PHRASE" else "tier_2_broad"
                tier_2.append((keyword, roi, acos))
            elif acos <= self.target_acos * 1.5:
                tier = "tier_3_broad"
                tier_3.append((keyword, roi, acos))
            elif sales > 0:
                tier = "tier_4_monitor"
                tier_4.append((keyword, roi, acos))
            else:
                tier = "negative_candidate"
                negative_candidates.append(keyword)
            
            self.analysis_results["keyword_performance_tiers"][keyword_text] = {
                "tier": tier,
                "match_type": match_type,
                "spend": spend,
                "sales": sales,
                "acos": acos,
                "roi": roi,
                "bid": bid,
                "impressions": keyword.get("impressions", 0),
                "clicks": keyword.get("clicks", 0)
            }
        
        print(f"  - Tier 1 (High Performance): {len(tier_1)}")
        print(f"  - Tier 2 (Good Performance): {len(tier_2)}")
        print(f"  - Tier 3 (Monitor): {len(tier_3)}")
        print(f"  - Tier 4 (Marginal): {len(tier_4)}")
        print(f"  - Negative Candidates: {len(negative_candidates)}")
        
        return {
            "tier_1": tier_1,
            "tier_2": tier_2,
            "tier_3": tier_3,
            "tier_4": tier_4,
            "negative_candidates": negative_candidates
        }
    
    def assess_campaign_health(self):
        """Score each campaign by ACOS vs target"""
        print("\nAssessing campaign health...")
        
        campaign_scores = {}
        
        for campaign in self.campaigns:
            campaign_name = campaign.get("campaignName", "")
            cost = float(campaign.get("cost", 0))
            sales = float(campaign.get("sales7d", 0))
            
            if cost == 0:
                continue
            
            acos = (cost / sales * 100) if sales > 0 else 100
            
            # Calculate health score (100 = perfect, lower is worse)
            acos_variance = abs(acos - self.target_acos) / self.target_acos
            if acos <= self.target_acos:
                health_score = 100 - (acos_variance * 50)
            else:
                health_score = 100 - (acos_variance * 100)
            
            health_score = max(0, min(100, health_score))
            
            # Determine status
            if acos <= self.target_acos * 0.9:
                status = "over_performing"
            elif acos <= self.target_acos * 1.1:
                status = "on_target"
            elif acos <= self.target_acos * 1.3:
                status = "under_performing"
            else:
                status = "critical"
            
            campaign_scores[campaign_name] = {
                "status": status,
                "health_score": round(health_score, 2),
                "spend": cost,
                "sales": sales,
                "acos": round(acos, 2),
                "target_acos": self.target_acos,
                "acos_variance": round(acos_variance * 100, 2),
                "impressions": campaign.get("impressions", 0),
                "clicks": campaign.get("clicks", 0),
                "conversions": campaign.get("purchases7d", 0)
            }
        
        self.analysis_results["campaign_health"] = campaign_scores
        
        statuses = [cs["status"] for cs in campaign_scores.values()]
        print(f"  - Over-performing: {statuses.count('over_performing')}")
        print(f"  - On-target: {statuses.count('on_target')}")
        print(f"  - Under-performing: {statuses.count('under_performing')}")
        print(f"  - Critical: {statuses.count('critical')}")
        
        return campaign_scores
    
    def find_negative_keyword_candidates(self):
        """Find search terms with spend > $5 and 0 sales"""
        print("\nFinding negative keyword candidates...")
        
        candidates = []
        
        for term in self.search_terms:
            spend = float(term.get("spend", 0))
            sales = float(term.get("sales", 0))
            
            if spend >= self.min_spend_threshold and sales == 0:
                candidates.append({
                    "search_term": term.get("search_term", ""),
                    "spend": spend,
                    "impressions": term.get("impressions", 0),
                    "clicks": term.get("clicks", 0),
                    "ad_group": term.get("ad_group", ""),
                    "match_type": term.get("match_type", ""),
                    "priority": "high" if spend >= 20 else "medium"
                })
        
        # Sort by spend descending
        candidates.sort(key=lambda x: x["spend"], reverse=True)
        self.analysis_results["negative_keyword_candidates"] = candidates[:50]  # Top 50
        
        print(f"  - Found {len(candidates)} candidates with spend >= ${self.min_spend_threshold}")
        print(f"  - Reporting top 50 by spend")
        
        return candidates
    
    def optimize_bids(self):
        """Calculate optimal bid for each keyword"""
        print("\nOptimizing bids...")
        
        bid_recommendations = {}
        
        for keyword in self.keywords:
            keyword_text = keyword.get("keyword", "")
            cpc = float(keyword.get("cpc", 0))
            cvr = float(keyword.get("cvr", 0))
            conversions = float(keyword.get("orders", 0))
            clicks = float(keyword.get("clicks", 0))
            
            if clicks == 0 or conversions == 0:
                continue
            
            # Calculate CVR if not provided or convert from percentage
            if cvr == 0 and clicks > 0:
                cvr = conversions / clicks
            else:
                # cvr appears to be in percentage format (14.54 = 14.54%)
                cvr = cvr / 100 if cvr > 1 else cvr
            
            # Optimal bid = (target_acos/100) * avg_price * cvr
            if cvr > 0:
                optimal_bid = (self.target_acos / 100) * self.avg_price * cvr
                current_bid = float(keyword.get("bid", 0))
                
                # Calculate recommendation
                if current_bid == 0:
                    recommendation = "increase"
                    change_percent = 0
                else:
                    change_percent = ((optimal_bid - current_bid) / current_bid) * 100
                    if change_percent > 5:
                        recommendation = "increase"
                    elif change_percent < -5:
                        recommendation = "decrease"
                    else:
                        recommendation = "maintain"
                
                bid_recommendations[keyword_text] = {
                    "current_bid": current_bid,
                    "optimal_bid": round(optimal_bid, 2),
                    "change_percent": round(change_percent, 2),
                    "recommendation": recommendation,
                    "cpc": cpc,
                    "cvr": round(cvr, 4),
                    "rationale": f"Based on target ACOS of {self.target_acos}% and avg price ${self.avg_price}"
                }
        
        self.analysis_results["bid_optimization"] = bid_recommendations
        
        increases = sum(1 for r in bid_recommendations.values() if r["recommendation"] == "increase")
        decreases = sum(1 for r in bid_recommendations.values() if r["recommendation"] == "decrease")
        maintains = sum(1 for r in bid_recommendations.values() if r["recommendation"] == "maintain")
        
        print(f"  - Bid increase recommendations: {increases}")
        print(f"  - Bid decrease recommendations: {decreases}")
        print(f"  - Bid maintain recommendations: {maintains}")
        
        return bid_recommendations
    
    def recommend_budget_redistribution(self, classifications):
        """Recommend budget redistribution from bleeders to winners"""
        print("\nRecommending budget redistribution...")
        
        winners = classifications["winners"]
        bleeders = classifications["bleeders"]
        
        total_bleeder_spend = sum(float(b.get("spend", 0)) for b in bleeders)
        total_winner_spend = sum(float(w.get("spend", 0)) for w in winners)
        total_winner_sales = sum(float(w.get("sales", 0)) for w in winners)
        
        # Calculate how much to reallocate
        reallocate_amount = min(total_bleeder_spend * 0.5, total_bleeder_spend / 3)
        
        # Project impact
        if total_winner_spend > 0:
            projected_sales = total_winner_sales + (reallocate_amount * (total_winner_sales / total_winner_spend))
        else:
            projected_sales = total_winner_sales
        
        recommendations = {
            "budget_reallocation": {
                "from_bleeders": round(reallocate_amount, 2),
                "to_winners": round(reallocate_amount, 2),
                "current_bleeder_spend": round(total_bleeder_spend, 2),
                "current_winner_spend": round(total_winner_spend, 2),
                "current_winner_sales": round(total_winner_sales, 2)
            },
            "projected_impact": {
                "additional_sales": round(reallocate_amount * (total_winner_sales / total_winner_spend) if total_winner_spend > 0 else 0, 2),
                "reduced_wasted_spend": round(reallocate_amount, 2),
                "estimated_acos_improvement": f"{self.target_acos - 2}%" if (self.target_acos - 2) > 0 else "At Target"
            },
            "action_items": [
                f"Reduce spend on bottom {len(bleeders)} bleeders by 50%",
                f"Allocate ${round(reallocate_amount, 2)} to top {min(10, len(winners))} winners",
                "Monitor closely for 7 days after reallocation",
                "Scale winners with proven ROI > 50%"
            ]
        }
        
        self.analysis_results["budget_recommendations"] = recommendations
        
        print(f"  - Recommended reallocation: ${reallocate_amount:.2f}")
        print(f"  - From {len(bleeders)} bleeders to {len(winners)} winners")
        print(f"  - Projected additional sales: ${recommendations['projected_impact']['additional_sales']:.2f}")
        
        return recommendations
    
    def calculate_summary_metrics(self):
        """Calculate summary metrics"""
        print("\nCalculating summary metrics...")
        
        total_spend = sum(float(t.get("spend", 0)) for t in self.search_terms)
        total_sales = sum(float(t.get("sales", 0)) for t in self.search_terms)
        overall_acos = (total_spend / total_sales * 100) if total_sales > 0 else 0
        overall_roas = (total_sales / total_spend) if total_spend > 0 else 0
        
        # Count classifications
        classifications = self.analysis_results["search_term_classification"]
        winners_count = sum(1 for c in classifications.values() if c["classification"] == "winner")
        marginal_count = sum(1 for c in classifications.values() if c["classification"] == "marginal")
        bleeder_count = sum(1 for c in classifications.values() if c["classification"] == "bleeder")
        wasted_count = sum(1 for c in classifications.values() if c["classification"] == "wasted")
        
        # Campaign health
        campaign_health = self.analysis_results["campaign_health"]
        on_target_campaigns = sum(1 for c in campaign_health.values() if c["status"] == "on_target")
        
        summary = {
            "total_search_terms": len(self.search_terms),
            "total_keywords": len(self.keywords),
            "total_campaigns": len(self.campaigns),
            "total_spend": round(total_spend, 2),
            "total_sales": round(total_sales, 2),
            "overall_acos": round(overall_acos, 2),
            "overall_roas": round(overall_roas, 2),
            "target_acos": self.target_acos,
            "performance_vs_target": f"{round(((self.target_acos - overall_acos) / self.target_acos * 100), 1)}%" if overall_acos != 0 else "N/A",
            "search_term_distribution": {
                "winners": winners_count,
                "marginal": marginal_count,
                "bleeders": bleeder_count,
                "wasted": wasted_count
            },
            "campaigns_on_target": on_target_campaigns,
            "negative_candidates_found": len(self.analysis_results["negative_keyword_candidates"])
        }
        
        self.analysis_results["summary_metrics"] = summary
        
        return summary
    
    def run(self):
        """Run complete analysis"""
        print("=" * 70)
        print("PPC ANALYSIS REPORT - Amazon Advertising")
        print("=" * 70)
        print(f"Date: {self.date}")
        print(f"Product: B0CR5D91N2 (Hand Sanitizer Wipe)")
        print(f"Target ACOS: {self.target_acos}%")
        print("=" * 70)
        
        self.load_data()
        classifications = self.classify_search_terms()
        tiers = self.rank_keywords_by_performance()
        campaign_health = self.assess_campaign_health()
        negative_keywords = self.find_negative_keyword_candidates()
        bid_opts = self.optimize_bids()
        budget_recs = self.recommend_budget_redistribution(classifications)
        summary = self.calculate_summary_metrics()
        
        return summary
    
    def save_results(self, output_path):
        """Save analysis results to JSON"""
        print(f"\nSaving results to {output_path}...")
        with open(output_path, 'w') as f:
            json.dump(self.analysis_results, f, indent=2)
        print("Results saved successfully!")
    
    def print_summary(self):
        """Print a clean summary of findings"""
        summary = self.analysis_results["summary_metrics"]
        
        print("\n" + "=" * 70)
        print("EXECUTIVE SUMMARY")
        print("=" * 70)
        
        print(f"\nOVERALL PERFORMANCE:")
        print(f"  Total Spend:              ${summary['total_spend']:,.2f}")
        print(f"  Total Sales:              ${summary['total_sales']:,.2f}")
        print(f"  Overall ACOS:             {summary['overall_acos']:.2f}%")
        print(f"  Overall ROAS:             {summary['overall_roas']:.2f}x")
        print(f"  Performance vs Target:    {summary['performance_vs_target']}")
        
        print(f"\nSEARCH TERM CLASSIFICATION:")
        print(f"  Winners (ACOS <= {self.target_acos}%):           {summary['search_term_distribution']['winners']:>4} terms")
        print(f"  Marginal (ACOS <= {self.target_acos*1.3:.0f}%):        {summary['search_term_distribution']['marginal']:>4} terms")
        print(f"  Bleeders (ACOS > {self.target_acos*1.3:.0f}%):        {summary['search_term_distribution']['bleeders']:>4} terms")
        print(f"  Wasted (No Sales):        {summary['search_term_distribution']['wasted']:>4} terms")
        
        print(f"\nCAMPAIGN HEALTH:")
        print(f"  Total Campaigns:          {summary['total_campaigns']:>4}")
        print(f"  On Target:                {summary['campaigns_on_target']:>4}")
        
        print(f"\nKEY OPPORTUNITIES:")
        print(f"  Negative Keyword Candidates: {summary['negative_candidates_found']}")
        print(f"  Keywords to Optimize:        {len(self.analysis_results['bid_optimization'])}")
        
        print(f"\nBUDGET REALLOCATION:")
        budg = self.analysis_results["budget_recommendations"]
        print(f"  Recommended Move:         ${budg['budget_reallocation']['from_bleeders']:,.2f}")
        print(f"  Projected Sales Impact:   ${budg['projected_impact']['additional_sales']:,.2f}")
        
        print("\n" + "=" * 70)
        print("KEY RECOMMENDATIONS:")
        print("=" * 70)
        budg_recs = budg.get("action_items", [])
        for i, rec in enumerate(budg_recs, 1):
            print(f"{i}. {rec}")
        
        # Top winners
        print(f"\nTOP 5 WINNING SEARCH TERMS (by spend):")
        winners = [t for t in self.search_terms if self.analysis_results["search_term_classification"].get(t.get("search_term", ""), {}).get("classification") == "winner"]
        winners.sort(key=lambda x: float(x.get("spend", 0)), reverse=True)
        for i, term in enumerate(winners[:5], 1):
            print(f"{i}. {term['search_term']}: ${term.get('spend', 0):.2f} spend, {term.get('acos', 0):.1f}% ACOS")
        
        # Top bleeders
        print(f"\nTOP 5 BLEEDING SEARCH TERMS (by spend):")
        bleeders = [t for t in self.search_terms if self.analysis_results["search_term_classification"].get(t.get("search_term", ""), {}).get("classification") == "bleeder"]
        bleeders.sort(key=lambda x: float(x.get("spend", 0)), reverse=True)
        for i, term in enumerate(bleeders[:5], 1):
            print(f"{i}. {term['search_term']}: ${term.get('spend', 0):.2f} spend, {term.get('acos', 0):.1f}% ACOS")
        
        print("\n" + "=" * 70)


if __name__ == "__main__":
    analyzer = PPCAnalyzer()
    analyzer.run()
    
    output_path = "/tmp/api_cache/ppc_analysis_2026-03-02.json"
    analyzer.save_results(output_path)
    analyzer.print_summary()
    
    print("\nAnalysis complete!")
