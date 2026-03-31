# SPDX-FileCopyrightText: 2026 Pl4yer-ONE <mahadevan.rajeev27@gmail.com>
# SPDX-License-Identifier: LicenseRef-Sacrilege-EULA

"""
LLM Client for local AI Coaching via Ollama.
Interfaces with local Qwen/Llama models for tactical analysis.
Supports multi-turn conversation for interactive coaching chat.
"""

import requests
import json
import threading
from typing import Optional, Dict, Any, Callable, List


class LLMClient:
    """Client for local Ollama instance with multi-turn conversation support."""
    
    DEFAULT_MODEL = "qwen2.5"
    API_URL = "http://localhost:11434/api/generate"
    CHAT_URL = "http://localhost:11434/api/chat"
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model = model_name
        self.available = False
        self.conversation_history: List[Dict[str, str]] = []
        self._check_availability()
        
    def _check_availability(self):
        """Check if Ollama is running and model is available."""
        try:
            resp = requests.get("http://localhost:11434/api/version", timeout=1.0)
            if resp.status_code == 200:
                print(f"✓ Ollama connected (v{resp.json().get('version')})")
                self.available = True
            else:
                print("✗ Ollama running but returned error")
        except:
            print("✗ Ollama not detected at localhost:11434")
            self.available = False

    def generate_async(self, prompt: str, callback: Callable[[str], None], system_prompt: str = ""):
        """Generate response asynchronously (single-turn, non-chat mode)."""
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

    def chat_async(self, user_message: str, callback: Callable[[str], None], 
                   context: str = "", system_prompt: str = ""):
        """
        Multi-turn chat: sends conversation history to Ollama /api/chat endpoint.
        Maintains conversation context across messages for back-and-forth coaching.
        
        Args:
            user_message: The user's chat message
            callback: Function called with the AI response text
            context: Optional game context (current round state, player stats, etc.)
            system_prompt: System prompt for the coach persona
        """
        if not self.available:
            callback("Error: AI Engine (Ollama) not connected. Start Ollama to chat.")
            return

        # Build the user's message with optional game context
        full_user_msg = user_message
        if context:
            full_user_msg = f"[Current Game Context]\n{context}\n\n[Player Question]\n{user_message}"

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": full_user_msg
        })

        def _run():
            try:
                # Build messages array with system prompt + history
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                # Include conversation history (keep last 20 messages to avoid context overflow)
                messages.extend(self.conversation_history[-20:])
                
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_ctx": 4096
                    }
                }
                
                resp = requests.post(self.CHAT_URL, json=payload, timeout=45)
                if resp.status_code == 200:
                    result = resp.json().get("message", {}).get("content", "")
                    # Add assistant response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": result
                    })
                    callback(result)
                else:
                    callback(f"Error: Model returned {resp.status_code}")
            except Exception as e:
                callback(f"Error: {str(e)}")

        thread = threading.Thread(target=_run)
        thread.daemon = True
        thread.start()

    def reset_conversation(self):
        """Clear conversation history for a fresh chat session."""
        self.conversation_history.clear()
        print("✓ Chat history cleared")

    def get_coach_persona(self) -> str:
        """Return the system prompt for the coach."""
        return """You are a professional CS2 Coach. Your job is to analyze death scenarios and give specific, actionable advice.
        Be concise, direct, and slightly strict/tough love (like a real sports coach).
        Focus on positioning, utility usage, and crosshair placement.
        Do not be generic. Use CS2 terminology (trade, spacing, contact, map control).
        Limit response to 2-3 short sentences max."""

    def get_chat_persona(self) -> str:
        """Return the system prompt for interactive chat mode - more conversational."""
        return """You are SACRILEGE COACH, a professional CS2 tactical analyst and coach embedded in a demo replay viewer.

You have access to the player's match data shown in the demo replay. You can see:
- Kill/death events with blame analysis
- Player positioning and rotations  
- Utility usage (smokes, flashes, mollies)
- Trade success/failure rates
- Performance grades (S through F)

Your personality:
- Direct and honest, like a real esports coach
- Use CS2 terminology naturally (trade, spacing, contact play, map control, anchor, rotate, lurk, entry, etc.)
- Give specific, actionable advice - never generic
- Tough love when needed, praise only when genuinely earned
- Keep responses concise (3-5 sentences max unless asked for detail)
- Reference specific rounds and situations from the match when possible

When the player asks about strategy, positioning, or improvement, draw from the match data context provided.
If no specific context is given, provide general CS2 coaching based on the question."""
