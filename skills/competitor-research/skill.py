#!/usr/bin/env python3
"""Competitor Research Skill — discovers and analyzes Amazon competitors."""

import time
from datetime import datetime
from skills.base import BaseSkill, SkillInput, SkillOutput


class CompetitorResearchSkill(BaseSkill):
    
    def __init__(self, config: dict):
        super().__init__("competitor-research", config)
    
    def validate_inputs(self, inputs: SkillInput) -> bool:
        if not inputs.asin:
            return False
        product_config = inputs.config.get('products', {}).get(inputs.asin, {})
        if not product_config.get('primary_keywords'):
            return False
        return True
    
    def execute(self, inputs: SkillInput) -> SkillOutput:
        start = time.time()
        try:
            # This skill is primarily browser-driven (H10 automation)
            # The scripts handle the data processing pipeline:
            # 1. merge_asin_csvs.py — merge H10 ASIN Grabber exports
            # 2. score_competitors.py — score and rank competitors
            # 3. generate_xlsx.py — generate XLSX report
            # 4. generate_visual_report.py — HTML + MD reports
            
            return SkillOutput(
                status="ready",
                skill_id=self.skill_id,
                execution_time=time.time() - start,
                timestamp=datetime.now(),
                data={"message": "Competitor research requires browser automation. Use scripts/ for data processing."},
                summaries={"status": "Skill initialized, awaiting browser-driven data collection."},
            )
        except Exception as e:
            return SkillOutput(
                status="failure",
                skill_id=self.skill_id,
                execution_time=time.time() - start,
                timestamp=datetime.now(),
                data={},
                summaries={},
                errors=[str(e)],
            )
    
    def generate_summary(self, data: dict, max_tokens: int = 2000) -> str:
        merged = data.get('merged', {})
        top = data.get('top', [])
        niche = data.get('niche', {})
        
        lines = [
            f"COMPETITOR LANDSCAPE — {data.get('asin', 'N/A')}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "Market Overview",
            f"- Total competitors found: {merged.get('total_raw', 0)}",
            f"- After dedup: {merged.get('total_unique', 0)}",
            f"- After filter: {merged.get('total_filtered', 0)}",
            "",
            "Top Competitors",
        ]
        
        for i, comp in enumerate(top[:5], 1):
            lines.append(f"{i}. {comp.get('brand', 'N/A')} - {comp.get('title', '')[:50]} | "
                        f"BSR #{comp.get('bsr', 'N/A')} | {comp.get('reviews', 0)} reviews | "
                        f"${comp.get('price', 0):.2f} | Score: {comp.get('relevance_score', 0):.1f}")
        
        return '\n'.join(lines)
