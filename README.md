# Discord Transcript Processor

A Discord bot that turns book reading transcripts into active learning sessions. It watches for transcripts posted by [DiscMeet](https://discmeet.com/) and runs you through a two-phase study loop:

1. **MCQ Quiz** — 5 multiple-choice questions that test understanding, not just recall
2. **Feynman Challenge** — pick a key concept and explain it in your own words, then get feedback on gaps

## How it works

```
You read aloud in a voice channel
    ↓
DiscMeet transcribes and posts to a thread
    ↓
Bot picks up the formatted-transcript-*.txt file
    ↓
Generates 5 MCQs → you answer (e.g. "1A 2C 3B 4D 5A")
    ↓
Grades your answers with explanations
    ↓
Feynman challenge → you explain a concept in your own words
    ↓
Feedback on what you nailed and what to revisit
```

Everything happens inside the DiscMeet thread — one thread per reading session.

## Setup

### 1. Create a Discord bot

- Go to https://discord.com/developers/applications → **New Application**
- **Bot** tab → **Reset Token** → copy it
- Enable **Message Content Intent** under Privileged Gateway Intents
- **OAuth2** → **URL Generator** → select `bot` scope
- Bot permissions: `Read Messages/View Channels`, `Send Messages`, `Read Message History`
- Open the generated URL to invite the bot to your server

### 2. Get your IDs

Enable **Developer Mode** in Discord (Settings → Advanced), then:

- Right-click the channel where DiscMeet posts → **Copy Channel ID**
- Right-click the DiscMeet bot → **Copy User ID** (optional, for filtering)

### 3. Configure

```bash
cp .env.example .env
```

Fill in `DISCORD_BOT_TOKEN`, `ANTHROPIC_API_KEY`, and `WATCH_CHANNEL_ID` at minimum.

### 4. Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python bot.py
```

## Deploy (systemd)

```bash
sudo cp transcript-bot.service /etc/systemd/system/
# Edit the service file to match your user and paths
sudo systemctl daemon-reload
sudo systemctl enable --now transcript-bot
sudo journalctl -u transcript-bot -f
```

## Customizing prompts

All LLM prompts are separate `.md` files — edit them without touching code:

| File | Purpose |
|------|---------|
| `prompt.md` | MCQ generation |
| `grade_prompt.md` | MCQ grading and explanations |
| `feynman_prompt.md` | Picks a concept, issues the challenge |
| `feynman_grade_prompt.md` | Evaluates your explanation |

Restart the bot after editing prompts.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Discord bot token |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `WATCH_CHANNEL_ID` | Yes | Channel ID where DiscMeet posts (watches threads under it) |
| `OUTPUT_CHANNEL_ID` | No | Output channel ID (defaults to same thread) |
| `TRANSCRIPT_BOT_ID` | No | Only process messages from this bot |
| `CLAUDE_MODEL` | No | Claude model (default: `claude-sonnet-4-5-20250929`) |
| `MAX_TOKENS` | No | Max response tokens (default: `4096`) |
