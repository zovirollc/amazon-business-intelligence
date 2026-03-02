#!/usr/bin/env python3
"""
Base Skill Interface
All skills extend this class for standardized execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass
class SkillInput:
    """Standardized input for any skill."""
    asin: str
    brand: str
    config: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None
    upstream_data: Optional[Dict[str, Any]] = None  # Data from previous skill in chain


@dataclass 
class SkillOutput:
    """Standardized output from any skill."""
    status: str  # "success", "partial", "failure"
    skill_id: str
    execution_time: float
    timestamp: datetime
    data: Dict[str, Any]
    summaries: Dict[str, str]  # Token-optimized summaries for LLM
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            'status': self.status,
            'skill_id': self.skill_id,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp.isoformat(),
            'data': self.data,
            'summaries': self.summaries,
            'errors': self.errors,
        }


class BaseSkill(ABC):
    """Abstract base class for all skills."""
    
    def __init__(self, skill_id: str, config: dict):
        self.skill_id = skill_id
        self.config = config
    
    @abstractmethod
    def execute(self, inputs: SkillInput) -> SkillOutput:
        """Execute the skill and return standardized output."""
        pass
    
    @abstractmethod
    def validate_inputs(self, inputs: SkillInput) -> bool:
        """Validate that inputs are complete."""
        pass
    
    def generate_summary(self, data: dict, max_tokens: int = 2000) -> str:
        """Generate a token-optimized summary from skill output data.
        Subclasses should override for skill-specific summaries."""
        return f"[{self.skill_id}] Execution completed at {datetime.now().isoformat()}"
