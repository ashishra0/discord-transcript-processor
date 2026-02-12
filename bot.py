import os
import asyncio
from pathlib import Path

import discord
import anthropic
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
WATCH_CHANNEL_ID = int(os.environ["WATCH_CHANNEL_ID"])
OUTPUT_CHANNEL_ID = int(os.environ.get("OUTPUT_CHANNEL_ID") or 0) or WATCH_CHANNEL_ID
TRANSCRIPT_BOT_ID = os.environ.get("TRANSCRIPT_BOT_ID")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "4096"))

PROMPT_DIR = Path(__file__).parent
QUIZ_PROMPT = (PROMPT_DIR / "prompt.md").read_text().strip()
GRADE_PROMPT = (PROMPT_DIR / "grade_prompt.md").read_text().strip()
FEYNMAN_PROMPT = (PROMPT_DIR / "feynman_prompt.md").read_text().strip()
FEYNMAN_GRADE_PROMPT = (PROMPT_DIR / "feynman_grade_prompt.md").read_text().strip()

intents = discord.Intents(messages=True, message_content=True, guilds=True)
client = discord.Client(intents=intents)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# State machine per channel
# Phase: "mcq" -> waiting for MCQ answers
#         "feynman" -> waiting for Feynman explanation
sessions: dict[int, dict] = {}


async def call_claude(system: str, user_content: str) -> str:
    """Send a message to Claude and return the response."""
    response = await asyncio.to_thread(
        claude.messages.create,
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_content}],
    )
    return response.content[0].text


async def send_long_message(channel, text: str, reference=None):
    """Split and send a message that might exceed Discord's 2000 char limit."""
    chunks = []
    while len(text) > 2000:
        split_at = text.rfind("\n", 0, 2000)
        if split_at == -1:
            split_at = 2000
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    chunks.append(text)

    for i, chunk in enumerate(chunks):
        ref = reference if i == 0 else None
        await channel.send(chunk, reference=ref)


def is_transcript(message: discord.Message) -> bool:
    """Check if this message is a transcript from the watched bot."""
    if message.channel.id != WATCH_CHANNEL_ID:
        return False
    if message.author.id == client.user.id:
        return False
    if TRANSCRIPT_BOT_ID and str(message.author.id) != TRANSCRIPT_BOT_ID:
        return False
    if len(message.content) < 100 and not message.attachments:
        return False
    return True


def is_user_reply(message: discord.Message) -> bool:
    """Check if this is a non-bot reply in a channel with an active session."""
    if message.author.bot:
        return False
    return message.channel.id in sessions


def looks_like_mcq_answer(text: str) -> bool:
    """Check if text looks like MCQ answers (e.g. '1A 2C 3B 4D 5A')."""
    upper = text.strip().upper()
    answer_chars = sum(1 for ch in upper if ch in "ABCD")
    return answer_chars >= 3


@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    print(f"Watching channel: {WATCH_CHANNEL_ID}")
    print(f"Output channel:   {OUTPUT_CHANNEL_ID}")
    print(f"Model:            {CLAUDE_MODEL}")
    if TRANSCRIPT_BOT_ID:
        print(f"Filtering for bot: {TRANSCRIPT_BOT_ID}")


@client.event
async def on_message(message: discord.Message):

    # --- New transcript arrives → Start MCQ phase ---
    if is_transcript(message):
        transcript = message.content
        for attachment in message.attachments:
            if attachment.filename.endswith((".md", ".txt")):
                file_bytes = await attachment.read()
                transcript += "\n\n" + file_bytes.decode("utf-8", errors="replace")

        print(f"Transcript received ({len(transcript)} chars) from {message.author}")
        output_channel = client.get_channel(OUTPUT_CHANNEL_ID) or message.channel

        async with output_channel.typing():
            try:
                questions = await call_claude(QUIZ_PROMPT, transcript)
            except Exception as e:
                await output_channel.send(f"**Error generating quiz:** {e}")
                return

        header = "**Reading Quiz** — answer with your choices, e.g. `1A 2C 3B 4D 5A`\n\n"
        await send_long_message(output_channel, header + questions, reference=message)

        sessions[output_channel.id] = {
            "phase": "mcq",
            "transcript": transcript,
            "questions": questions,
        }
        print("Quiz posted, waiting for answers...")
        return

    if not is_user_reply(message):
        return

    channel_id = message.channel.id
    session = sessions[channel_id]

    # --- MCQ phase: grade answers, then move to Feynman ---
    if session["phase"] == "mcq" and looks_like_mcq_answer(message.content):
        grading_input = (
            f"## Original Transcript\n{session['transcript']}\n\n"
            f"## Quiz Questions\n{session['questions']}\n\n"
            f"## User's Answers\n{message.content}"
        )

        print(f"Grading MCQ answers from {message.author}...")
        async with message.channel.typing():
            try:
                result = await call_claude(GRADE_PROMPT, grading_input)
            except Exception as e:
                await message.channel.send(f"**Error grading quiz:** {e}")
                return

        await send_long_message(message.channel, result, reference=message)

        # Transition to Feynman phase
        print("MCQ graded. Starting Feynman challenge...")
        async with message.channel.typing():
            try:
                challenge = await call_claude(FEYNMAN_PROMPT, session["transcript"])
            except Exception as e:
                await message.channel.send(f"**Error generating Feynman challenge:** {e}")
                del sessions[channel_id]
                return

        await send_long_message(message.channel, "\n\n---\n\n**Feynman Challenge** — explain it in your own words:\n\n" + challenge)

        session["phase"] = "feynman"
        session["feynman_challenge"] = challenge
        print("Feynman challenge posted, waiting for explanation...")
        return

    # --- Feynman phase: evaluate the user's explanation ---
    if session["phase"] == "feynman":
        # Any non-trivial message counts as their explanation
        if len(message.content.strip()) < 20:
            await message.channel.send("Give it a real shot — try to explain the concept in a few sentences at least.")
            return

        feynman_input = (
            f"## Original Transcript\n{session['transcript']}\n\n"
            f"## Concept & Challenge\n{session['feynman_challenge']}\n\n"
            f"## Student's Explanation\n{message.content}"
        )

        print(f"Evaluating Feynman explanation from {message.author}...")
        async with message.channel.typing():
            try:
                feedback = await call_claude(FEYNMAN_GRADE_PROMPT, feynman_input)
            except Exception as e:
                await message.channel.send(f"**Error evaluating explanation:** {e}")
                return

        await send_long_message(message.channel, feedback, reference=message)

        # Session complete
        del sessions[channel_id]
        print("Session complete.")
        return


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
