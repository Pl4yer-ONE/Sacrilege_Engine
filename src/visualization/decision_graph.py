"""Decision graph visualization."""

from dataclasses import dataclass, field
from typing import Optional
import json

from src.models import DemoData, RoundData, Team
from src.intelligence.base import Feedback, FeedbackCategory, FeedbackSeverity


@dataclass
class DecisionNode:
    """A node in the decision graph."""
    id: str
    tick: int
    round_number: int
    
    decision_type: str  # peek, rotate, utility, position, trade
    
    # Outcome
    outcome: str  # good, bad, neutral
    
    # Context
    description: str = ""
    
    # Scores
    quality_score: float = 50.0  # 0-100
    
    # Connected nodes
    leads_to: list[str] = field(default_factory=list)
    caused_by: list[str] = field(default_factory=list)


@dataclass
class DecisionGraph:
    """Graph of player decisions for a match."""
    player_id: str
    player_name: str
    map_name: str
    
    nodes: list[DecisionNode] = field(default_factory=list)
    
    # Summary
    good_decisions: int = 0
    bad_decisions: int = 0
    
    # Per-round breakdown
    round_summaries: dict[int, dict] = field(default_factory=dict)


class DecisionGraphGenerator:
    """
    Generates decision graphs showing cause-effect chains.
    
    Visualizes:
    - Peek decisions → outcomes
    - Rotation decisions → impact
    - Trade opportunities → execution
    
    Output: JSON for graph visualization (D3.js compatible)
    """
    
    def __init__(self):
        self.node_counter = 0
    
    def generate(
        self,
        demo_data: Optional[DemoData],
        player_id: str,
        feedbacks: list[Feedback]
    ) -> DecisionGraph:
        """Generate decision graph from analysis results."""
        # Handle None demo_data
        if demo_data is None:
            graph = DecisionGraph(
                player_id=player_id,
                player_name="Unknown",
                map_name="unknown",
            )
        else:
            player_info = demo_data.players.get(player_id)
            graph = DecisionGraph(
                player_id=player_id,
                player_name=player_info.name if player_info else "Unknown",
                map_name=demo_data.header.map_name if demo_data.header else "unknown",
            )
        
        self.node_counter = 0
        
        # Create nodes from feedbacks
        for feedback in feedbacks:
            nodes = self._feedback_to_nodes(feedback)
            graph.nodes.extend(nodes)
            
            # Count good/bad
            for node in nodes:
                if node.outcome == "bad":
                    graph.bad_decisions += 1
                elif node.outcome == "good":
                    graph.good_decisions += 1
        
        # Create round summaries from demo_data if available
        if demo_data and demo_data.rounds:
            for round_data in demo_data.rounds:
                round_nodes = [n for n in graph.nodes if n.round_number == round_data.round_number]
                graph.round_summaries[round_data.round_number] = {
                    "total_decisions": len(round_nodes),
                    "good": sum(1 for n in round_nodes if n.outcome == "good"),
                    "bad": sum(1 for n in round_nodes if n.outcome == "bad"),
                }
        
        return graph
    
    def _feedback_to_nodes(self, feedback: Feedback) -> list[DecisionNode]:
        """Convert feedback to decision nodes."""
        nodes = []
        
        # Determine decision type from category
        decision_type = {
            FeedbackCategory.MECHANICAL: "aim",
            FeedbackCategory.TACTICAL: "tactical",
            FeedbackCategory.MENTAL: "mental",
        }.get(feedback.category, "other")
        
        # Determine outcome from severity (critical/major = bad, minor = neutral)
        outcome = "bad" if feedback.severity in (FeedbackSeverity.CRITICAL, FeedbackSeverity.MAJOR) else "neutral"
        
        # Create a node for each round mentioned
        for round_num in feedback.rounds or [0]:
            self.node_counter += 1
            nodes.append(DecisionNode(
                id=f"node_{self.node_counter}",
                tick=0,
                round_number=round_num,
                decision_type=decision_type,
                outcome=outcome,
                description=feedback.title,
                quality_score=100 - (feedback.priority * 10),
            ))
        
        return nodes
    
    def to_json(self, graph: DecisionGraph) -> str:
        """Export graph as JSON (D3.js force-directed compatible)."""
        data = {
            "player": graph.player_name,
            "map": graph.map_name,
            "summary": {
                "good_decisions": graph.good_decisions,
                "bad_decisions": graph.bad_decisions,
                "ratio": graph.good_decisions / max(1, graph.good_decisions + graph.bad_decisions),
            },
            "nodes": [
                {
                    "id": n.id,
                    "round": n.round_number,
                    "type": n.decision_type,
                    "outcome": n.outcome,
                    "description": n.description,
                    "score": n.quality_score,
                }
                for n in graph.nodes
            ],
            "links": [
                {"source": n.id, "target": t}
                for n in graph.nodes
                for t in n.leads_to
            ],
            "rounds": graph.round_summaries,
        }
        return json.dumps(data, indent=2)
    
    def to_text_summary(self, graph: DecisionGraph) -> str:
        """Generate text summary of decision quality."""
        total = graph.good_decisions + graph.bad_decisions
        if total == 0:
            return "No decisions analyzed."
        
        ratio = graph.good_decisions / total * 100
        
        lines = [
            f"=== Decision Quality: {graph.player_name} ===",
            f"Map: {graph.map_name}",
            f"",
            f"Good decisions: {graph.good_decisions}",
            f"Bad decisions: {graph.bad_decisions}",
            f"Quality ratio: {ratio:.1f}%",
            f"",
            "Round breakdown:",
        ]
        
        for rnum, summary in sorted(graph.round_summaries.items()):
            if summary["total_decisions"] > 0:
                lines.append(f"  R{rnum}: {summary['good']} good, {summary['bad']} bad")
        
        return "\n".join(lines)
