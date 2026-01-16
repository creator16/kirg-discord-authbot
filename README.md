# 🤖 Kirg AI - Realistic User Simulator

Kirg is a high-fidelity Discord user simulator (Self-bot) powered by LLMs. It mimics human behavior, including typing delays, reading pauses, and spontaneous interactions.

---

## ✨ Features
- **Deterministic Persona**: Acts as "Ian", a 17-year-old Discord native.
- **Dual Provider Support**: Seamlessly switch between **OpenRouter** and **Google Gemini (Native)**.
- **Smart Debouncing**: Accumulates messages to reply in batches, just like a human.
- **Context-Aware**: Remembers recent history to stay relevant.
- **Proactive Engagement**: Initiates conversation if the chat stays quiet for too long.
- **Realistic Typing**: Variable typing speeds and pauses between multi-line responses.
- **Mention Mapping**: Automatically maps user names in AI output to real Discord mentions.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/creator16/kirg-discord-authbot.git
   cd kirg-discord-authbot
   ```

2. **Setup virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuration

1. **Environment Variables**:
   Copy `.env.example` to `.env` and fill in your keys:
   - `AI_PROVIDER`: Choose between `openrouter` or `gemini`.
   - `KIRG_TOKEN`: Your Discord User Token (Self-bot).
   - `OPENROUTER_API_KEY`: Required if using OpenRouter.
   - `GEMINI_API_KEY`: Required if using Gemini.

2. **Channels Setup**:
   Modify `config.json` to include the channels you want to target:
   ```json
   {
       "channels": {
           "general": "CHANNEL_ID_HERE"
       },
       "last_channel": "general"
   }
   ```

## 🚀 Running

Start the simulator:
```bash
python main.py
```

Choose your target channel when prompted, and the AI will take over.

---

## ⚠️ Disclaimer
This is a **Self-bot**. Using automated scripts on user accounts can violate Discord's Terms of Service. Use this at your own risk.

## ⚖️ License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Made with ❤️ for the **Open Source Society**.
