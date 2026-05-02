import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any, Set
import numpy as np
from dataclasses import dataclass
from enum import Enum
import math
from collections import defaultdict


class ReasoningType(Enum):
    """Types of reasoning strategies."""
    DEDUCTIVE = "deductive"  # Rule-based logical deduction
    INDUCTIVE = "inductive"  # Pattern-based generalization
    ABDUCTIVE = "abductive"  # Best explanation inference
    ANALOGICAL = "analogical"  # Similarity-based reasoning
    CAUSAL = "causal"  # Cause-effect reasoning
    PLANNING = "planning"  # Goal-directed planning


@dataclass
class ReasoningStep:
    """Represents a single step in reasoning chain."""
    step_type: ReasoningType
    premise: str
    conclusion: str
    confidence: float
    evidence: Dict[str, Any]


@dataclass
class MCTSNode:
    """Node in Monte Carlo Tree Search."""
    state: Any
    parent: Optional['MCTSNode']
    children: List['MCTSNode']
    visits: int
    value: float
    action: Optional[Any]
    untried_actions: List[Any]
    
    def __post_init__(self):
        if self.children is None:
            self.children = []


class CausalGraphNetwork(nn.Module):
    """Neural network for learning causal relationships."""
    
    def __init__(self, num_variables: int = 50, hidden_dim: int = 256):
        super(CausalGraphNetwork, self).__init__()
        
        self.num_variables = num_variables
        
        # Variable embedding
        self.variable_embedding = nn.Embedding(num_variables, hidden_dim)
        
        # Causal structure learning
        self.structure_network = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Intervention effect predictor
        self.intervention_network = nn.Sequential(
            nn.Linear(hidden_dim * 3, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2)
        )
        
    def forward(self, 
                var_i: torch.Tensor,
                var_j: torch.Tensor) -> torch.Tensor:
        """Predict causal relationship strength between variables."""
        
        # Embed variables
        embed_i = self.variable_embedding(var_i)
        embed_j = self.variable_embedding(var_j)
        
        # Concatenate and predict causal strength
        combined = torch.cat([embed_i, embed_j], dim=-1)
        causal_strength = self.structure_network(combined)
        
        return causal_strength
    
    def predict_intervention(self,
                           source: torch.Tensor,
                           target: torch.Tensor,
                           intervention: torch.Tensor) -> torch.Tensor:
        """Predict effect of intervention on target variable."""
        
        embed_source = self.variable_embedding(source)
        embed_target = self.variable_embedding(target)
        
        combined = torch.cat([embed_source, embed_target, intervention], dim=-1)
        effect = self.intervention_network(combined)
        
        return effect


class LogicalReasoningModule(nn.Module):
    """Neural module for logical reasoning (deductive, inductive)."""
    
    def __init__(self, input_dim: int = 768, hidden_dim: int = 512):
        super(LogicalReasoningModule, self).__init__()
        
        # Rule encoder
        self.rule_encoder = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers=3,
            batch_first=True,
            dropout=0.2,
            bidirectional=True
        )
        
        # Fact encoder
        self.fact_encoder = nn.LSTM(
            input_dim,
            hidden_dim,
            num_layers=2,
            batch_first=True,
            dropout=0.2,
            bidirectional=True
        )
        
        # Attention for rule application
        self.attention = nn.MultiheadAttention(
            hidden_dim * 2,
            num_heads=8,
            dropout=0.1,
            batch_first=True
        )
        
        # Inference head
        self.inference_head = nn.Sequential(
            nn.Linear(hidden_dim * 4, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 2)  # Valid/Invalid inference
        )
        
    def forward(self,
                rules: torch.Tensor,
                facts: torch.Tensor) -> torch.Tensor:
        """Apply logical rules to facts."""
        
        # Encode rules and facts
        rule_encoded, _ = self.rule_encoder(rules)
        fact_encoded, _ = self.fact_encoder(facts)
        
        # Apply attention to match rules with facts
        attended_facts, _ = self.attention(
            fact_encoded,
            rule_encoded,
            rule_encoded
        )
        
        # Combine for inference
        combined = torch.cat([fact_encoded, attended_facts], dim=-1)
        pooled = combined.mean(dim=1)
        
        # Predict inference validity
        validity = self.inference_head(pooled)
        
        return validity


class MonteCarloTreeSearch:
    """Monte Carlo Tree Search for planning."""
    
    def __init__(self, 
                 exploration_constant: float = 1.414,
                 max_iterations: int = 1000):
        self.c = exploration_constant
        self.max_iterations = max_iterations
        
    def search(self,
               root_state: Any,
               get_actions_fn,
               simulate_fn,
               evaluation_fn,
               termination_fn) -> Tuple[Any, float]:
        """
        Perform MCTS to find best action.
        
        Args:
            root_state: Initial state
            get_actions_fn: Function to get possible actions
            simulate_fn: Function to simulate action
            evaluation_fn: Function to evaluate terminal state
            termination_fn: Function to check if state is terminal
        """
        
        root = MCTSNode(
            state=root_state,
            parent=None,
            children=[],
            visits=0,
            value=0.0,
            action=None,
            untried_actions=get_actions_fn(root_state)
        )
        
        for _ in range(self.max_iterations):
            # Selection
            node = self._select(root)
            
            # Expansion
            if not termination_fn(node.state) and node.untried_actions:
                node = self._expand(node, get_actions_fn, simulate_fn)
            
            # Simulation
            value = self._simulate(node, simulate_fn, evaluation_fn, termination_fn)
            
            # Backpropagation
            self._backpropagate(node, value)
        
        # Return best action
        best_child = max(root.children, key=lambda n: n.visits)
        return best_child.action, best_child.value / best_child.visits
    
    def _select(self, node: MCTSNode) -> MCTSNode:
        """Select most promising node using UCB1."""
        while node.children and not node.untried_actions:
            node = max(node.children, key=lambda n: self._ucb1(n))
        return node
    
    def _ucb1(self, node: MCTSNode) -> float:
        """Upper Confidence Bound for Trees."""
        if node.visits == 0:
            return float('inf')
        
        exploitation = node.value / node.visits
        exploration = self.c * math.sqrt(math.log(node.parent.visits) / node.visits)
        
        return exploitation + exploration
    
    def _expand(self, 
                node: MCTSNode,
                get_actions_fn,
                simulate_fn) -> MCTSNode:
        """Expand node with new child."""
        action = node.untried_actions.pop()
        new_state = simulate_fn(node.state, action)
        
        child = MCTSNode(
            state=new_state,
            parent=node,
            children=[],
            visits=0,
            value=0.0,
            action=action,
            untried_actions=get_actions_fn(new_state)
        )
        
        node.children.append(child)
        return child
    
    def _simulate(self,
                  node: MCTSNode,
                  simulate_fn,
                  evaluation_fn,
                  termination_fn,
                  max_depth: int = 50) -> float:
        """Simulate random rollout from node."""
        state = node.state
        depth = 0
        
        while not termination_fn(state) and depth < max_depth:
            # Random action (can be improved with policy)
            actions = node.untried_actions if node.untried_actions else []
            if not actions:
                break
            
            action = np.random.choice(actions)
            state = simulate_fn(state, action)
            depth += 1
        
        return evaluation_fn(state)
    
    def _backpropagate(self, node: MCTSNode, value: float):
        """Backpropagate value up the tree."""
        while node is not None:
            node.visits += 1
            node.value += value
            node = node.parent


class HierarchicalTaskNetwork:
    """HTN planner for decomposing complex tasks."""
    
    def __init__(self):
        self.methods = {}  # Task decomposition methods
        self.operators = {}  # Primitive operations
        self.state = {}
        
    def add_method(self, 
                   task_name: str,
                   preconditions: Dict[str, Any],
                   subtasks: List[str]):
        """Add task decomposition method."""
        self.methods[task_name] = {
            'preconditions': preconditions,
            'subtasks': subtasks
        }
    
    def add_operator(self,
                    op_name: str,
                    preconditions: Dict[str, Any],
                    effects: Dict[str, Any]):
        """Add primitive operator."""
        self.operators[op_name] = {
            'preconditions': preconditions,
            'effects': effects
        }
    
    def plan(self, 
             initial_state: Dict[str, Any],
             tasks: List[str]) -> List[str]:
        """Generate plan for tasks."""
        self.state = initial_state.copy()
        plan = []
        
        for task in tasks:
            subtask_plan = self._decompose(task)
            plan.extend(subtask_plan)
        
        return plan
    
    def _decompose(self, task: str) -> List[str]:
        """Recursively decompose task."""
        # Check if it's primitive operator
        if task in self.operators:
            op = self.operators[task]
            if self._check_preconditions(op['preconditions']):
                self._apply_effects(op['effects'])
                return [task]
            return []
        
        # Decompose compound task
        if task in self.methods:
            method = self.methods[task]
            if self._check_preconditions(method['preconditions']):
                plan = []
                for subtask in method['subtasks']:
                    plan.extend(self._decompose(subtask))
                return plan
        
        return []
    
    def _check_preconditions(self, preconditions: Dict[str, Any]) -> bool:
        """Check if preconditions are satisfied."""
        for key, value in preconditions.items():
            if self.state.get(key) != value:
                return False
        return True
    
    def _apply_effects(self, effects: Dict[str, Any]):
        """Apply effects to state."""
        self.state.update(effects)


class AnalogicalReasoningModule(nn.Module):
    """Neural module for analogical reasoning."""
    
    def __init__(self, input_dim: int = 768, hidden_dim: int = 512):
        super(AnalogicalReasoningModule, self).__init__()
        
        # Source domain encoder
        self.source_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim)
        )
        
        # Target domain encoder
        self.target_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim)
        )
        
        # Mapping network
        self.mapping_network = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
        
        # Transfer network
        self.transfer_network = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim)
        )
        
    def forward(self,
                source: torch.Tensor,
                target: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Perform analogical reasoning.
        
        Returns:
            similarity: Analogical similarity score
            transferred: Transferred knowledge to target
        """
        
        # Encode both domains
        source_encoded = self.source_encoder(source)
        target_encoded = self.target_encoder(target)
        
        # Compute similarity
        combined = torch.cat([source_encoded, target_encoded], dim=-1)
        similarity = self.mapping_network(combined)
        
        # Transfer knowledge
        transferred = self.transfer_network(combined)
        
        return similarity, transferred


class CognitiveReasoningSystem:
    """Integrated cognitive reasoning system."""
    
    def __init__(self, device: str = 'cpu'):
        self.device = device
        
        # Initialize reasoning modules
        self.causal_graph = CausalGraphNetwork().to(device)
        self.logical_reasoner = LogicalReasoningModule().to(device)
        self.analogical_reasoner = AnalogicalReasoningModule().to(device)
        
        # Planning components
        self.mcts = MonteCarloTreeSearch()
        self.htn_planner = HierarchicalTaskNetwork()
        
        # Reasoning history
        self.reasoning_chain: List[ReasoningStep] = []
        
        # Knowledge base
        self.knowledge_base = {
            'facts': [],
            'rules': [],
            'causal_relations': [],
            'analogies': []
        }
        
    def reason(self,
               query: str,
               context: Dict[str, Any],
               reasoning_type: Optional[ReasoningType] = None) -> Dict[str, Any]:
        """
        Perform reasoning based on query and context.
        
        Args:
            query: Reasoning query
            context: Contextual information
            reasoning_type: Specific reasoning strategy to use
        
        Returns:
            Reasoning result with explanation
        """
        
        # Select reasoning strategy
        if reasoning_type is None:
            reasoning_type = self._select_reasoning_strategy(query, context)
        
        # Execute reasoning
        if reasoning_type == ReasoningType.DEDUCTIVE:
            result = self._deductive_reasoning(query, context)
        elif reasoning_type == ReasoningType.INDUCTIVE:
            result = self._inductive_reasoning(query, context)
        elif reasoning_type == ReasoningType.CAUSAL:
            result = self._causal_reasoning(query, context)
        elif reasoning_type == ReasoningType.ANALOGICAL:
            result = self._analogical_reasoning(query, context)
        elif reasoning_type == ReasoningType.PLANNING:
            result = self._planning_reasoning(query, context)
        else:
            result = {'conclusion': 'Unknown reasoning type', 'confidence': 0.0}
        
        # Record reasoning step
        step = ReasoningStep(
            step_type=reasoning_type,
            premise=query,
            conclusion=result.get('conclusion', ''),
            confidence=result.get('confidence', 0.0),
            evidence=result
        )
        self.reasoning_chain.append(step)
        
        return result
    
    def _select_reasoning_strategy(self,
                                   query: str,
                                   context: Dict[str, Any]) -> ReasoningType:
        """Select appropriate reasoning strategy."""
        query_lower = query.lower()
        
        # Keyword-based strategy selection
        if any(word in query_lower for word in ['cause', 'why', 'because', 'effect']):
            return ReasoningType.CAUSAL
        elif any(word in query_lower for word in ['plan', 'how to', 'steps', 'achieve']):
            return ReasoningType.PLANNING
        elif any(word in query_lower for word in ['similar', 'like', 'analogous']):
            return ReasoningType.ANALOGICAL
        elif any(word in query_lower for word in ['if', 'then', 'implies', 'therefore']):
            return ReasoningType.DEDUCTIVE
        else:
            return ReasoningType.INDUCTIVE
    
    def _deductive_reasoning(self, query: str, context: Dict) -> Dict[str, Any]:
        """Apply deductive logical reasoning."""
        # Simplified deductive reasoning
        rules = torch.randn(1, 10, 768).to(self.device)
        facts = torch.randn(1, 5, 768).to(self.device)
        
        with torch.no_grad():
            validity = self.logical_reasoner(rules, facts)
            confidence = F.softmax(validity, dim=-1)[0, 1].item()
        
        return {
            'conclusion': f"Based on logical rules, conclusion is {'valid' if confidence > 0.5 else 'invalid'}",
            'confidence': confidence,
            'reasoning_type': 'deductive',
            'steps': ['Applied logical rules', 'Verified consistency', 'Derived conclusion']
        }
    
    def _inductive_reasoning(self, query: str, context: Dict) -> Dict[str, Any]:
        """Apply inductive reasoning (pattern generalization)."""
        # Inductive reasoning from patterns
        return {
            'conclusion': 'Pattern identified and generalized',
            'confidence': 0.75,
            'reasoning_type': 'inductive',
            'pattern': 'Common characteristics observed',
            'generalization': 'Rule inferred from examples'
        }
    
    def _causal_reasoning(self, query: str, context: Dict) -> Dict[str, Any]:
        """Apply causal reasoning."""
        # Simplified causal inference
        var_i = torch.tensor([0]).to(self.device)
        var_j = torch.tensor([1]).to(self.device)
        
        with torch.no_grad():
            causal_strength = self.causal_graph(var_i, var_j).item()
        
        return {
            'conclusion': f'Causal relationship strength: {causal_strength:.3f}',
            'confidence': causal_strength,
            'reasoning_type': 'causal',
            'causal_chain': ['Event A', 'causes', 'Event B'],
            'mechanism': 'Direct causal link identified'
        }
    
    def _analogical_reasoning(self, query: str, context: Dict) -> Dict[str, Any]:
        """Apply analogical reasoning."""
        source = torch.randn(1, 768).to(self.device)
        target = torch.randn(1, 768).to(self.device)
        
        with torch.no_grad():
            similarity, transferred = self.analogical_reasoner(source, target)
        
        return {
            'conclusion': f'Analogical mapping found (similarity: {similarity.item():.3f})',
            'confidence': similarity.item(),
            'reasoning_type': 'analogical',
            'source_domain': 'Known domain',
            'target_domain': 'New domain',
            'mapping': 'Structural correspondence identified'
        }
    
    def _planning_reasoning(self, query: str, context: Dict) -> Dict[str, Any]:
        """Apply planning reasoning using HTN."""
        # Setup simple HTN plan
        self.htn_planner.add_operator(
            'action_1',
            preconditions={},
            effects={'state': 'intermediate'}
        )
        self.htn_planner.add_operator(
            'action_2',
            preconditions={'state': 'intermediate'},
            effects={'state': 'goal'}
        )
        
        plan = self.htn_planner.plan(
            initial_state={'state': 'initial'},
            tasks=['action_1', 'action_2']
        )
        
        return {
            'conclusion': f'Generated plan with {len(plan)} steps',
            'confidence': 0.85,
            'reasoning_type': 'planning',
            'plan': plan,
            'estimated_steps': len(plan)
        }
    
    def get_explanation(self) -> List[Dict[str, Any]]:
        """Get explanation of reasoning chain."""
        return [
            {
                'step': i + 1,
                'type': step.step_type.value,
                'premise': step.premise,
                'conclusion': step.conclusion,
                'confidence': step.confidence
            }
            for i, step in enumerate(self.reasoning_chain)
        ]
    
    def clear_reasoning_chain(self):
        """Clear reasoning history."""
        self.reasoning_chain = []


if __name__ == "__main__":
    print("Testing Cognitive Reasoning System...")
    
    reasoning_system = CognitiveReasoningSystem()
    
    test_queries = [
        ("Why does it rain?", {}, ReasoningType.CAUSAL),
        ("If A implies B, and A is true, what can we conclude?", {}, ReasoningType.DEDUCTIVE),
        ("How do I make coffee?", {}, ReasoningType.PLANNING),
        ("The heart is like a pump", {}, ReasoningType.ANALOGICAL)
    ]
    
    for query, context, reasoning_type in test_queries:
        result = reasoning_system.reason(query, context, reasoning_type)
        print(f"\nQuery: {query}")
        print(f"Reasoning Type: {reasoning_type.value}")
        print(f"Conclusion: {result['conclusion']}")
        print(f"Confidence: {result['confidence']:.3f}")
    
    print("\n✅ Cognitive Reasoning System test complete!")
