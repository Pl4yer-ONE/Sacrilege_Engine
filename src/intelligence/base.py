"""Base classes for intelligence modules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, Any
from enum import Enum


class FeedbackCategory(Enum):
    """Feedback category types."""
    MECHANICAL = "mechanical"
    TACTICAL = "tactical"
    MENTAL = "mental"


class FeedbackSeverity(Enum):
    """Feedback severity levels."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


@dataclass
class Feedback:
    """Actionable feedback item."""
    category: FeedbackCategory
    severity: FeedbackSeverity
    priority: int  # 1-10, 1 = highest
    
    title: str
    description: str
    fix: str
    
    rounds: list[int] = field(default_factory=list)
    ticks: list[int] = field(default_factory=list)
    
    source_module: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleScore:
    """Score from an intelligence module."""
    module_name: str
    overall_score: float  # 0-100
    
    components: dict[str, float] = field(default_factory=dict)
    round_scores: list[float] = field(default_factory=list)
    
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleResult:
    """Result from an intelligence module analysis."""
    module_name: str
    score: ModuleScore
    feedbacks: list[Feedback] = field(default_factory=list)
    
    raw_data: dict[str, Any] = field(default_factory=dict)


class IntelligenceModule(ABC):
    """Base interface for all intelligence modules."""
    
    name: str
    version: str = "1.0.0"
    
    @abstractmethod
    def analyze(self, context: Any) -> ModuleResult:
        """Run analysis on world state/demo data."""
        ...
    
    @abstractmethod
    def generate_feedback(self, result: ModuleResult) -> list[Feedback]:
        """Generate actionable feedback from analysis results."""
        ...
    
    def compute_score(self, result: ModuleResult) -> ModuleScore:
        """Compute module score from analysis results."""
        return result.score
