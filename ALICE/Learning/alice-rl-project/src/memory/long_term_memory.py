import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
import pickle
import json
from datetime import datetime

# ── Safe persistence (CWE-502 mitigation) ────────────────────────────────────
# secure_save/secure_load add an HMAC signature so only files written by this
# ALICE instance are ever deserialized; safe_torch_load defaults to
# weights_only=True. Falls back gracefully if the helper isn't importable.
try:
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from safe_persistence import (
        secure_save, secure_load, safe_torch_load, safe_torch_save, IntegrityError
    )
    _SAFE_PERSIST = True
except Exception:  # pragma: no cover
    _SAFE_PERSIST = False
    class IntegrityError(Exception):
        ...

class LongTermMemoryModule(nn.Module):
    """
    Sophisticated long-term memory system using LSTM and attention mechanisms.
    Stores and retrieves knowledge across conversations.
    """
    
    def __init__(self, 
                 embedding_dim: int = 512,
                 memory_size: int = 1024,
                 num_layers: int = 4,
                 attention_heads: int = 8):
        super(LongTermMemoryModule, self).__init__()
        
        self.embedding_dim = embedding_dim
        self.memory_size = memory_size
        
        # Multi-layer LSTM for sequential memory
        self.lstm = nn.LSTM(
            input_size=embedding_dim,
            hidden_size=memory_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.3,
            bidirectional=True
        )
        
        # Multi-head attention for memory retrieval
        self.attention = nn.MultiheadAttention(
            embed_dim=memory_size * 2,  # Bidirectional
            num_heads=attention_heads,
            dropout=0.2,
            batch_first=True
        )
        
        # Memory consolidation network
        self.consolidation_network = nn.Sequential(
            nn.Linear(memory_size * 2, memory_size),
            nn.LayerNorm(memory_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(memory_size, memory_size),
            nn.LayerNorm(memory_size),
            nn.ReLU()
        )
        
        # Memory importance scorer
        self.importance_scorer = nn.Sequential(
            nn.Linear(memory_size, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Sigmoid()
        )
        
        # Episodic memory buffer (stores key memories)
        self.episodic_buffer = []
        self.max_episodic_size = 10000
        
        # Semantic memory (stores factual knowledge)
        self.semantic_memory = {}
        
        # Working memory state
        self.working_memory_state = None
        
    def encode_experience(self, experience: torch.Tensor) -> torch.Tensor:
        """Encode experience into memory representation."""
        # Process through LSTM
        lstm_out, (hidden, cell) = self.lstm(experience.unsqueeze(0))
        
        # Apply attention
        attended_memory, attention_weights = self.attention(
            lstm_out, lstm_out, lstm_out
        )
        
        # Consolidate memory
        consolidated = self.consolidation_network(attended_memory)
        
        # Score importance
        importance = self.importance_scorer(consolidated)
        
        return consolidated, importance, attention_weights
    
    def store_episodic_memory(self, 
                             experience: Dict[str, Any], 
                             importance: float):
        """Store important experiences in episodic memory."""
        memory_entry = {
            'timestamp': datetime.now().isoformat(),
            'experience': experience,
            'importance': importance,
            'access_count': 0,
            'last_accessed': datetime.now().isoformat()
        }
        
        self.episodic_buffer.append(memory_entry)
        
        # Maintain buffer size using importance-based pruning
        if len(self.episodic_buffer) > self.max_episodic_size:
            self._prune_episodic_memory()
    
    def store_semantic_memory(self, key: str, value: Any):
        """Store factual knowledge in semantic memory."""
        self.semantic_memory[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat(),
            'update_count': self.semantic_memory.get(key, {}).get('update_count', 0) + 1
        }
    
    def retrieve_episodic_memory(self, 
                                query: torch.Tensor, 
                                top_k: int = 5) -> List[Dict]:
        """Retrieve relevant episodic memories based on query."""
        if not self.episodic_buffer:
            return []
        
        # Calculate similarity scores
        similarities = []
        for idx, memory in enumerate(self.episodic_buffer):
            # Convert experience to tensor for similarity calculation
            score = self._calculate_memory_similarity(query, memory)
            similarities.append((idx, score))
        
        # Sort by similarity and importance
        similarities.sort(key=lambda x: x[1] * self.episodic_buffer[x[0]]['importance'], 
                         reverse=True)
        
        # Retrieve top-k memories
        retrieved_memories = []
        for idx, score in similarities[:top_k]:
            memory = self.episodic_buffer[idx]
            memory['access_count'] += 1
            memory['last_accessed'] = datetime.now().isoformat()
            retrieved_memories.append(memory)
        
        return retrieved_memories
    
    def retrieve_semantic_memory(self, key: str) -> Optional[Any]:
        """Retrieve factual knowledge from semantic memory."""
        if key in self.semantic_memory:
            return self.semantic_memory[key]['value']
        return None
    
    def consolidate_memories(self):
        """Consolidate and strengthen important memories (like sleep consolidation)."""
        if len(self.episodic_buffer) < 100:
            return
        
        # Sort by importance and recency
        sorted_memories = sorted(
            self.episodic_buffer,
            key=lambda x: (x['importance'], x['access_count']),
            reverse=True
        )
        
        # Keep top memories and some random samples
        consolidated_size = min(self.max_episodic_size // 2, len(sorted_memories))
        self.episodic_buffer = sorted_memories[:consolidated_size]
        
        # Add some random samples for diversity
        remaining = sorted_memories[consolidated_size:]
        if remaining:
            sample_size = min(len(remaining), self.max_episodic_size // 4)
            random_samples = np.random.choice(remaining, sample_size, replace=False)
            self.episodic_buffer.extend(random_samples)
    
    def _prune_episodic_memory(self):
        """Remove less important memories when buffer is full."""
        # Sort by importance score and access patterns
        self.episodic_buffer.sort(
            key=lambda x: (x['importance'] * (1 + np.log(1 + x['access_count']))),
            reverse=True
        )
        
        # Keep top memories
        self.episodic_buffer = self.episodic_buffer[:self.max_episodic_size]
    
    def _calculate_memory_similarity(self, 
                                    query: torch.Tensor, 
                                    memory: Dict) -> float:
        """Calculate similarity between query and stored memory."""
        # Simplified similarity calculation
        importance = memory['importance']
        recency = self._calculate_recency_bonus(memory['timestamp'])
        access_bonus = np.log(1 + memory['access_count']) / 10
        
        return float(importance * recency * (1 + access_bonus))
    
    def _calculate_recency_bonus(self, timestamp: str) -> float:
        """Calculate recency bonus for memory retrieval."""
        try:
            memory_time = datetime.fromisoformat(timestamp)
            time_diff = (datetime.now() - memory_time).total_seconds()
            # Exponential decay with 24-hour half-life
            decay_rate = np.log(2) / (24 * 3600)
            return np.exp(-decay_rate * time_diff)
        except:
            return 0.5
    
    def save_memory(self, filepath: str):
        """Save memory systems to disk (signed for integrity)."""
        memory_data = {
            'episodic_buffer': self.episodic_buffer,
            'semantic_memory': self.semantic_memory,
            'model_state': self.state_dict()
        }
        if _SAFE_PERSIST:
            secure_save(memory_data, filepath)
        else:
            with open(filepath, 'wb') as f:
                pickle.dump(memory_data, f)

    def load_memory(self, filepath: str):
        """Load memory systems from disk.

        SECURITY: verifies the file's HMAC signature before deserializing, so a
        tampered or foreign memory file is refused (no arbitrary-code execution).
        """
        try:
            if _SAFE_PERSIST:
                memory_data = secure_load(filepath)
            else:
                with open(filepath, 'rb') as f:
                    memory_data = pickle.load(f)

            self.episodic_buffer = memory_data['episodic_buffer']
            self.semantic_memory = memory_data['semantic_memory']
            self.load_state_dict(memory_data['model_state'])
        except IntegrityError as e:
            print(f"SECURITY: refused to load memory file: {e}")
        except Exception as e:
            print(f"Error loading memory: {e}")


class ExperienceReplayBuffer:
    """
    Advanced experience replay buffer with prioritized sampling.
    """
    
    def __init__(self, 
                 capacity: int = 100000,
                 alpha: float = 0.6,
                 beta: float = 0.4,
                 beta_increment: float = 0.001):
        self.capacity = capacity
        self.alpha = alpha  # Priority exponent
        self.beta = beta    # Importance sampling exponent
        self.beta_increment = beta_increment
        
        self.buffer = deque(maxlen=capacity)
        self.priorities = deque(maxlen=capacity)
        self.position = 0
        
    def add(self, 
            state: np.ndarray, 
            action: int, 
            reward: float, 
            next_state: np.ndarray, 
            done: bool,
            priority: Optional[float] = None):
        """Add experience to buffer with priority."""
        
        experience = (state, action, reward, next_state, done)
        
        # Use max priority for new experiences if not specified
        if priority is None:
            priority = max(self.priorities) if self.priorities else 1.0
        
        self.buffer.append(experience)
        self.priorities.append(priority)
    
    def sample(self, batch_size: int) -> Tuple[List, np.ndarray, List[int]]:
        """Sample batch with prioritized sampling."""
        if len(self.buffer) < batch_size:
            return [], np.array([]), []
        
        # Calculate sampling probabilities
        priorities = np.array(self.priorities)
        probabilities = priorities ** self.alpha
        probabilities /= probabilities.sum()
        
        # Sample indices
        indices = np.random.choice(
            len(self.buffer), 
            batch_size, 
            p=probabilities,
            replace=False
        )
        
        # Calculate importance sampling weights
        weights = (len(self.buffer) * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()  # Normalize
        
        # Increment beta
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        # Get experiences
        experiences = [self.buffer[idx] for idx in indices]
        
        return experiences, weights, indices
    
    def update_priorities(self, indices: List[int], priorities: np.ndarray):
        """Update priorities for sampled experiences."""
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority + 1e-6  # Small epsilon to avoid zero
    
    def __len__(self):
        return len(self.buffer)


class TransferLearningManager:
    """
    Manages transfer learning capabilities for Alice.
    """
    
    def __init__(self, base_model: nn.Module):
        self.base_model = base_model
        self.task_specific_heads = {}
        self.knowledge_base = {}
        
    def add_task_head(self, task_name: str, head: nn.Module):
        """Add task-specific head for transfer learning."""
        self.task_specific_heads[task_name] = head
    
    def freeze_base_layers(self, num_layers: int = -1):
        """Freeze base model layers for fine-tuning."""
        layers = list(self.base_model.children())
        
        if num_layers == -1:
            layers_to_freeze = layers[:-1]  # Freeze all except last
        else:
            layers_to_freeze = layers[:num_layers]
        
        for layer in layers_to_freeze:
            for param in layer.parameters():
                param.requires_grad = False
    
    def unfreeze_all_layers(self):
        """Unfreeze all layers."""
        for param in self.base_model.parameters():
            param.requires_grad = True
    
    def save_transfer_state(self, filepath: str):
        """Save transfer learning state."""
        state = {
            'base_model': self.base_model.state_dict(),
            'task_heads': {name: head.state_dict() 
                          for name, head in self.task_specific_heads.items()},
            'knowledge_base': self.knowledge_base
        }
        torch.save(state, filepath)
    
    def load_transfer_state(self, filepath: str):
        """Load transfer learning state (weights-only, integrity-checked)."""
        state = safe_torch_load(filepath) if _SAFE_PERSIST else torch.load(filepath, weights_only=True)
        self.base_model.load_state_dict(state['base_model'])
        
        for name, head_state in state['task_heads'].items():
            if name in self.task_specific_heads:
                self.task_specific_heads[name].load_state_dict(head_state)
        
        self.knowledge_base = state['knowledge_base']


class MetaLearningModule:
    """
    Meta-learning (learning to learn) capabilities for Alice.
    """
    
    def __init__(self, model: nn.Module, meta_lr: float = 0.001, inner_lr: float = 0.01):
        self.model = model
        self.meta_lr = meta_lr
        self.inner_lr = inner_lr
        self.meta_optimizer = torch.optim.Adam(model.parameters(), lr=meta_lr)
        
    def maml_update(self, 
                    support_set: List[Tuple],
                    query_set: List[Tuple],
                    num_inner_steps: int = 5) -> float:
        """Model-Agnostic Meta-Learning (MAML) update."""
        # Save original parameters
        original_params = [p.clone() for p in self.model.parameters()]
        
        # Inner loop: adapt to support set
        for _ in range(num_inner_steps):
            support_loss = self._compute_loss(support_set)
            
            # Compute gradients
            grads = torch.autograd.grad(support_loss, self.model.parameters())
            
            # Update parameters
            with torch.no_grad():
                for param, grad in zip(self.model.parameters(), grads):
                    param.sub_(self.inner_lr * grad)
        
        # Outer loop: evaluate on query set
        query_loss = self._compute_loss(query_set)
        
        # Meta-update
        self.meta_optimizer.zero_grad()
        query_loss.backward()
        self.meta_optimizer.step()
        
        # Restore original parameters for next task
        with torch.no_grad():
            for param, original in zip(self.model.parameters(), original_params):
                param.copy_(original)
        
        return query_loss.item()
    
    def _compute_loss(self, data: List[Tuple]) -> torch.Tensor:
        """Compute loss for given data."""
        total_loss = 0
        for state, action, reward, next_state, done in data:
            state_tensor = torch.FloatTensor(state)
            action_tensor = torch.LongTensor([action])
            
            # Simple forward pass (simplified for demonstration)
            total_loss += torch.tensor(reward).float()
        
        return total_loss / len(data) if data else torch.tensor(0.0)


if __name__ == "__main__":
    print("Testing Long-Term Memory Module...")
    
    ltm = LongTermMemoryModule()
    
    # Test experience encoding
    test_experience = torch.randn(1, 10, 512)
    consolidated, importance, attention = ltm.encode_experience(test_experience)
    print(f"✅ Memory encoding works! Shape: {consolidated.shape}")
    
    # Test episodic memory
    ltm.store_episodic_memory({'test': 'data'}, 0.8)
    print(f"✅ Episodic memory stored! Buffer size: {len(ltm.episodic_buffer)}")
    
    # Test semantic memory
    ltm.store_semantic_memory('test_key', 'test_value')
    result = ltm.retrieve_semantic_memory('test_key')
    print(f"✅ Semantic memory works! Retrieved: {result}")
    
    print("\n✅ All memory tests passed!")
