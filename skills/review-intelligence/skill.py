#!/usr/bin/env python3
"""Review Intelligence Skill — analyzes competitor reviews for insights."""

import time
from datetime import datetime
from skills.base import BaseSkill, SkillInput, SkillOutput


class ReviewIntelligenceSkill(BaseSkill):
    
    def __init__(self, config: dict):
        super().__init__("review-intelligence", config)
    
    def validate_inputs(self, inputs: SkillInput) -> bool:
        return bool(inputs.asin)
    
    def execute(self, inputs: SkillInput) -> SkillOutput:
        start = time.time()
        try:
            return SkillOutput(
                status="ready",
                skill_id=self.skill_id,
                execution_time=time.time() - start,
                timestamp=datetime.now(),
                data={"message": "Review intelligence ready. Requires H10 review CSV exports."},
                summaries={"status": f"Review intelligence initialized for {inputs.asin}"},
            )
        except Exception as e:
            return SkillOutput(
                status="failure", skill_id=self.skill_id,
                execution_time=time.time() - start, timestamp=datetime.now(),
                data={}, summaries={}, errors=[str(e)],
            )
    
    def generate_summary(self, data: dict, max_tokens: int = 2000) -> str:
        lines = [
            f"REVIEW INTELLIGENCE — {data.get('asin', 'N/A')}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Reviews Analyzed: {data.get('total_reviews', 0)}",
            "",
            f"Avg Rating: {data.get('avg_rating', 0)}★ | Sentiment: {data.get('avg_sentiment', 0):+.3f}",
            "",
            "Top Themes",
        ]
        for theme in data.get('themes', [])[:5]:
            lines.append(f"- {theme.get('label', '')}: {theme.get('mentions', 0)} mentions, sentiment {theme.get('sentiment', 0):+.3f}")
        lines.append("")
        lines.append("Strengths")
        for s in data.get('strengths', [])[:3]:
            lines.append(f"- {s}")
        lines.append("")
        lines.append("Pain Points")
        for p in data.get('pain_points', [])[:5]:
            lines.append(f"- {p}")
        return '\n'.join(lines)
