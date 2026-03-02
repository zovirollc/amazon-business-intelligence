#!/usr/bin/env python3
"""PPC Optimization Skill — analyzes and optimizes Amazon PPC campaigns."""

import time
import json
import os
from datetime import datetime
from skills.base import BaseSkill, SkillInput, SkillOutput


class PPCOptimizationSkill(BaseSkill):
    
    def __init__(self, config: dict):
        super().__init__("ppc-optimization", config)
    
    def validate_inputs(self, inputs: SkillInput) -> bool:
        return bool(inputs.asin)
    
    def execute(self, inputs: SkillInput) -> SkillOutput:
        start = time.time()
        try:
            product_config = inputs.config.get('products', {}).get(inputs.asin, {})
            target_acos = product_config.get('target_acos', 30)
            avg_price = product_config.get('avg_price', 14.99)
            
            # The PPC skill can run fully automated via API data
            # Scripts: parse_search_terms.py, keyword_research.py, campaign_structure.py, generate_ppc_xlsx.py
            
            return SkillOutput(
                status="ready",
                skill_id=self.skill_id,
                execution_time=time.time() - start,
                timestamp=datetime.now(),
                data={
                    "target_acos": target_acos,
                    "avg_price": avg_price,
                    "message": "PPC skill ready. Use data_fetcher.pull_all_data() then run analysis scripts.",
                },
                summaries={"status": f"PPC optimization initialized for {inputs.asin}, target ACOS: {target_acos}%"},
            )
        except Exception as e:
            return SkillOutput(
                status="failure", skill_id=self.skill_id,
                execution_time=time.time() - start, timestamp=datetime.now(),
                data={}, summaries={}, errors=[str(e)],
            )
    
    def generate_summary(self, data: dict, max_tokens: int = 2000) -> str:
        lines = [
            f"PPC PERFORMANCE — {data.get('asin', 'N/A')}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Period: {data.get('period', 'N/A')}",
            "",
            "Key Metrics",
            f"- Total Spend: ${data.get('total_spend', 0):,.2f}",
            f"- Total Sales: ${data.get('total_sales', 0):,.2f}",
            f"- ACOS: {data.get('acos', 0):.1f}% (target: {data.get('target_acos', 30)}%)",
            f"- ROAS: {data.get('roas', 0):.2f}x",
            f"- Active Keywords: {data.get('active_keywords', 0)}",
            f"- Search Terms: {data.get('search_terms', 0)}",
            "",
            "Search Term Classification",
            f"- Winners (ACOS ≤ target): {data.get('winners', 0)}",
            f"- Wasted (0 sales): {data.get('wasted', 0)}",
            f"- Bleeders (ACOS > 2x target): {data.get('bleeders', 0)}",
            "",
            "Top Actions",
        ]
        for action in data.get('top_actions', [])[:5]:
            lines.append(f"- {action}")
        return '\n'.join(lines)
