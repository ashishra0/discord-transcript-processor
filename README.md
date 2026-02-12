# Readback

Turn your book club's reading sessions into active learning — automatically.

Readback is a Discord bot that hooks into [DiscMeet](https://discmeet.com/) transcripts and runs you through a two-phase study loop right in the same thread:

1. **Quiz** — 5 multiple-choice questions that test understanding, not just recall
2. **Feynman challenge** — pick a concept, explain it in your own words, get feedback on gaps

No setup per-session. Drop in a transcript, the bot takes it from there.

## How it works

```
You read aloud in a Discord voice channel
    ↓
DiscMeet transcribes and posts to a thread
    ↓
Readback detects the formatted-transcript-*.txt attachment
    ↓
Generates 5 MCQs → you answer (e.g. "1A 2C 3B 4D 5A")
    ↓
Grades your answers with explanations
    ↓
Issues a Feynman challenge → you explain a concept in your own words
    ↓
Feedback on what you got and what to revisit
```

Everything stays inside the DiscMeet thread — one thread per reading session.

## Setup

### 1. Create a Discord bot

- Go to [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**
- **Bot** tab → **Reset Token** → copy the token
- Enable **Message Content Intent** under Privileged Gateway Intents
- **OAuth2 → URL Generator** → scope: `bot`, permissions: `Read Messages/View Channels`, `Send Messages`, `Read Message History`
- Open the generated URL to invite the bot to your server

### 2. Get your channel ID

Enable **Developer Mode** in Discord (Settings → Advanced), then right-click the channel where DiscMeet posts → **Copy Channel ID**.

### 3. Configure

```bash
cp .env.example .env
# Fill in DISCORD_BOT_TOKEN, ANTHROPIC_API_KEY, WATCH_CHANNEL_ID
```

### 4. Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python bot.py
```

## Deploy (systemd)

```bash
sudo cp transcript-bot.service /etc/systemd/system/
# Edit the service file: set User and WorkingDirectory to match your setup
sudo systemctl daemon-reload
sudo systemctl enable --now transcript-bot
sudo journalctl -u transcript-bot -f
```

## Customise the prompts

All AI prompts are standalone `.md` files — edit them without touching code:

| File | Purpose |
|------|---------|
| `prompt.md` | MCQ generation |
| `grade_prompt.md` | MCQ grading + explanations |
| `feynman_prompt.md` | Selects a concept and issues the challenge |
| `feynman_grade_prompt.md` | Evaluates your explanation |

Restart the bot after editing.

## Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | — | Discord bot token |
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key |
| `WATCH_CHANNEL_ID` | Yes | — | Channel where DiscMeet posts (bot watches threads under it) |
| `TRANSCRIPT_BOT_ID` | No | — | Only process attachments from this bot user ID |
| `CLAUDE_MODEL` | No | `claude-sonnet-4-5-20250929` | Claude model to use |
| `MAX_TOKENS` | No | `4096` | Max tokens per response |
