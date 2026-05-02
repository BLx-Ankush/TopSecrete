import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass
import re
from collections import defaultdict

@dataclass
class IntentClassification:
    """Represents classified intent from user input."""
    intent: str
    confidence: float
    entities: Dict[str, Any]
    sentiment: str
    urgency: float

@dataclass
class ConversationContext:
    """Maintains conversation context across turns."""
    topic: str
    history: List[Dict]
    user_profile: Dict[str, Any]
    current_state: str
    turn_count: int


class TransformerLanguageModel(nn.Module):
    """
    Advanced Transformer-based language understanding model.
    """
    
    def __init__(self,
                 vocab_size: int = 50000,
                 embedding_dim: int = 768,
                 num_heads: int = 12,
                 num_layers: int = 6,
                 ff_dim: int = 3072,
                 max_seq_length: int = 512,
                 dropout: float = 0.1):
        super(TransformerLanguageModel, self).__init__()
        
        self.embedding_dim = embedding_dim
        self.max_seq_length = max_seq_length
        
        # Token and position embeddings
        self.token_embedding = nn.Embedding(vocab_size, embedding_dim)
        self.position_embedding = nn.Embedding(max_seq_length, embedding_dim)
        
        # Transformer encoder layers
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        
        # Output projection
        self.output_projection = nn.Linear(embedding_dim, vocab_size)
        
        # Layer normalization
        self.layer_norm = nn.LayerNorm(embedding_dim)
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, 
                input_ids: torch.Tensor,
                attention_mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Forward pass for encoding."""
        batch_size, seq_length = input_ids.shape
        
        # Create position indices
        positions = torch.arange(seq_length, device=input_ids.device).unsqueeze(0).expand(batch_size, -1)
        
        # Embed tokens and positions
        token_embeddings = self.token_embedding(input_ids)
        position_embeddings = self.position_embedding(positions)
        
        # Combine embeddings
        embeddings = self.dropout(token_embeddings + position_embeddings)
        embeddings = self.layer_norm(embeddings)
        
        # Create attention mask if not provided
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids)
        
        # Convert attention mask to proper format
        attention_mask = attention_mask.bool()
        
        # Encode
        encoded = self.transformer_encoder(
            embeddings,
            src_key_padding_mask=~attention_mask
        )
        
        return encoded


class IntentClassifier(nn.Module):
    """Multi-task intent classification with entity extraction."""
    
    def __init__(self, 
                 input_dim: int = 768,
                 num_intents: int = 20,
                 num_entity_types: int = 10,
                 hidden_dim: int = 256):
        super(IntentClassifier, self).__init__()
        
        # Intent classification head
        self.intent_classifier = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, num_intents)
        )
        
        # Sentiment analysis head
        self.sentiment_analyzer = nn.Sequential(
            nn.Linear(input_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 3)  # Positive, Neutral, Negative
        )
        
        # Urgency predictor
        self.urgency_predictor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, 1),
            nn.Sigmoid()
        )
        
    def forward(self, encoded_input: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Multi-task forward pass."""
        # Use mean pooling for sequence-level classification
        pooled = encoded_input.mean(dim=1)
        
        # Compute all outputs
        intent_logits = self.intent_classifier(pooled)
        sentiment_logits = self.sentiment_analyzer(pooled)
        urgency = self.urgency_predictor(pooled)
        
        return {
            'intent': intent_logits,
            'sentiment': sentiment_logits,
            'urgency': urgency
        }


class ContextualConversationManager:
    """Manages conversation context and maintains dialogue state."""
    
    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self.current_context = None
        self.topic_transitions = []
        self.user_preferences = defaultdict(float)
        
        # Define intent categories
        self.intent_mapping = {
            0: "question",
            1: "command",
            2: "greeting",
            3: "farewell",
            4: "acknowledgment",
            5: "clarification_request",
            6: "complaint",
            7: "praise",
            8: "small_talk",
            9: "task_request",
            10: "information_query",
            11: "help_request",
            12: "correction",
            13: "agreement",
            14: "disagreement",
            15: "expression_emotion",
            16: "suggestion",
            17: "opinion",
            18: "confirmation",
            19: "cancellation"
        }
        
        self.entity_types = {
            0: "person",
            1: "location",
            2: "time",
            3: "date",
            4: "application",
            5: "file",
            6: "number",
            7: "url",
            8: "email",
            9: "organization"
        }
    
    def initialize_context(self, user_id: str) -> ConversationContext:
        """Initialize conversation context for a user."""
        self.current_context = ConversationContext(
            topic="general",
            history=[],
            user_profile=self._load_user_profile(user_id),
            current_state="idle",
            turn_count=0
        )
        return self.current_context
    
    def update_context(self, 
                      user_input: str,
                      intent: str,
                      entities: Dict[str, Any],
                      alice_response: str):
        """Update conversation context with new turn."""
        if self.current_context is None:
            self.current_context = self.initialize_context("default_user")
        
        # Add to history
        turn = {
            'turn': self.current_context.turn_count,
            'user_input': user_input,
            'intent': intent,
            'entities': entities,
            'alice_response': alice_response,
            'topic': self.current_context.topic
        }
        
        self.current_context.history.append(turn)
        self.current_context.turn_count += 1
        
        # Maintain history size
        if len(self.current_context.history) > self.max_history:
            self.current_context.history.pop(0)
        
        # Detect topic transition
        new_topic = self._detect_topic(user_input, entities)
        if new_topic != self.current_context.topic:
            self.topic_transitions.append({
                'from': self.current_context.topic,
                'to': new_topic,
                'turn': self.current_context.turn_count
            })
            self.current_context.topic = new_topic
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation context."""
        if not self.current_context:
            return {}
        
        return {
            'current_topic': self.current_context.topic,
            'conversation_length': self.current_context.turn_count,
            'recent_intents': [turn['intent'] for turn in self.current_context.history[-5:]],
            'user_engagement': self._calculate_engagement()
        }
    
    def get_relevant_history(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant conversation history for current query."""
        if not self.current_context or not self.current_context.history:
            return []
        
        # Simple relevance scoring
        scored_history = []
        query_words = set(query.lower().split())
        
        for turn in self.current_context.history:
            user_words = set(turn['user_input'].lower().split())
            relevance = len(query_words & user_words) / max(len(query_words), 1)
            
            # Boost recent turns
            recency_boost = 1.0 - (self.current_context.turn_count - turn['turn']) / self.max_history
            score = relevance * 0.7 + recency_boost * 0.3
            
            scored_history.append((score, turn))
        
        # Sort and return top-k
        scored_history.sort(reverse=True, key=lambda x: x[0])
        return [turn for score, turn in scored_history[:top_k]]
    
    def _detect_topic(self, user_input: str, entities: Dict[str, Any]) -> str:
        """Detect conversation topic from input and entities."""
        user_lower = user_input.lower()
        
        # Topic keywords
        topic_keywords = {
            'weather': ['weather', 'temperature', 'forecast', 'rain', 'snow'],
            'technology': ['computer', 'software', 'app', 'program', 'code'],
            'entertainment': ['movie', 'music', 'game', 'video', 'watch'],
            'work': ['work', 'job', 'office', 'meeting', 'project'],
            'personal': ['feel', 'emotion', 'life', 'friend', 'family'],
            'help': ['help', 'support', 'assist', 'problem', 'issue']
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in user_lower for keyword in keywords):
                return topic
        
        return 'general'
    
    def _calculate_engagement(self) -> float:
        """Calculate user engagement score."""
        if not self.current_context or self.current_context.turn_count == 0:
            return 0.5
        
        # Factors: conversation length, response variety
        length_score = min(self.current_context.turn_count / 10, 1.0)
        
        # Count different intent types
        intents = [turn['intent'] for turn in self.current_context.history]
        variety_score = len(set(intents)) / max(len(intents), 1)
        
        engagement = (length_score * 0.5 + variety_score * 0.5)
        return engagement
    
    def _load_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Load user profile."""
        return {
            'user_id': user_id,
            'language': 'en',
            'preferences': {},
            'history_summary': {}
        }


class ResponseGenerator:
    """Natural language response generation with personality."""
    
    def __init__(self, personality: str = "helpful"):
        self.personality = personality
        
        self.personality_traits = {
            'helpful': {'tone': 'supportive', 'verbosity': 0.7, 'enthusiasm': 0.6},
            'professional': {'tone': 'neutral', 'verbosity': 0.5, 'enthusiasm': 0.3},
            'friendly': {'tone': 'warm', 'verbosity': 0.8, 'enthusiasm': 0.9},
            'concise': {'tone': 'direct', 'verbosity': 0.3, 'enthusiasm': 0.4}
        }
        
        self.current_traits = self.personality_traits.get(personality, 
                                                         self.personality_traits['helpful'])
    
    def generate_response(self,
                         intent: str,
                         context: Dict[str, Any],
                         action_result: Optional[Dict] = None) -> str:
        """Generate contextual response based on intent and context."""
        
        # Response templates based on intent
        templates = {
            'greeting': self._generate_greeting(context),
            'farewell': self._generate_farewell(context),
            'question': self._generate_question_response(context, action_result),
            'command': self._generate_command_response(context, action_result),
            'help_request': "I'm here to help! What do you need assistance with?"
        }
        
        response = templates.get(intent, "I understand. How can I help you further?")
        
        return self._apply_personality(response)
    
    def _generate_greeting(self, context: Dict[str, Any]) -> str:
        """Generate greeting based on context."""
        greetings = {
            'helpful': ["Hello! I'm Alice. How can I help you today?",
                       "Hi there! I'm ready to assist you."],
            'professional': ["Good day. How may I assist you?",
                           "Hello. I'm Alice, your AI assistant."],
            'friendly': ["Hey! Great to see you!",
                        "Hi! I'm Alice, and I'm excited to help!"],
            'concise': ["Hello. How can I help?"]
        }
        
        return np.random.choice(greetings[self.personality])
    
    def _generate_farewell(self, context: Dict[str, Any]) -> str:
        """Generate farewell."""
        return "Goodbye! Have a great day!"
    
    def _generate_question_response(self, context: Dict, action_result: Optional[Dict]) -> str:
        """Generate response to a question."""
        if action_result and action_result.get('answer'):
            return action_result['answer']
        return "That's an interesting question. Let me find the answer for you."
    
    def _generate_command_response(self, context: Dict, action_result: Optional[Dict]) -> str:
        """Generate response to a command."""
        if action_result and action_result.get('status') == 'success':
            return "Done! Task completed successfully."
        return "I'm working on that for you."
    
    def _apply_personality(self, response: str) -> str:
        """Apply personality traits to response."""
        if self.current_traits['enthusiasm'] > 0.7 and not response.endswith('!'):
            if np.random.random() > 0.5:
                response = response.rstrip('.') + '!'
        
        return response


class NLPPipeline:
    """Complete NLP pipeline integrating all components."""
    
    def __init__(self, model_path: Optional[str] = None):
        # Initialize components
        self.language_model = TransformerLanguageModel()
        self.intent_classifier = IntentClassifier()
        self.context_manager = ContextualConversationManager()
        self.response_generator = ResponseGenerator(personality="helpful")
        
        if model_path:
            self.load_model(model_path)
    
    def process(self, user_input: str, user_id: str = "default") -> Dict[str, Any]:
        """Process user input through complete NLP pipeline."""
        
        # Initialize context if needed
        if self.context_manager.current_context is None:
            self.context_manager.initialize_context(user_id)
        
        # Tokenize and encode (simplified)
        input_ids = self._tokenize(user_input)
        
        # Encode with language model
        with torch.no_grad():
            encoded = self.language_model(input_ids)
            
            # Classify intent
            classification = self.intent_classifier(encoded)
        
        # Get intent
        intent_id = torch.argmax(classification['intent'], dim=-1).item()
        intent = self.context_manager.intent_mapping.get(intent_id, "unknown")
        
        # Get sentiment
        sentiment_id = torch.argmax(classification['sentiment'], dim=-1).item()
        sentiments = ['positive', 'neutral', 'negative']
        sentiment = sentiments[sentiment_id]
        
        # Get urgency
        urgency = classification['urgency'].item()
        
        # Extract entities (simplified)
        entities = {}
        
        # Get relevant conversation history
        relevant_history = self.context_manager.get_relevant_history(user_input)
        
        # Generate response
        context = {
            'user_input': user_input,
            'intent': intent,
            'sentiment': sentiment,
            'urgency': urgency,
            'entities': entities,
            'relevant_history': relevant_history
        }
        
        response = self.response_generator.generate_response(intent, context)
        
        # Update context
        self.context_manager.update_context(
            user_input, intent, entities, response
        )
        
        return {
            'intent': intent,
            'confidence': torch.max(F.softmax(classification['intent'], dim=-1)).item(),
            'sentiment': sentiment,
            'urgency': urgency,
            'entities': entities,
            'response': response,
            'context_summary': self.context_manager.get_context_summary()
        }
    
    def _tokenize(self, text: str) -> torch.Tensor:
        """Simplified tokenization."""
        words = text.lower().split()
        token_ids = [hash(word) % 50000 for word in words]
        return torch.tensor([token_ids[:512]])  # Truncate to max length
    
    def save_model(self, filepath: str):
        """Save NLP models."""
        torch.save({
            'language_model': self.language_model.state_dict(),
            'intent_classifier': self.intent_classifier.state_dict()
        }, filepath)
    
    def load_model(self, filepath: str):
        """Load NLP models."""
        checkpoint = torch.load(filepath)
        self.language_model.load_state_dict(checkpoint['language_model'])
        self.intent_classifier.load_state_dict(checkpoint['intent_classifier'])


if __name__ == "__main__":
    print("Testing NLP Pipeline...")
    
    nlp = NLPPipeline()
    
    test_inputs = [
        "Hello! Can you help me?",
        "What's the weather like?",
        "Thank you!"
    ]
    
    for test_input in test_inputs:
        result = nlp.process(test_input)
        print(f"Input: {test_input}")
        print(f"Intent: {result['intent']} (confidence: {result['confidence']:.3f})")
        print(f"Response: {result['response']}\n")
    
    print("✅ NLP Pipeline test complete!")
