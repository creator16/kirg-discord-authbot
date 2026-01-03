import os
import asyncio
import random
import re
from typing import List, Optional, Tuple, Any
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class KirgBrain:
    """
    Main AI logic for Kirg, supporting multiple providers (OpenRouter, Gemini).
    """
    def __init__(self, provider: str = "openrouter"):
        self.provider = os.getenv("AI_PROVIDER", provider).lower()
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        
        self.client = None
        self.gemini_model = None

        if self.provider == "gemini" and self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            print(f"[BRAIN] 🧠 Native Gemini Engine Initialized")
        elif self.openrouter_key:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=self.openrouter_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/EdwardLow/KirgBot", 
                    "X-Title": "Kirg AI Persona"
                }
            )
            print(f"[BRAIN] 🧠 OpenRouter Engine Initialized")
        else:
            print(f"[BRAIN] ⚠️ No AI provider configured or keys missing.")

    def _generate_response(self, system_prompt: str, user_prompt: str, temperature: float = 0.7, max_tokens: int = 150) -> Optional[str]:
        """Internal helper to route requests to the active provider."""
        try:
            if self.provider == "gemini" and self.gemini_model:
                # Gemini handles system instructions in the model initialization or as a specific role
                # For simplicity and effectiveness, we join them
                combined_prompt = f"SYSTEM INSTRUCTION: {system_prompt}\n\nUSER INPUT: {user_prompt}"
                response = self.gemini_model.generate_content(
                    combined_prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=temperature,
                        max_output_tokens=max_tokens,
                    )
                )
                return response.text.strip()
            
            elif self.client:
                completion = self.client.chat.completions.create(
                    model="xiaomi/mimo-v2-flash:free", 
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature, 
                    max_tokens=max_tokens,
                )
                return completion.choices[0].message.content.strip()
            
            return None
        except Exception as e:
            print(f"[BRAIN] Generation error ({self.provider}): {e}")
            return None

    def decide_and_respond(self, chat_history: List[Tuple[str, str]], my_name: str, is_direct: bool = False) -> Optional[List[str]]:
        """Analyzes chat history and decides whether and how to respond."""
        
        system_prompt = (
            f"You are {my_name}, a 17-year-old Discord native. You're a bit of a shut-in, gamer, and tech enthusiast.\n"
            "PERSONALIDADE:\n"
            "- Casual, witty, uses internet slang (slk, mid, peak, intankavel, fds, peak).\n"
            "- Focus on responding naturally to one specific person in the conversation.\n"
            "CHAT DYNAMICS:\n"
            "- DO NOT prefix messages with anyone's name (e.g., 'Ian: hi' or 'User: hi' are FORBIDDEN).\n"
            "- WRITE ONLY THE MESSAGE CONTENT.\n"
            "- You can send 1 to 3 messages to complete a thought, separated by newlines.\n"
            "- If you have nothing relevant to say, send only [SKIP].\n"
            "- Write in lowercase, no formal punctuation.\n"
            "- NEVER repeat what was just said.\n"
            "- Talk directly to people without repeating their names constantly."
        )
        
        if is_direct:
            system_prompt += "\nIMPORTANT: You were mentioned. DO NOT [SKIP], respond now."
        
        history_text = ""
        recent_contents = set()
        active_users = set()
        for author, content in chat_history:
            history_text += f"{author}: {content}\n"
            active_users.add(author)
            recent_contents.add(content.lower().strip())

        active_list = ", ".join(active_users)
        user_prompt = (
            f"PARTICIPANTS: [{active_list}]\n\n"
            f"RECENT CHAT:\n{history_text}\n---\n"
            f"Respond as {my_name}. Send ONLY your response, no names prefixing."
        )

        response = self._generate_response(system_prompt, user_prompt)
        
        if not response:
            return None

        # Clean up thinking tags and formatting
        response = re.sub(r'<(think|thought)>.*?</\1>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
        
        if "[SKIP]" in response:
            return None
        
        lines = response.split('\n')
        valid_msgs = []
        common_slang = {"intankavel", "slk", "fds", "mid", "peak"}

        for line in lines:
            line = line.strip()
            if not line or "[SKIP]" in line: continue 
            
            # Filter hallucinated history
            if ":" in line:
                parts = line.split(":", 1)
                name_part = parts[0].strip().lower()
                if name_part in [u.lower() for u in active_users] or name_part == my_name.lower():
                    if name_part == my_name.lower():
                        line = parts[1].strip()
                    else:
                        continue

            # Filter eco
            if line.lower().strip() in recent_contents:
                continue

            # Deduplicate slang
            words = line.split()
            clean_words = []
            seen_slang = set()
            for w in words:
                wc = w.lower().replace('.', '').replace(',', '')
                if wc in common_slang:
                    if wc in seen_slang: continue
                    seen_slang.add(wc)
                clean_words.append(w)
            
            line_clean = " ".join(clean_words).replace('"', '').replace("'", "")
            
            if line_clean:
                if any(line_clean.lower() == v.lower() for v in valid_msgs):
                    continue
                valid_msgs.append(line_clean)

        return valid_msgs[:3] if valid_msgs else None

    def decide_proactive_message(self, chat_history: List[Tuple[str, str]], my_name: str) -> Optional[List[str]]:
        """Generates a proactive message to break the silence in the chat."""
        
        system_prompt = (
            f"You are {my_name}, 17. The chat is quiet and you are bored.\n"
            "OBJECTIVE: Send a short message to start a conversation or vent about boredom.\n"
            "TOPICS: Games, lag, bad ping, school, food, internet drama, or random thoughts.\n"
            "STYLE: Casual, lowercase, discord slang (slk, fds, intankavel).\n"
            "RULES: NO greetings, speak directly, max 10 words."
        )

        history_text = ""
        for author, content in chat_history[-5:]:
            history_text += f"{author}: {content}\n"

        user_prompt = (
            f"RECENT CHAT:\n{history_text}\n---\n"
            f"What would {my_name} say right now?"
        )

        response = self._generate_response(system_prompt, user_prompt, temperature=0.9, max_tokens=60)
        
        if not response or "[SKIP]" in response:
             return ["slk que tédio"]
             
        response = re.sub(r'<(think|thought)>.*?</\1>', '', response, flags=re.DOTALL | re.IGNORECASE).strip()
        return [response.replace('"', '').replace("'", "").lower()]
