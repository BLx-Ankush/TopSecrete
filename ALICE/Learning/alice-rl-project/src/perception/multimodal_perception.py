import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass


@dataclass
class StateRepresentation:
    """Multi-modal state representation."""
    visual: Optional[torch.Tensor] = None
    audio: Optional[torch.Tensor] = None
    text: Optional[torch.Tensor] = None
    proprioceptive: Optional[torch.Tensor] = None
    fused: Optional[torch.Tensor] = None
    metadata: Optional[Dict[str, Any]] = None


class VisionEncoder(nn.Module):
    """
    Advanced vision encoder with ResNet-like architecture and attention.
    """
    
    def __init__(self,
                 input_channels: int = 3,
                 base_channels: int = 64,
                 output_dim: int = 512):
        super(VisionEncoder, self).__init__()
        
        # Initial convolution
        self.conv1 = nn.Conv2d(input_channels, base_channels, 
                              kernel_size=7, stride=2, padding=3)
        self.bn1 = nn.BatchNorm2d(base_channels)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        
        # ResNet-like blocks
        self.layer1 = self._make_layer(base_channels, base_channels, 2)
        self.layer2 = self._make_layer(base_channels, base_channels * 2, 2, stride=2)
        self.layer3 = self._make_layer(base_channels * 2, base_channels * 4, 2, stride=2)
        self.layer4 = self._make_layer(base_channels * 4, base_channels * 8, 2, stride=2)
        
        # Spatial attention
        self.spatial_attention = SpatialAttentionModule(base_channels * 8)
        
        # Global average pooling
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        
        # Final projection
        self.fc = nn.Linear(base_channels * 8, output_dim)
        
    def _make_layer(self, 
                    in_channels: int,
                    out_channels: int,
                    num_blocks: int,
                    stride: int = 1) -> nn.Module:
        """Create residual layer."""
        layers = []
        
        # First block (may downsample)
        layers.append(ResidualBlock(in_channels, out_channels, stride))
        
        # Remaining blocks
        for _ in range(1, num_blocks):
            layers.append(ResidualBlock(out_channels, out_channels))
        
        return nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through vision encoder."""
        # Initial convolution
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        # ResNet blocks
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        
        # Spatial attention
        x = self.spatial_attention(x)
        
        # Global pooling and projection
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        
        return x


class ResidualBlock(nn.Module):
    """Residual block for vision encoder."""
    
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1):
        super(ResidualBlock, self).__init__()
        
        self.conv1 = nn.Conv2d(in_channels, out_channels, 
                              kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        
        self.conv2 = nn.Conv2d(out_channels, out_channels,
                              kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        # Shortcut connection
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, 
                         kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        
        out = self.conv2(out)
        out = self.bn2(out)
        
        out += self.shortcut(identity)
        out = self.relu(out)
        
        return out


class SpatialAttentionModule(nn.Module):
    """Spatial attention mechanism for vision."""
    
    def __init__(self, channels: int):
        super(SpatialAttentionModule, self).__init__()
        
        self.conv = nn.Conv2d(2, 1, kernel_size=7, padding=3)
        self.sigmoid = nn.Sigmoid()
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Channel pooling
        max_pool = torch.max(x, dim=1, keepdim=True)[0]
        avg_pool = torch.mean(x, dim=1, keepdim=True)
        
        # Concatenate and convolve
        combined = torch.cat([max_pool, avg_pool], dim=1)
        attention = self.sigmoid(self.conv(combined))
        
        return x * attention


class AudioEncoder(nn.Module):
    """Audio/speech encoder with 1D convolutions."""
    
    def __init__(self,
                 input_channels: int = 1,
                 base_channels: int = 64,
                 output_dim: int = 512):
        super(AudioEncoder, self).__init__()
        
        # Convolutional layers for audio features
        self.conv1 = nn.Conv1d(input_channels, base_channels,
                              kernel_size=11, stride=2, padding=5)
        self.bn1 = nn.BatchNorm1d(base_channels)
        
        self.conv2 = nn.Conv1d(base_channels, base_channels * 2,
                              kernel_size=7, stride=2, padding=3)
        self.bn2 = nn.BatchNorm1d(base_channels * 2)
        
        self.conv3 = nn.Conv1d(base_channels * 2, base_channels * 4,
                              kernel_size=5, stride=2, padding=2)
        self.bn3 = nn.BatchNorm1d(base_channels * 4)
        
        self.conv4 = nn.Conv1d(base_channels * 4, base_channels * 8,
                              kernel_size=3, stride=2, padding=1)
        self.bn4 = nn.BatchNorm1d(base_channels * 8)
        
        # Temporal attention
        self.temporal_attention = TemporalAttentionModule(base_channels * 8)
        
        # Global pooling
        self.avgpool = nn.AdaptiveAvgPool1d(1)
        
        # Final projection
        self.fc = nn.Linear(base_channels * 8, output_dim)
        
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through audio encoder."""
        # Convolutional layers
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.relu(self.bn3(self.conv3(x)))
        x = self.relu(self.bn4(self.conv4(x)))
        
        # Temporal attention
        x = self.temporal_attention(x)
        
        # Global pooling and projection
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        
        return x


class TemporalAttentionModule(nn.Module):
    """Temporal attention for audio sequences."""
    
    def __init__(self, channels: int):
        super(TemporalAttentionModule, self).__init__()
        
        self.conv = nn.Conv1d(channels, channels // 8, kernel_size=1)
        self.sigmoid = nn.Sigmoid()
        self.fc1 = nn.Linear(channels // 8, channels // 16)
        self.fc2 = nn.Linear(channels // 16, channels)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, channels, length = x.shape
        
        # Global pooling
        pooled = F.adaptive_avg_pool1d(x, 1).squeeze(-1)
        
        # Attention weights
        attention = self.fc1(self.conv(x.mean(dim=-1, keepdim=True)).squeeze(-1))
        attention = F.relu(attention)
        attention = self.fc2(attention)
        attention = self.sigmoid(attention).unsqueeze(-1)
        
        return x * attention


class CrossModalFusion(nn.Module):
    """Cross-modal fusion with attention mechanism."""
    
    def __init__(self,
                 visual_dim: int = 512,
                 audio_dim: int = 512,
                 text_dim: int = 768,
                 fusion_dim: int = 1024):
        super(CrossModalFusion, self).__init__()
        
        # Modal projections to common space
        self.visual_proj = nn.Linear(visual_dim, fusion_dim)
        self.audio_proj = nn.Linear(audio_dim, fusion_dim)
        self.text_proj = nn.Linear(text_dim, fusion_dim)
        
        # Cross-modal attention
        self.cross_attention = nn.MultiheadAttention(
            fusion_dim,
            num_heads=8,
            dropout=0.1,
            batch_first=True
        )
        
        # Fusion network
        self.fusion_network = nn.Sequential(
            nn.Linear(fusion_dim * 3, fusion_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(fusion_dim * 2, fusion_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(fusion_dim, fusion_dim)
        )
        
        # Modal importance weights
        self.modal_importance = nn.Sequential(
            nn.Linear(fusion_dim * 3, fusion_dim),
            nn.ReLU(),
            nn.Linear(fusion_dim, 3),
            nn.Softmax(dim=-1)
        )
        
    def forward(self,
                visual: Optional[torch.Tensor] = None,
                audio: Optional[torch.Tensor] = None,
                text: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Fuse multiple modalities."""
        
        modalities = []
        projected = []
        
        # Project available modalities
        if visual is not None:
            visual_proj = self.visual_proj(visual)
            modalities.append(visual_proj)
            projected.append(visual_proj)
        
        if audio is not None:
            audio_proj = self.audio_proj(audio)
            modalities.append(audio_proj)
            projected.append(audio_proj)
        
        if text is not None:
            text_proj = self.text_proj(text)
            modalities.append(text_proj)
            projected.append(text_proj)
        
        if len(modalities) == 0:
            raise ValueError("At least one modality must be provided")
        
        if len(modalities) == 1:
            return modalities[0]
        
        # Stack modalities for attention
        stacked = torch.stack(modalities, dim=1)
        
        # Apply cross-modal attention
        attended, _ = self.cross_attention(stacked, stacked, stacked)
        
        # Concatenate all modalities
        concatenated = torch.cat([m for m in modalities], dim=-1)
        
        # Compute modal importance weights
        importance = self.modal_importance(concatenated)
        
        # Weighted fusion
        weighted_modalities = []
        for i, modality in enumerate(modalities):
            weighted_modalities.append(modality * importance[:, i:i+1])
        
        weighted_sum = sum(weighted_modalities)
        
        # Final fusion
        fused = self.fusion_network(concatenated) + weighted_sum
        
        return fused


class ProprioceptiveEncoder(nn.Module):
    """Encoder for proprioceptive/internal state information."""
    
    def __init__(self,
                 input_dim: int = 50,
                 hidden_dim: int = 256,
                 output_dim: int = 512):
        super(ProprioceptiveEncoder, self).__init__()
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, output_dim),
            nn.Tanh()
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)


class PerceptionSystem:
    """
    Complete multi-modal perception system for ALICE.
    Processes visual, audio, text, and proprioceptive inputs.
    """
    
    def __init__(self, device: str = 'cpu'):
        self.device = device
        
        # Initialize encoders
        self.vision_encoder = VisionEncoder(
            input_channels=3,
            output_dim=512
        ).to(device)
        
        self.audio_encoder = AudioEncoder(
            input_channels=1,
            output_dim=512
        ).to(device)
        
        self.proprioceptive_encoder = ProprioceptiveEncoder(
            input_dim=50,
            output_dim=512
        ).to(device)
        
        # Cross-modal fusion
        self.fusion = CrossModalFusion(
            visual_dim=512,
            audio_dim=512,
            text_dim=768,
            fusion_dim=1024
        ).to(device)
        
        # Perception history
        self.perception_history: List[StateRepresentation] = []
        self.max_history = 100
        
    def perceive(self,
                 visual: Optional[np.ndarray] = None,
                 audio: Optional[np.ndarray] = None,
                 text_embedding: Optional[torch.Tensor] = None,
                 proprioceptive: Optional[np.ndarray] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> StateRepresentation:
        """
        Process multi-modal input and create unified state representation.
        
        Args:
            visual: Visual input (H, W, C) or (B, C, H, W)
            audio: Audio input (samples,) or (B, C, samples)
            text_embedding: Pre-computed text embedding
            proprioceptive: Internal state vector
            metadata: Additional metadata
        
        Returns:
            StateRepresentation with all modalities
        """
        
        encoded_visual = None
        encoded_audio = None
        encoded_proprioceptive = None
        
        # Process visual input
        if visual is not None:
            visual_tensor = self._prepare_visual(visual)
            with torch.no_grad():
                encoded_visual = self.vision_encoder(visual_tensor)
        
        # Process audio input
        if audio is not None:
            audio_tensor = self._prepare_audio(audio)
            with torch.no_grad():
                encoded_audio = self.audio_encoder(audio_tensor)
        
        # Process proprioceptive input
        if proprioceptive is not None:
            proprio_tensor = torch.tensor(proprioceptive, dtype=torch.float32).to(self.device)
            if proprio_tensor.dim() == 1:
                proprio_tensor = proprio_tensor.unsqueeze(0)
            with torch.no_grad():
                encoded_proprioceptive = self.proprioceptive_encoder(proprio_tensor)
        
        # Fuse modalities
        fused = None
        if any(x is not None for x in [encoded_visual, encoded_audio, text_embedding]):
            with torch.no_grad():
                fused = self.fusion(
                    visual=encoded_visual,
                    audio=encoded_audio,
                    text=text_embedding
                )
        
        # Create state representation
        state = StateRepresentation(
            visual=encoded_visual,
            audio=encoded_audio,
            text=text_embedding,
            proprioceptive=encoded_proprioceptive,
            fused=fused,
            metadata=metadata or {}
        )
        
        # Add to history
        self.perception_history.append(state)
        if len(self.perception_history) > self.max_history:
            self.perception_history.pop(0)
        
        return state
    
    def _prepare_visual(self, visual: np.ndarray) -> torch.Tensor:
        """Prepare visual input for encoder."""
        # Convert to tensor
        if visual.dtype != np.float32:
            visual = visual.astype(np.float32) / 255.0
        
        # Add batch and channel dimensions if needed
        if visual.ndim == 3:  # (H, W, C)
            visual = np.transpose(visual, (2, 0, 1))  # (C, H, W)
            visual = np.expand_dims(visual, 0)  # (1, C, H, W)
        elif visual.ndim == 4:  # (B, H, W, C)
            visual = np.transpose(visual, (0, 3, 1, 2))  # (B, C, H, W)
        
        return torch.tensor(visual, dtype=torch.float32).to(self.device)
    
    def _prepare_audio(self, audio: np.ndarray) -> torch.Tensor:
        """Prepare audio input for encoder."""
        # Normalize
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        audio = audio / (np.max(np.abs(audio)) + 1e-8)
        
        # Add dimensions if needed
        if audio.ndim == 1:  # (samples,)
            audio = np.expand_dims(audio, (0, 1))  # (1, 1, samples)
        elif audio.ndim == 2:  # (batch, samples)
            audio = np.expand_dims(audio, 1)  # (batch, 1, samples)
        
        return torch.tensor(audio, dtype=torch.float32).to(self.device)
    
    def get_current_state(self) -> Optional[StateRepresentation]:
        """Get most recent state representation."""
        return self.perception_history[-1] if self.perception_history else None
    
    def get_perception_history(self, last_n: int = 10) -> List[StateRepresentation]:
        """Get recent perception history."""
        return self.perception_history[-last_n:]
    
    def save_models(self, filepath: str):
        """Save perception models."""
        torch.save({
            'vision_encoder': self.vision_encoder.state_dict(),
            'audio_encoder': self.audio_encoder.state_dict(),
            'proprioceptive_encoder': self.proprioceptive_encoder.state_dict(),
            'fusion': self.fusion.state_dict()
        }, filepath)
    
    def load_models(self, filepath: str):
        """Load perception models."""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.vision_encoder.load_state_dict(checkpoint['vision_encoder'])
        self.audio_encoder.load_state_dict(checkpoint['audio_encoder'])
        self.proprioceptive_encoder.load_state_dict(checkpoint['proprioceptive_encoder'])
        self.fusion.load_state_dict(checkpoint['fusion'])


if __name__ == "__main__":
    print("Testing Perception System...")
    
    perception = PerceptionSystem(device='cpu')
    
    # Test with dummy data
    dummy_visual = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    dummy_audio = np.random.randn(16000).astype(np.float32)
    dummy_text_embedding = torch.randn(1, 768)
    dummy_proprioceptive = np.random.randn(50).astype(np.float32)
    
    print("Processing multi-modal input...")
    state = perception.perceive(
        visual=dummy_visual,
        audio=dummy_audio,
        text_embedding=dummy_text_embedding,
        proprioceptive=dummy_proprioceptive
    )
    
    print(f"Visual encoding shape: {state.visual.shape if state.visual is not None else 'None'}")
    print(f"Audio encoding shape: {state.audio.shape if state.audio is not None else 'None'}")
    print(f"Text embedding shape: {state.text.shape if state.text is not None else 'None'}")
    print(f"Proprioceptive shape: {state.proprioceptive.shape if state.proprioceptive is not None else 'None'}")
    print(f"Fused representation shape: {state.fused.shape if state.fused is not None else 'None'}")
    
    print("\n✅ Perception System test complete!")
