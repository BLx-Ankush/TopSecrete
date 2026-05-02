import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass
from enum import Enum


class EmotionType(Enum):
    """Basic emotion types based on psychological research."""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    NEUTRAL = "neutral"


class PersonalityTrait(Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


@dataclass
class EmotionState:
    """Current emotional state."""
    primary_emotion: EmotionType
    emotion_intensities: Dict[EmotionType, float]
    valence: float  # Positive/negative (-1 to 1)
    arousal: float  # Activation level (0 to 1)
    dominance: float  # Control/submissiveness (0 to 1)


@dataclass
class PersonalityProfile:
    """Personality profile based on Big Five."""
    traits: Dict[PersonalityTrait, float]
    adaptability: float
    learning_rate_modifier: float
    risk_tolerance: float


class EmotionRecognitionNetwork(nn.Module):
    """Neural network for recognizing emotions from state."""
    
    def __init__(self,
                 input_dim: int = 1024,
                 hidden_dim: int = 512,
                 num_emotions: int = 9):
        super(EmotionRecognitionNetwork, self).__init__()
        
        # Multi-layer recognition network
        self.recognition_network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, num_emotions)
        )
        
        # Valence-Arousal-Dominance (VAD) predictor
        self.vad_predictor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 3),
            nn.Tanh()
        )
        
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Recognize emotion from state.
        
        Returns:
            emotion_logits: Logits for each emotion class
            vad: Valence, Arousal, Dominance values
        """
        emotion_logits = self.recognition_network(state)
        vad = self.vad_predictor(state)
        
        return emotion_logits, vad


class EmotionDynamicsModel(nn.Module):
    """
    Models emotion dynamics and transitions over time.
    Based on psychological theories of emotion regulation.
    """
    
    def __init__(self,
                 emotion_dim: int = 9,
                 hidden_dim: int = 256):
        super(EmotionDynamicsModel, self).__init__()
        
        self.emotion_dim = emotion_dim
        
        # Emotion transition network (models how emotions evolve)
        self.transition_lstm = nn.LSTM(
            emotion_dim,
            hidden_dim,
            num_layers=2,
            batch_first=True,
            dropout=0.2
        )
        
        # Emotion decay network (emotions fade over time)
        self.decay_network = nn.Sequential(
            nn.Linear(emotion_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, emotion_dim),
            nn.Sigmoid()
        )
        
        # Emotion amplification (based on personality and context)
        self.amplification_network = nn.Sequential(
            nn.Linear(emotion_dim + 5, hidden_dim),  # +5 for personality traits
            nn.ReLU(),
            nn.Linear(hidden_dim, emotion_dim),
            nn.Tanh()
        )
        
        # Projection to next emotional state
        self.projection = nn.Linear(hidden_dim, emotion_dim)
        
    def forward(self,
                current_emotion: torch.Tensor,
                personality: torch.Tensor,
                event_impact: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Predict next emotional state given current state and personality.
        
        Args:
            current_emotion: Current emotion intensities
            personality: Personality trait values
            event_impact: Optional external event impact
        
        Returns:
            next_emotion: Predicted next emotional state
        """
        batch_size = current_emotion.shape[0]
        
        # Model natural emotion decay
        decay_factor = self.decay_network(current_emotion)
        decayed_emotion = current_emotion * decay_factor
        
        # Apply personality-based amplification/dampening
        emotion_personality = torch.cat([current_emotion, personality], dim=-1)
        amplification = self.amplification_network(emotion_personality)
        modulated_emotion = decayed_emotion + amplification * 0.1
        
        # If there's an event, incorporate its impact
        if event_impact is not None:
            modulated_emotion = modulated_emotion + event_impact
        
        # Model temporal dynamics with LSTM
        emotion_sequence = modulated_emotion.unsqueeze(1)
        lstm_out, _ = self.transition_lstm(emotion_sequence)
        
        # Project to next state
        next_emotion = self.projection(lstm_out.squeeze(1))
        next_emotion = torch.sigmoid(next_emotion)
        
        return next_emotion


class PersonalityModel(nn.Module):
    """
    Models ALICE's personality based on Big Five traits.
    Influences emotion dynamics and decision making.
    """
    
    def __init__(self,
                 state_dim: int = 1024,
                 hidden_dim: int = 256):
        super(PersonalityModel, self).__init__()
        
        # Personality encoder (learns personality from behavior)
        self.personality_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 5),  # Big Five traits
            nn.Sigmoid()
        )
        
        # Personality-based behavior modifier
        self.behavior_modifier = nn.Sequential(
            nn.Linear(5 + state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, state_dim)
        )
        
        # Initialize with default balanced personality
        self.default_personality = nn.Parameter(
            torch.tensor([0.5, 0.5, 0.5, 0.5, 0.5]),
            requires_grad=False
        )
        
    def forward(self,
                state: torch.Tensor,
                learned_personality: Optional[torch.Tensor] = None) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Apply personality to modify behavior.
        
        Args:
            state: Current state
            learned_personality: Optional pre-learned personality traits
        
        Returns:
            personality_traits: The personality trait values
            modified_state: State modified by personality
        """
        if learned_personality is None:
            personality_traits = self.personality_encoder(state)
        else:
            personality_traits = learned_personality
        
        # Modify state based on personality
        combined = torch.cat([personality_traits, state], dim=-1)
        modification = self.behavior_modifier(combined)
        modified_state = state + modification * 0.1
        
        return personality_traits, modified_state


class EmotionalIntelligenceModule(nn.Module):
    """
    Emotional intelligence for understanding and responding to emotions.
    """
    
    def __init__(self,
                 emotion_dim: int = 9,
                 context_dim: int = 768,
                 hidden_dim: int = 256):
        super(EmotionalIntelligenceModule, self).__init__()
        
        # Empathy network (understand others' emotions)
        self.empathy_network = nn.Sequential(
            nn.Linear(context_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, emotion_dim),
            nn.Softmax(dim=-1)
        )
        
        # Emotional response generator
        self.response_network = nn.Sequential(
            nn.Linear(emotion_dim * 2 + context_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, emotion_dim)
        )
        
        # Emotion regulation (managing own emotions)
        self.regulation_network = nn.Sequential(
            nn.Linear(emotion_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, emotion_dim),
            nn.Sigmoid()
        )
        
    def perceive_emotion(self, context: torch.Tensor) -> torch.Tensor:
        """Perceive emotion from context (e.g., user's emotion)."""
        return self.empathy_network(context)
    
    def generate_response(self,
                         own_emotion: torch.Tensor,
                         perceived_emotion: torch.Tensor,
                         context: torch.Tensor) -> torch.Tensor:
        """Generate emotional response to situation."""
        combined = torch.cat([own_emotion, perceived_emotion, context], dim=-1)
        return self.response_network(combined)
    
    def regulate_emotion(self, emotion: torch.Tensor) -> torch.Tensor:
        """Regulate emotion intensity."""
        regulation_factor = self.regulation_network(emotion)
        return emotion * regulation_factor


class EmotionBasedRewardShaper:
    """
    Shapes RL rewards based on emotional state and personality.
    Makes ALICE's learning more human-like.
    """
    
    def __init__(self,
                 emotion_weights: Optional[Dict[EmotionType, float]] = None):
        
        # Default emotion-reward mappings
        self.emotion_weights = emotion_weights or {
            EmotionType.JOY: 1.0,
            EmotionType.TRUST: 0.8,
            EmotionType.ANTICIPATION: 0.5,
            EmotionType.SURPRISE: 0.2,
            EmotionType.NEUTRAL: 0.0,
            EmotionType.FEAR: -0.5,
            EmotionType.ANGER: -0.6,
            EmotionType.DISGUST: -0.7,
            EmotionType.SADNESS: -0.8
        }
        
    def shape_reward(self,
                    base_reward: float,
                    emotion_state: EmotionState,
                    personality: PersonalityProfile) -> float:
        """
        Shape reward based on emotion and personality.
        
        Args:
            base_reward: Original RL reward
            emotion_state: Current emotional state
            personality: Personality profile
        
        Returns:
            shaped_reward: Modified reward
        """
        
        # Emotional contribution to reward
        emotion_bonus = sum(
            intensity * self.emotion_weights.get(emotion, 0.0)
            for emotion, intensity in emotion_state.emotion_intensities.items()
        )
        
        # Personality modulation
        # High neuroticism amplifies negative emotions
        neuroticism = personality.traits.get(PersonalityTrait.NEUROTICISM, 0.5)
        if emotion_bonus < 0:
            emotion_bonus *= (1.0 + neuroticism * 0.5)
        
        # High openness encourages exploration (positive surprise)
        openness = personality.traits.get(PersonalityTrait.OPENNESS, 0.5)
        if emotion_state.primary_emotion == EmotionType.SURPRISE and emotion_bonus > 0:
            emotion_bonus *= (1.0 + openness * 0.3)
        
        # Valence-based scaling
        valence_scale = 1.0 + emotion_state.valence * 0.2
        
        # Combine base reward with emotional shaping
        shaped_reward = base_reward * valence_scale + emotion_bonus * 0.1
        
        return shaped_reward
    
    def get_intrinsic_motivation(self,
                                 emotion_state: EmotionState,
                                 personality: PersonalityProfile) -> float:
        """
        Calculate intrinsic motivation from emotional state.
        """
        # High arousal increases motivation
        arousal_boost = emotion_state.arousal * 0.5
        
        # Positive emotions increase motivation
        valence_boost = max(0, emotion_state.valence) * 0.3
        
        # Conscientiousness increases baseline motivation
        conscientiousness = personality.traits.get(PersonalityTrait.CONSCIENTIOUSNESS, 0.5)
        baseline = conscientiousness * 0.2
        
        intrinsic_motivation = baseline + arousal_boost + valence_boost
        
        return intrinsic_motivation


class PersonalityEmotionSystem:
    """
    Complete personality and emotion system for ALICE.
    Integrates emotion recognition, dynamics, personality, and emotional intelligence.
    """
    
    def __init__(self, device: str = 'cpu'):
        self.device = device
        
        # Initialize components
        self.emotion_recognizer = EmotionRecognitionNetwork().to(device)
        self.emotion_dynamics = EmotionDynamicsModel().to(device)
        self.personality_model = PersonalityModel().to(device)
        self.emotional_intelligence = EmotionalIntelligenceModule().to(device)
        self.reward_shaper = EmotionBasedRewardShaper()
        
        # Current state
        self.current_emotion_state: Optional[EmotionState] = None
        self.current_personality: Optional[PersonalityProfile] = None
        
        # Emotion history
        self.emotion_history: List[EmotionState] = []
        self.max_history = 100
        
        # Initialize with neutral state
        self._initialize_state()
        
    def _initialize_state(self):
        """Initialize with neutral emotional state and balanced personality."""
        
        # Neutral emotion state
        neutral_intensities = {emotion: 0.0 for emotion in EmotionType}
        neutral_intensities[EmotionType.NEUTRAL] = 1.0
        
        self.current_emotion_state = EmotionState(
            primary_emotion=EmotionType.NEUTRAL,
            emotion_intensities=neutral_intensities,
            valence=0.0,
            arousal=0.3,
            dominance=0.5
        )
        
        # Balanced personality
        balanced_traits = {trait: 0.5 for trait in PersonalityTrait}
        
        self.current_personality = PersonalityProfile(
            traits=balanced_traits,
            adaptability=0.7,
            learning_rate_modifier=1.0,
            risk_tolerance=0.5
        )
        
    def process_state(self,
                     state: torch.Tensor,
                     context: Optional[torch.Tensor] = None,
                     event_impact: Optional[torch.Tensor] = None) -> Tuple[EmotionState, PersonalityProfile]:
        """
        Process current state to update emotions and personality.
        
        Args:
            state: Current fused state representation
            context: Optional context information
            event_impact: Optional external event impact
        
        Returns:
            Updated emotion state and personality profile
        """
        
        with torch.no_grad():
            # Recognize current emotion from state
            emotion_logits, vad = self.emotion_recognizer(state)
            emotion_probs = F.softmax(emotion_logits, dim=-1)
            
            # Extract personality traits
            personality_traits, _ = self.personality_model(state)
            
            # Update emotion dynamics
            current_emotion_tensor = torch.tensor(
                [self.current_emotion_state.emotion_intensities.get(e, 0.0) 
                 for e in EmotionType],
                dtype=torch.float32,
                device=self.device
            ).unsqueeze(0)
            
            next_emotion = self.emotion_dynamics(
                current_emotion_tensor,
                personality_traits,
                event_impact
            )
            
            # Blend recognized emotion with dynamics
            blended_emotion = 0.7 * next_emotion + 0.3 * emotion_probs
            
            # Apply emotional regulation if needed
            if context is not None:
                perceived_emotion = self.emotional_intelligence.perceive_emotion(context)
                emotional_response = self.emotional_intelligence.generate_response(
                    blended_emotion,
                    perceived_emotion,
                    context
                )
                blended_emotion = self.emotional_intelligence.regulate_emotion(
                    blended_emotion + emotional_response * 0.1
                )
            
            # Convert to emotion state
            emotion_intensities_list = blended_emotion.squeeze(0).cpu().numpy()
            emotion_intensities = {
                emotion: float(intensity)
                for emotion, intensity in zip(EmotionType, emotion_intensities_list)
            }
            
            primary_emotion_idx = np.argmax(emotion_intensities_list)
            primary_emotion = list(EmotionType)[primary_emotion_idx]
            
            # Extract VAD
            vad_values = vad.squeeze(0).cpu().numpy()
            
            # Create emotion state
            emotion_state = EmotionState(
                primary_emotion=primary_emotion,
                emotion_intensities=emotion_intensities,
                valence=float(vad_values[0]),
                arousal=float(vad_values[1]),
                dominance=float(vad_values[2])
            )
            
            # Create personality profile
            personality_traits_values = personality_traits.squeeze(0).cpu().numpy()
            personality_dict = {
                trait: float(value)
                for trait, value in zip(PersonalityTrait, personality_traits_values)
            }
            
            # Calculate derived personality attributes
            adaptability = (personality_dict[PersonalityTrait.OPENNESS] + 
                          personality_dict[PersonalityTrait.EXTRAVERSION]) / 2
            
            learning_rate_modifier = 0.5 + personality_dict[PersonalityTrait.CONSCIENTIOUSNESS] * 0.5
            
            risk_tolerance = (personality_dict[PersonalityTrait.OPENNESS] + 
                            (1.0 - personality_dict[PersonalityTrait.NEUROTICISM])) / 2
            
            personality_profile = PersonalityProfile(
                traits=personality_dict,
                adaptability=float(adaptability),
                learning_rate_modifier=float(learning_rate_modifier),
                risk_tolerance=float(risk_tolerance)
            )
            
            # Update current state
            self.current_emotion_state = emotion_state
            self.current_personality = personality_profile
            
            # Add to history
            self.emotion_history.append(emotion_state)
            if len(self.emotion_history) > self.max_history:
                self.emotion_history.pop(0)
            
            return emotion_state, personality_profile
    
    def shape_reward(self, base_reward: float) -> float:
        """Shape reward based on current emotional state and personality."""
        if self.current_emotion_state and self.current_personality:
            return self.reward_shaper.shape_reward(
                base_reward,
                self.current_emotion_state,
                self.current_personality
            )
        return base_reward
    
    def get_intrinsic_motivation(self) -> float:
        """Get current intrinsic motivation level."""
        if self.current_emotion_state and self.current_personality:
            return self.reward_shaper.get_intrinsic_motivation(
                self.current_emotion_state,
                self.current_personality
            )
        return 0.5
    
    def get_emotion_summary(self) -> Dict[str, Any]:
        """Get summary of current emotional state."""
        if not self.current_emotion_state:
            return {}
        
        return {
            'primary_emotion': self.current_emotion_state.primary_emotion.value,
            'valence': self.current_emotion_state.valence,
            'arousal': self.current_emotion_state.arousal,
            'dominance': self.current_emotion_state.dominance,
            'top_emotions': sorted(
                self.current_emotion_state.emotion_intensities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        }
    
    def get_personality_summary(self) -> Dict[str, Any]:
        """Get summary of personality profile."""
        if not self.current_personality:
            return {}
        
        return {
            'traits': {k.value: v for k, v in self.current_personality.traits.items()},
            'adaptability': self.current_personality.adaptability,
            'learning_rate_modifier': self.current_personality.learning_rate_modifier,
            'risk_tolerance': self.current_personality.risk_tolerance
        }
    
    def save_models(self, filepath: str):
        """Save emotion and personality models."""
        torch.save({
            'emotion_recognizer': self.emotion_recognizer.state_dict(),
            'emotion_dynamics': self.emotion_dynamics.state_dict(),
            'personality_model': self.personality_model.state_dict(),
            'emotional_intelligence': self.emotional_intelligence.state_dict()
        }, filepath)
    
    def load_models(self, filepath: str):
        """Load emotion and personality models."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.emotion_recognizer.load_state_dict(checkpoint['emotion_recognizer'])
        self.emotion_dynamics.load_state_dict(checkpoint['emotion_dynamics'])
        self.personality_model.load_state_dict(checkpoint['personality_model'])
        self.emotional_intelligence.load_state_dict(checkpoint['emotional_intelligence'])


if __name__ == "__main__":
    print("Testing Personality & Emotion System...")
    
    system = PersonalityEmotionSystem(device='cpu')
    
    # Test with dummy state
    dummy_state = torch.randn(1, 1024)
    dummy_context = torch.randn(1, 768)
    
    print("Processing emotional state...")
    emotion_state, personality = system.process_state(dummy_state, dummy_context)
    
    print(f"\nEmotion Summary:")
    emotion_summary = system.get_emotion_summary()
    print(f"  Primary: {emotion_summary['primary_emotion']}")
    print(f"  Valence: {emotion_summary['valence']:.3f}")
    print(f"  Arousal: {emotion_summary['arousal']:.3f}")
    
    print(f"\nPersonality Summary:")
    personality_summary = system.get_personality_summary()
    print(f"  Adaptability: {personality_summary['adaptability']:.3f}")
    print(f"  Risk Tolerance: {personality_summary['risk_tolerance']:.3f}")
    
    # Test reward shaping
    base_reward = 10.0
    shaped_reward = system.shape_reward(base_reward)
    print(f"\nReward Shaping:")
    print(f"  Base: {base_reward}")
    print(f"  Shaped: {shaped_reward:.3f}")
    
    print("\n✅ Personality & Emotion System test complete!")
