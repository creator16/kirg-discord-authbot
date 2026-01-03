import discord
import os
import asyncio
import random
import json
import time
import re
from collections import deque
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from brain import KirgBrain

# Constants for behavior tuning
HISTORY_LIMIT = 12
TYPING_SPEED_RANGE = (0.04, 0.12)
PROACTIVITY_RANGE_MINUTES = (15, 50)
DEMO_PROACTIVITY_RANGE_MINUTES = (5, 20)

def load_config() -> Dict[str, Any]:
    """Loads configuration from config.json or returns default values."""
    if not os.path.exists("config.json"):
        return {"channels": {}, "last_channel": ""}
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(config: Dict[str, Any]):
    """Saves the current configuration to config.json."""
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

load_dotenv()
TOKEN = os.getenv("KIRG_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

class KirgClient(discord.Client):
    """
    Discord Client implementation for Kirg Simulator.
    Handles events, message processing, and realistic typing simulation.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brain = KirgBrain() # Automatically picks provider from .env
        self.config = load_config()
        self.target_channel_id = None
        self.chat_memories = {} 
        self.me_user = None
        self.processing_lock = asyncio.Lock()
        self.known_users = {} # Cache for mention mapping
        self.channel_debounces = {}
        self.channel_mentions_pending = {}
        
        # Proactivity tracking
        self.last_activity_time = time.time()
        self.next_activity_trigger = 0
        self._schedule_next_proactivity()

    def _schedule_next_proactivity(self):
        """Schedules the next spontaneous interaction (cooldown)."""
        minutes = random.uniform(*DEMO_PROACTIVITY_RANGE_MINUTES) 
        self.next_activity_trigger = time.time() + (minutes * 60)
        print(f"⏰ Next spontaneous interaction scheduled in {minutes:.1f} minutes")

    async def proactivity_loop(self):
        """Background loop that triggers spontaneous messages when chat is idle."""
        await self.wait_until_ready()
        print("🔁 Proactivity Loop Started")
        
        while not self.is_closed():
            await asyncio.sleep(30)
            
            if not self.target_channel_id:
                continue
            
            now = time.time()
            if now > self.next_activity_trigger:
                # Trigger logic
                if self.target_channel_id in self.chat_memories:
                    history = self.chat_memories[self.target_channel_id]
                    if history:
                        last_author, _ = history[-1]
                        my_name = self.me_user.display_name if self.me_user else "Ian"
                        # Don't talk twice in a row if yours was the last message
                        if last_author == my_name:
                            self._schedule_next_proactivity()
                            continue
                
                if not self.processing_lock.locked():
                    async with self.processing_lock:
                        print("⚡ Boredom trigger activated!")
                        channel = self.get_channel(self.target_channel_id)
                        if channel:
                            history_list = list(self.chat_memories.get(self.target_channel_id, []))
                            my_nick = self.me_user.display_name
                            
                            response = await asyncio.to_thread(self.brain.decide_proactive_message, history_list, my_nick)
                            
                            if response:
                                async with channel.typing():
                                    await self._send_response_package(channel, response, my_nick, self.target_channel_id)
                
                self._schedule_next_proactivity()

    def _remember_user(self, user: discord.User):
        """Maps user names/nicks to mentions for future AI use."""
        if not user or user.bot: return
        
        keys = [user.name.lower()]
        if user.display_name and user.display_name.lower() != user.name.lower():
            keys.append(user.display_name.lower())
        
        if hasattr(user, 'nick') and user.nick and user.nick.lower() not in keys:
            keys.append(user.nick.lower())
        
        for k in keys:
            self.known_users[k] = user.mention

    async def on_ready(self):
        """Called when the client is logged in and ready."""
        self.me_user = self.user
        print(f'\n[KIRG] Simulator Started: {self.user}')
        print('⚡ Mode: Autonomous (User Account) / Realism Locks Active')
        
        await self.setup_channel()
        if self.target_channel_id:
            await self.preload_history(self.target_channel_id)
            
        self.loop.create_task(self.proactivity_loop())

    def _format_mentions(self, text: str) -> str:
        """Replaces plain text names with Discord mentions."""
        if not text: return text
        sorted_names = sorted(self.known_users.keys(), key=len, reverse=True)
        
        for name in sorted_names:
            if name in text.lower():
                mention = self.known_users[name]
                pattern = re.compile(re.escape(name), re.IGNORECASE)
                text = pattern.sub(mention, text)
        return text

    async def setup_channel(self):
        """Prompts user to select the simulation channel."""
        channels = self.config.get("channels", {})
        if not channels:
            # Fallback if no channels are saved
            print("\n⚠️ No channels configured in config.json.")
            return

        print("\nWhere shall we simulate today?")
        for name in channels.keys(): print(f"- {name}")
        
        choice = input("Channel (name) or [ENTER] for last: ").strip()
        if not choice and self.config.get("last_channel"):
            choice = self.config["last_channel"]
            
        if choice in channels:
            self.target_channel_id = int(channels[choice])
            self.config["last_channel"] = choice
            save_config(self.config)
            print(f"✅ Focusing on channel: {choice}")
        else:
            first = list(channels.keys())[0]
            self.target_channel_id = int(channels[first])
            print(f"Fallback to: {first}")

    async def get_real_name(self, author: discord.Member, guild: Optional[discord.Guild]) -> str:
        """Retrieves the effective display name (nick) for a user."""
        if guild:
            member = guild.get_member(author.id) or author
            self._remember_user(member)
            if hasattr(member, 'nick') and member.nick:
                return member.nick
        else:
            self._remember_user(author)
        return author.display_name

    async def preload_history(self, channel_id: int):
        """Loads recent messages to build context before starting."""
        try:
            channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
            if not channel: return
            
            guild = getattr(channel, 'guild', None)
            print(f"📚 Preloading history for {channel}...")
            
            history = [msg async for msg in channel.history(limit=HISTORY_LIMIT)]
            self.chat_memories[channel_id] = deque(maxlen=HISTORY_LIMIT)
            
            for msg in reversed(history):
                real_name = await self.get_real_name(msg.author, guild)
                self.chat_memories[channel_id].append((real_name, msg.content))
            
            print(f"🧠 Context loaded! ({len(self.known_users)} users mapped)")
        except Exception as e:
            print(f"Error preloading history: {e}")

    async def on_message(self, message: discord.Message):
        """Main event handler for new messages."""
        if message.author.id == self.user.id:
            return
        
        # Support for Private Messages (DM)
        if message.guild is None:
            await self._handle_dm(message)
            return
        
        if message.channel.id != self.target_channel_id:
            return
            
        if self.processing_lock.locked():
            return

        self._remember_user(message.author)
        clean_content = message.content.replace(f"<@{self.user.id}>", "@Me")
        
        if message.channel.id not in self.chat_memories:
            self.chat_memories[message.channel.id] = deque(maxlen=HISTORY_LIMIT)
        
        real_name = await self.get_real_name(message.author, message.guild)
        self.chat_memories[message.channel.id].append((real_name, clean_content))

        # Reset proactivity timer
        self.last_activity_time = time.time()
        self._schedule_next_proactivity()

        # Logic for debouncing (Group related messages into one response batch)
        is_direct = self.user.mentioned_in(message) or (message.reference and message.reference.cached_message and message.reference.cached_message.author.id == self.user.id)
        
        if is_direct:
            self.channel_mentions_pending[message.channel.id] = True

        this_msg_time = time.time()
        self.channel_debounces[message.channel.id] = this_msg_time

        # Reading delay simulation
        wait_time = random.uniform(2.0, 4.5)
        await asyncio.sleep(wait_time)

        if self.channel_debounces.get(message.channel.id) != this_msg_time:
            return

        if self.processing_lock.locked():
            return

        async with self.processing_lock:
            mention_was_pending = self.channel_mentions_pending.get(message.channel.id, False)
            self.channel_mentions_pending[message.channel.id] = False
            
            history_list = list(self.chat_memories.get(message.channel.id, []))
            my_nickname = message.guild.me.display_name
            
            response = await asyncio.to_thread(self.brain.decide_and_respond, history_list, my_nickname, mention_was_pending)

            if response:
                async with message.channel.typing():
                    await self._send_response_package(message.channel, response, my_nickname, message.channel.id, message if mention_was_pending else None)

    async def _handle_dm(self, message: discord.Message):
        """Handles response logic for Direct Messages."""
        async with self.processing_lock:
            dm_key = f"dm_{message.author.id}"
            if dm_key not in self.chat_memories:
                self.chat_memories[dm_key] = deque(maxlen=HISTORY_LIMIT)
            
            self.chat_memories[dm_key].append((message.author.name, message.content))
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            history_list = list(self.chat_memories[dm_key])
            response = await asyncio.to_thread(self.brain.decide_and_respond, history_list, "Ian", True)
            
            if response:
                async with message.channel.typing():
                    await self._send_response_package(message.channel, response, "Ian", dm_key, message)

    async def _send_response_package(self, channel: Any, response_list: List[str], my_name: str, memory_id: Any, reply_to: Optional[discord.Message] = None):
        """Sequentially sends a package of messages with typing delays."""
        for i, line in enumerate(response_list):
            formatted_line = self._format_mentions(line)
            
            # Simulated typing speed based on length
            speed = random.uniform(*TYPING_SPEED_RANGE)
            duration = min(len(line) * speed, 8.0)
            await asyncio.sleep(duration)

            try:
                if i == 0 and reply_to:
                    await reply_to.reply(formatted_line, mention_author=True)
                else:
                    await channel.send(formatted_line)
                
                self.chat_memories[memory_id].append((my_name, line))
                print(f"🗣️ Sent: {line}")
                
                # Small pause between consecutive messages
                if i < len(response_list) - 1:
                    await asyncio.sleep(random.uniform(1.0, 2.5))
            except Exception as e:
                print(f"Failed to send message: {e}")

if __name__ == "__main__":
    if TOKEN:
        client = KirgClient()
        client.run(TOKEN)
    else:
        print("❌ KIRG_TOKEN not found in environment.")
