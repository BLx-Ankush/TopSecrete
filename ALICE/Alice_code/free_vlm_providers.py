"""
Free VLM Providers for Alice Vision System
Supports multiple free vision language models as alternatives to Gemini
"""

import os
import base64
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class FreeVLMProvider:
    """Base class for free VLM providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.available = False
        self.error_message = ""
    
    async def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze image with the VLM"""
        raise NotImplementedError
    
    def check_availability(self) -> bool:
        """Check if this provider is available"""
        raise NotImplementedError

class OllamaVLMProvider(FreeVLMProvider):
    """Ollama local VLM provider (completely free)"""
    
    def __init__(self):
        super().__init__("Ollama")
        self.base_url = "http://localhost:11434"
        self.model = "llava:latest"  # Default model
        self.available = self.check_availability()
    
    def check_availability(self) -> bool:
        """Check if Ollama is running and has vision models"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                vision_models = [m for m in models if "llava" in m["name"].lower() or "vision" in m["name"].lower()]
                if vision_models:
                    self.model = vision_models[0]["name"]
                    return True
                else:
                    self.error_message = "No vision models found in Ollama. Install with: ollama pull llava"
                    return False
            else:
                self.error_message = "Ollama not running. Start with: ollama serve"
                return False
        except ImportError:
            self.error_message = "requests library not installed: pip install requests"
            return False
        except Exception as e:
            self.error_message = f"Ollama not available: {e}"
            return False
    
    async def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using Ollama"""
        try:
            import requests
            
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode()
            
            # Prepare request
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_data],
                "stream": False
            }
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "analysis": result.get("response", "No response"),
                    "provider": "Ollama",
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama error: {response.status_code}",
                    "provider": "Ollama"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Ollama analysis failed: {e}",
                "provider": "Ollama"
            }

class HuggingFaceVLMProvider(FreeVLMProvider):
    """Hugging Face Inference API VLM provider (free tier)"""
    
    def __init__(self):
        super().__init__("Hugging Face")
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.model = "Salesforce/blip-image-captioning-large"  # Free model
        self.available = self.check_availability()
    
    def check_availability(self) -> bool:
        """Check if HF API key is available"""
        if not self.api_key:
            self.error_message = "HUGGINGFACE_API_KEY not found in environment"
            return False
        
        try:
            import requests
            return True
        except ImportError:
            self.error_message = "requests library not installed"
            return False
    
    async def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using Hugging Face"""
        try:
            import requests
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # Read image
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
            
            # Use image captioning model (free tier friendly)
            response = requests.post(
                f"https://api-inference.huggingface.co/models/{self.model}",
                headers=headers,
                data=image_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                caption = result[0]["generated_text"] if isinstance(result, list) else str(result)
                
                return {
                    "success": True,
                    "analysis": f"Image Caption: {caption}\n\nNote: This is a basic caption. For detailed analysis like '{prompt}', consider using a full VLM.",
                    "provider": "Hugging Face",
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"HF API error: {response.status_code} - {response.text}",
                    "provider": "Hugging Face"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Hugging Face analysis failed: {e}",
                "provider": "Hugging Face"
            }

class TogetherAIVLMProvider(FreeVLMProvider):
    """Together AI VLM provider (free tier)"""
    
    def __init__(self):
        super().__init__("Together AI")
        self.api_key = os.getenv("TOGETHER_API_KEY")
        self.model = "meta-llama/Llama-Vision-Free"  # Example free model
        self.available = self.check_availability()
    
    def check_availability(self) -> bool:
        """Check if Together AI key is available"""
        if not self.api_key:
            self.error_message = "TOGETHER_API_KEY not found in environment"
            return False
        return True
    
    async def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using Together AI"""
        try:
            import requests
            
            # Read and encode image
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode()
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                        ]
                    }
                ]
            }
            
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                return {
                    "success": True,
                    "analysis": content,
                    "provider": "Together AI",
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": f"Together AI error: {response.status_code}",
                    "provider": "Together AI"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Together AI analysis failed: {e}",
                "provider": "Together AI"
            }

class FreeVLMManager:
    """Manager for multiple free VLM providers"""
    
    def __init__(self):
        self.providers = [
            OllamaVLMProvider(),
            HuggingFaceVLMProvider(),
            TogetherAIVLMProvider()
        ]
        self.available_providers = [p for p in self.providers if p.available]
        
        if self.available_providers:
            logger.info(f"Available free VLM providers: {[p.name for p in self.available_providers]}")
        else:
            logger.warning("No free VLM providers available")
    
    async def analyze_with_best_provider(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """Try providers in order of preference until one works"""
        
        if not self.available_providers:
            return {
                "success": False,
                "error": "No free VLM providers available",
                "suggestions": self._get_setup_suggestions()
            }
        
        for provider in self.available_providers:
            try:
                result = await provider.analyze_image(image_path, prompt)
                if result["success"]:
                    return result
                else:
                    logger.warning(f"{provider.name} failed: {result['error']}")
            except Exception as e:
                logger.error(f"{provider.name} error: {e}")
        
        return {
            "success": False,
            "error": "All free VLM providers failed",
            "tried_providers": [p.name for p in self.available_providers]
        }
    
    def _get_setup_suggestions(self) -> Dict[str, str]:
        """Get setup suggestions for unavailable providers"""
        suggestions = {}
        
        for provider in self.providers:
            if not provider.available:
                if provider.name == "Ollama":
                    suggestions["Ollama"] = "1. Install: https://ollama.ai\n2. Run: ollama serve\n3. Install vision model: ollama pull llava"
                elif provider.name == "Hugging Face":
                    suggestions["Hugging Face"] = "1. Get free API key: https://huggingface.co\n2. Set HUGGINGFACE_API_KEY environment variable"
                elif provider.name == "Together AI":
                    suggestions["Together AI"] = "1. Get free API key: https://together.ai\n2. Set TOGETHER_API_KEY environment variable"
        
        return suggestions
    
    def get_status_report(self) -> str:
        """Get detailed status of all providers"""
        report = "🔍 **FREE VLM PROVIDERS STATUS**\n\n"
        
        for provider in self.providers:
            status = "✅ Available" if provider.available else f"❌ {provider.error_message}"
            report += f"**{provider.name}**: {status}\n"
        
        if not self.available_providers:
            report += "\n📋 **Setup Instructions:**\n"
            suggestions = self._get_setup_suggestions()
            for name, instruction in suggestions.items():
                report += f"\n**{name}:**\n{instruction}\n"
        
        return report

# Global instance
free_vlm_manager = FreeVLMManager()

async def analyze_with_free_vlm(image_path: str, prompt: str) -> str:
    """Main function to analyze image with free VLMs"""
    result = await free_vlm_manager.analyze_with_best_provider(image_path, prompt)
    
    if result["success"]:
        return f"""🆓 **FREE VLM ANALYSIS** ({result['provider']})

🎯 **Task**: {prompt}
🔧 **Model**: {result.get('model', 'Unknown')}

📋 **Analysis**:
{result['analysis']}

✨ **Provider**: {result['provider']} (Free)
"""
    else:
        error_msg = f"""❌ **FREE VLM ANALYSIS FAILED**

🎯 **Task**: {prompt}
❌ **Error**: {result['error']}

"""
        if "suggestions" in result:
            error_msg += "💡 **Setup Free VLMs:**\n"
            for name, instruction in result["suggestions"].items():
                error_msg += f"\n**{name}:**\n{instruction}\n"
        
        return error_msg

def get_free_vlm_status() -> str:
    """Get status of all free VLM providers"""
    return free_vlm_manager.get_status_report()