# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""
LLM Client for local AI Coaching via Ollama.
Interfaces with local Qwen/Llama models for tactical analysis.
"""

import requests
import json
import threading
from typing import Optional, Dict, Any, Callable

class LLMClient:
    """Client for local Ollama instance."""
    
    DEFAULT_MODEL = "qwen2.5"
    API_URL = "http://localhost:11434/api/generate"
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model = model_name
        self.available = False
        self._check_availability()
        
    def _check_availability(self):
        """Check if Ollama is running and model is available."""
        try:
            # Check version endpoint
            resp = requests.get("http://localhost:11434/api/version", timeout=1.0)
            if resp.status_code == 200:
                print(f"✓ Ollama connected (v{resp.json().get('version')})")
                self.available = True
                # Trigger pull if needed (async)
                # self._ensure_model()
            else:
                print("✗ Ollama running but returned error")
        except:
            print("✗ Ollama not detected at localhost:11434")
            self.available = False

    def generate_async(self, prompt: str, callback: Callable[[str], None], system_prompt: str = ""):
        """Generate response asynchronously to avoid blocking UI."""
        if not self.available:
            callback("Error: AI Engine (Ollama) not connected.")
            return

        def _run():
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_ctx": 2048
                    }
                }
                
                resp = requests.post(self.API_URL, json=payload, timeout=30)
                if resp.status_code == 200:
                    result = resp.json().get("response", "")
                    callback(result)
                else:
                    callback(f"Error: Model returned {resp.status_code}")
            except Exception as e:
                callback(f"Error generating analysis: {str(e)}")

        thread = threading.Thread(target=_run)
        thread.daemon = True
        thread.start()

    def get_coach_persona(self) -> str:
        """Return the system prompt for the coach."""
        return """You are a professional CS2 Coach. Your job is to analyze death scenarios and give specific, actionable advice.
        Be concise, direct, and slightly strict/tough love (like a real sports coach).
        Focus on positioning, utility usage, and crosshair placement.
        Do not be generic. Use CS2 terminology (trade, spacing, contact, map control).
        Limit response to 2-3 short sentences max."""
