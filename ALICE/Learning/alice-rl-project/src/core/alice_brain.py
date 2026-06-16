import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass, field
import json
import os

# Import all cognitive systems
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from memory.long_term_memory import (
    LongTermMemoryModule, ExperienceReplayBuffer,
    TransferLearningManager, MetaLearningModule
)
from nlp.language_understanding import (
    NLPPipeline, IntentClassification, ConversationContext
)
from reasoning.cognitive_reasoning import (
    CognitiveReasoningSystem, ReasoningType, ReasoningStep
)
from perception.multimodal_perception import (
    PerceptionSystem, StateRepresentation
)
from personality.emotion_personality import (
    PersonalityEmotionSystem, EmotionState, PersonalityProfile
)


@dataclass
class AliceConfig:
    """Configuration for ALICE brain."""
    # Model dimensions
    state_dim: int = 1024
    action_dim: int = 10
    hidden_dim: int = 512
    
    # RL parameters
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    
    # Learning rates
    actor_lr: float = 3e-4
    critic_lr: float = 1e-3
    
    # Device
    device: str = 'cpu'
    
    # System toggles
    use_memory: bool = True
    use_nlp: bool = True
    use_reasoning: bool = True
    use_perception: bool = True
    use_personality: bool = True
    
    # Training parameters
    max_episode_length: int = 1000
    batch_size: int = 64
    update_epochs: int = 10
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {k: v for k, v in self.__dict__.items()}
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'AliceConfig':
        """Create config from dictionary."""
        return cls(**config_dict)


class ActorCriticNetwork(nn.Module):
    """
    Actor-Critic neural network for policy and value estimation.
    """
    
    def __init__(self,
                 state_dim: int,
                 action_dim: int,
                 hidden_dim: int = 512):
        super(ActorCriticNetwork, self).__init__()
        
        # Shared feature extractor
        self.shared_network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU()
        )
        
        # Actor head (policy)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, action_dim)
        )
        
        # Critic head (value function)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, 1)
        )
        
        # Action value head (Q-values for actor-critic hybrid)
        self.q_values = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )
        
    def forward(self,
                state: torch.Tensor,
                action: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        """
        Forward pass through actor-critic network.
        
        Returns dict with:
            - action_logits: Policy logits
            - value: State value
            - action_probs: Action probabilities
            - q_values: Q-values for each action
        """
        # Extract shared features
        features = self.shared_network(state)
        
        # Actor output
        action_logits = self.actor(features)
        action_probs = F.softmax(action_logits, dim=-1)
        
        # Critic output
        value = self.critic(features)
        
        # Q-values
        q_vals = self.q_values(features)
        
        return {
            'action_logits': action_logits,
            'action_probs': action_probs,
            'value': value,
            'q_values': q_vals
        }


class AliceBrain:
    """
    Complete ALICE cognitive system integrating all subsystems:
    - Memory (long-term, episodic, semantic)
    - NLP (language understanding and generation)
    - Reasoning (deductive, inductive, causal, analogical, planning)
    - Perception (multimodal: vision, audio, text)
    - Personality & Emotion (human-like emotional intelligence)
    """
    
    def __init__(self, config: Optional[AliceConfig] = None):
        self.config = config or AliceConfig()
        self.device = self.config.device
        
        # Initialize core neural network
        self.actor_critic = ActorCriticNetwork(
            state_dim=self.config.state_dim,
            action_dim=self.config.action_dim,
            hidden_dim=self.config.hidden_dim
        ).to(self.device)
        
        # Initialize cognitive subsystems
        self._initialize_subsystems()
        
        # Optimizers
        self.actor_optimizer = torch.optim.Adam(
            self.actor_critic.actor.parameters(),
            lr=self.config.actor_lr
        )
        self.critic_optimizer = torch.optim.Adam(
            self.actor_critic.critic.parameters(),
            lr=self.config.critic_lr
        )
        
        # Training statistics
        self.episode_count = 0
        self.total_steps = 0
        self.training_stats = {
            'episode_rewards': [],
            'actor_losses': [],
            'critic_losses': [],
            'average_values': []
        }
        
    def _initialize_subsystems(self):
        """Initialize all cognitive subsystems."""
        
        # Memory system
        if self.config.use_memory:
            self.memory = LongTermMemoryModule(
                input_dim=self.config.state_dim,
                memory_dim=512
            ).to(self.device)
            
            self.experience_buffer = ExperienceReplayBuffer(capacity=100000)
            self.transfer_manager = TransferLearningManager(
                base_model_dim=self.config.state_dim
            )
            self.meta_learner = MetaLearningModule(
                model_dim=self.config.state_dim
            )
        else:
            self.memory = None
            self.experience_buffer = None
        
        # NLP system
        if self.config.use_nlp:
            self.nlp = NLPPipeline()
        else:
            self.nlp = None
        
        # Reasoning system
        if self.config.use_reasoning:
            self.reasoning = CognitiveReasoningSystem(device=self.device)
        else:
            self.reasoning = None
        
        # Perception system
        if self.config.use_perception:
            self.perception = PerceptionSystem(device=self.device)
        else:
            self.perception = None
        
        # Personality & Emotion system
        if self.config.use_personality:
            self.personality_emotion = PersonalityEmotionSystem(device=self.device)
        else:
            self.personality_emotion = None
    
    def process_input(self,
                     text: Optional[str] = None,
                     visual: Optional[np.ndarray] = None,
                     audio: Optional[np.ndarray] = None,
                     context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process multi-modal input through all cognitive systems.
        
        Args:
            text: Text input
            visual: Visual input (image)
            audio: Audio input
            context: Additional context
        
        Returns:
            Complete processing result with all subsystem outputs
        """
        result = {
            'nlp_output': None,
            'perception_state': None,
            'reasoning_result': None,
            'emotion_state': None,
            'personality': None,
            'memory_retrieval': None,
            'fused_state': None
        }
        
        # 1. NLP Processing
        if text and self.nlp:
            nlp_output = self.nlp.process(text)
            result['nlp_output'] = nlp_output
        
        # 2. Perception Processing
        text_embedding = None
        if self.nlp and result['nlp_output']:
            # Get text embedding from NLP (simplified)
            text_embedding = torch.randn(1, 768).to(self.device)
        
        if self.perception:
            perception_state = self.perception.perceive(
                visual=visual,
                audio=audio,
                text_embedding=text_embedding
            )
            result['perception_state'] = perception_state
            
            # Use fused state as primary state
            if perception_state.fused is not None:
                fused_state = perception_state.fused
                result['fused_state'] = fused_state
            else:
                # Fallback to random state
                fused_state = torch.randn(1, self.config.state_dim).to(self.device)
                result['fused_state'] = fused_state
        else:
            fused_state = torch.randn(1, self.config.state_dim).to(self.device)
            result['fused_state'] = fused_state
        
        # 3. Memory Retrieval
        if self.memory:
            with torch.no_grad():
                memory_output = self.memory(fused_state)
                result['memory_retrieval'] = {
                    'episodic': memory_output['episodic_memory'],
                    'semantic': memory_output['semantic_memory']
                }
        
        # 4. Emotion & Personality Processing
        if self.personality_emotion:
            emotion_state, personality = self.personality_emotion.process_state(
                fused_state,
                context=text_embedding if text_embedding is not None else None
            )
            result['emotion_state'] = emotion_state
            result['personality'] = personality
        
        # 5. Reasoning (if query requires it)
        if text and self.reasoning:
            reasoning_result = self.reasoning.reason(
                query=text,
                context=context or {},
                reasoning_type=None  # Auto-select
            )
            result['reasoning_result'] = reasoning_result
        
        return result
    
    def select_action(self, 
                     state: torch.Tensor,
                     deterministic: bool = False) -> Tuple[int, float, torch.Tensor]:
        """
        Select action using current policy.
        
        Args:
            state: Current state tensor
            deterministic: If True, select argmax action; else sample
        
        Returns:
            action: Selected action index
            log_prob: Log probability of action
            value: State value estimate
        """
        with torch.no_grad():
            output = self.actor_critic(state)
            
            action_probs = output['action_probs']
            value = output['value']
            
            if deterministic:
                action = torch.argmax(action_probs, dim=-1)
                log_prob = torch.log(action_probs.gather(1, action.unsqueeze(-1)))
            else:
                dist = torch.distributions.Categorical(action_probs)
                action = dist.sample()
                log_prob = dist.log_prob(action)
            
            return action.item(), log_prob.item(), value.item()
    
    def think(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main thinking process - integrates all cognitive systems.
        
        Args:
            observation: Multi-modal observation dict
        
        Returns:
            Complete cognitive output including action, reasoning, emotion, etc.
        """
        # Process all inputs
        processing_result = self.process_input(
            text=observation.get('text'),
            visual=observation.get('visual'),
            audio=observation.get('audio'),
            context=observation.get('context')
        )
        
        # Get fused state
        state = processing_result['fused_state']
        
        # Select action
        action, log_prob, value = self.select_action(state, deterministic=False)
        
        # Apply personality-based modifications if available
        if self.personality_emotion and processing_result['personality']:
            personality = processing_result['personality']
            
            # Modify action selection based on personality traits
            # E.g., high openness -> more exploratory actions
            if personality.risk_tolerance > 0.7 and np.random.random() > 0.8:
                # Occasionally take random action (exploration)
                action = np.random.randint(0, self.config.action_dim)
        
        # Construct response
        response = {
            'action': action,
            'confidence': np.exp(log_prob),
            'value_estimate': value,
            'state': state,
            'nlp_output': processing_result.get('nlp_output'),
            'reasoning': processing_result.get('reasoning_result'),
            'emotion': processing_result.get('emotion_state'),
            'personality': processing_result.get('personality')
        }
        
        # Generate natural language response if NLP available
        if self.nlp and processing_result.get('nlp_output'):
            response['text_response'] = processing_result['nlp_output']['response']
        
        return response
    
    def learn(self,
             states: torch.Tensor,
             actions: torch.Tensor,
             rewards: torch.Tensor,
             next_states: torch.Tensor,
             dones: torch.Tensor,
             old_log_probs: torch.Tensor) -> Dict[str, float]:
        """
        Learn from experience using PPO algorithm.
        
        Args:
            states: Batch of states
            actions: Batch of actions taken
            rewards: Batch of rewards received
            next_states: Batch of next states
            dones: Batch of done flags
            old_log_probs: Log probabilities from behavior policy
        
        Returns:
            Training statistics
        """
        
        # Compute returns and advantages
        returns, advantages = self._compute_gae(
            rewards, next_states, dones
        )
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        stats = {
            'actor_loss': 0.0,
            'critic_loss': 0.0,
            'entropy': 0.0
        }
        
        # PPO update epochs
        for _ in range(self.config.update_epochs):
            # Forward pass
            output = self.actor_critic(states)
            
            # Compute new log probabilities
            dist = torch.distributions.Categorical(output['action_probs'])
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # Compute ratio
            ratio = torch.exp(new_log_probs - old_log_probs)
            
            # PPO clipped objective
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 
                              1.0 - self.config.clip_epsilon,
                              1.0 + self.config.clip_epsilon) * advantages
            actor_loss = -torch.min(surr1, surr2).mean()
            
            # Critic loss
            values = output['value'].squeeze()
            critic_loss = F.mse_loss(values, returns)
            
            # Total loss with entropy bonus
            total_loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy
            
            # Update actor
            self.actor_optimizer.zero_grad()
            actor_loss.backward(retain_graph=True)
            torch.nn.utils.clip_grad_norm_(self.actor_critic.actor.parameters(), 0.5)
            self.actor_optimizer.step()
            
            # Update critic
            self.critic_optimizer.zero_grad()
            critic_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.actor_critic.critic.parameters(), 0.5)
            self.critic_optimizer.step()
            
            stats['actor_loss'] += actor_loss.item()
            stats['critic_loss'] += critic_loss.item()
            stats['entropy'] += entropy.item()
        
        # Average over epochs
        for key in stats:
            stats[key] /= self.config.update_epochs
        
        # Store experience in memory if available
        if self.experience_buffer:
            for i in range(len(states)):
                self.experience_buffer.add(
                    state=states[i].cpu().numpy(),
                    action=actions[i].item(),
                    reward=rewards[i].item(),
                    next_state=next_states[i].cpu().numpy(),
                    done=dones[i].item()
                )
        
        return stats
    
    def _compute_gae(self,
                    rewards: torch.Tensor,
                    next_states: torch.Tensor,
                    dones: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Compute Generalized Advantage Estimation."""
        
        with torch.no_grad():
            # Get values for next states
            next_values = self.actor_critic(next_states)['value'].squeeze()
            
        returns = []
        advantages = []
        gae = 0
        
        # Compute backwards
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = next_values[-1] * (1 - dones[-1])
            else:
                next_value = next_values[t + 1] * (1 - dones[t + 1])
            
            delta = rewards[t] + self.config.gamma * next_value - next_values[t]
            gae = delta + self.config.gamma * self.config.gae_lambda * (1 - dones[t]) * gae
            
            returns.insert(0, gae + next_values[t])
            advantages.insert(0, gae)
        
        returns = torch.tensor(returns, device=self.device)
        advantages = torch.tensor(advantages, device=self.device)
        
        return returns, advantages
    
    def save(self, directory: str):
        """Save complete ALICE brain."""
        os.makedirs(directory, exist_ok=True)
        
        # Save main network
        torch.save({
            'actor_critic': self.actor_critic.state_dict(),
            'actor_optimizer': self.actor_optimizer.state_dict(),
            'critic_optimizer': self.critic_optimizer.state_dict(),
            'episode_count': self.episode_count,
            'total_steps': self.total_steps,
            'training_stats': self.training_stats
        }, os.path.join(directory, 'alice_brain.pt'))
        
        # Save subsystems
        if self.memory:
            torch.save(self.memory.state_dict(), 
                      os.path.join(directory, 'memory.pt'))
        
        if self.nlp:
            self.nlp.save_model(os.path.join(directory, 'nlp.pt'))
        
        if self.perception:
            self.perception.save_models(os.path.join(directory, 'perception.pt'))
        
        if self.personality_emotion:
            self.personality_emotion.save_models(
                os.path.join(directory, 'personality_emotion.pt')
            )
        
        # Save config
        with open(os.path.join(directory, 'config.json'), 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)
        
        print(f"✅ ALICE brain saved to {directory}")
    
    def load(self, directory: str):
        """Load complete ALICE brain."""
        
        # Load main network
        # SECURITY (CWE-502): weights_only=True prevents arbitrary code
        # execution from a crafted/tampered checkpoint during unpickling.
        checkpoint = torch.load(
            os.path.join(directory, 'alice_brain.pt'),
            map_location=self.device,
            weights_only=True
        )
        self.actor_critic.load_state_dict(checkpoint['actor_critic'])
        self.actor_optimizer.load_state_dict(checkpoint['actor_optimizer'])
        self.critic_optimizer.load_state_dict(checkpoint['critic_optimizer'])
        self.episode_count = checkpoint['episode_count']
        self.total_steps = checkpoint['total_steps']
        self.training_stats = checkpoint['training_stats']

        # Load subsystems
        if self.memory and os.path.exists(os.path.join(directory, 'memory.pt')):
            self.memory.load_state_dict(torch.load(
                os.path.join(directory, 'memory.pt'),
                map_location=self.device,
                weights_only=True
            ))
        
        if self.nlp and os.path.exists(os.path.join(directory, 'nlp.pt')):
            self.nlp.load_model(os.path.join(directory, 'nlp.pt'))
        
        if self.perception and os.path.exists(os.path.join(directory, 'perception.pt')):
            self.perception.load_models(os.path.join(directory, 'perception.pt'))
        
        if self.personality_emotion and os.path.exists(
            os.path.join(directory, 'personality_emotion.pt')):
            self.personality_emotion.load_models(
                os.path.join(directory, 'personality_emotion.pt')
            )
        
        print(f"✅ ALICE brain loaded from {directory}")


if __name__ == "__main__":
    print("Testing ALICE Brain Integration...")
    
    # Create ALICE
    config = AliceConfig(
        state_dim=1024,
        action_dim=10,
        device='cpu'
    )
    alice = AliceBrain(config)
    
    # Test thinking process
    observation = {
        'text': "Hello ALICE, how are you?",
        'visual': np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8),
        'context': {}
    }
    
    print("\n🧠 ALICE is thinking...")
    response = alice.think(observation)
    
    print(f"\nAction selected: {response['action']}")
    print(f"Confidence: {response['confidence']:.3f}")
    print(f"Value estimate: {response['value_estimate']:.3f}")
    
    if response.get('text_response'):
        print(f"Response: {response['text_response']}")
    
    if response.get('emotion'):
        emotion = response['emotion']
        print(f"\nEmotion: {emotion.primary_emotion.value}")
        print(f"Valence: {emotion.valence:.3f}")
    
    print("\n✅ ALICE Brain integration test complete!")
    print("\n🎉 ALL 6 CORE SYSTEMS CREATED SUCCESSFULLY!")
