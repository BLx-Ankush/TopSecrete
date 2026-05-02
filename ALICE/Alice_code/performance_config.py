"""
Optimized LiveKit client configuration for reduced latency
"""

# Add these settings to reduce audio latency
LIVEKIT_OPTIMIZATIONS = {
    # Audio optimizations
    'audio_sample_rate': 24000,  # Reduced from 48000
    'audio_buffer_size': 100,    # Smaller buffer for lower latency
    'vad_threshold': 0.5,        # Voice activity detection
    
    # Connection optimizations
    'track_publish_timeout': 2000,  # Reduced from 3000ms
    'connection_timeout': 3000,     # Reduced from 5000ms
    'reconnect_timeout': 2000,      # Reduced from 3000ms
    
    # Processing optimizations
    'preemptive_generation': True,  # Start generating before user stops speaking
    'streaming': True,              # Stream responses for faster perception
    'max_response_tokens': 512,     # Limit response length for speed
}

# Performance monitoring
import time
import logging

class PerformanceMonitor:
    def __init__(self):
        self.start_times = {}
        self.logger = logging.getLogger('alice_performance')
    
    def start_timer(self, operation):
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation):
        if operation in self.start_times:
            duration = time.time() - self.start_times[operation]
            self.logger.info(f"{operation}: {duration:.2f}s")
            del self.start_times[operation]
            return duration
        return 0

# Global performance monitor
perf_monitor = PerformanceMonitor()