"""
Daily Inspiration Bot  (v2 — 100 sentences, English + 1 random language)
------------------------------------------------------------------------
Every day at 09:00 it sends ONE encouraging sentence in English plus the
same sentence in one randomly chosen language (Chinese, Japanese, German,
French, Spanish or Italian).

How translation works:
  - The 100 sentences are stored in English only (below).
  - Each day the bot translates the chosen sentence into the day's random
    language using the free MyMemory API (no API key required).
  - Results are cached in translations_cache.json so the same sentence is
    never translated twice.

Deploy exactly like the habit bot:
  requirements.txt   ->  python-telegram-bot[job-queue]==21.6
  Render env vars    ->  BOT_TOKEN  and  PYTHON_VERSION = 3.12.8
  Start command      ->  python quote_bot.py
  Keep awake         ->  UptimeRobot pinging the Render URL.

The sentences are original lines (not copyrighted quotes); use them freely.
"""

import os
import json
import random
import asyncio
import threading
import urllib.parse
import urllib.request
import datetime as dt
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

TOKEN = os.environ.get("BOT_TOKEN", "PASTE_YOUR_TOKEN_HERE")
TIMEZONE = "Asia/Taipei"
SEND_TIME = "09:00"  # 24-hour clock

# The "other" languages the bot can pick from each day (besides English).
# Codes are what the MyMemory API expects.
LANGS = {
    "zh-CN": "\U0001F1E8\U0001F1F3 \u4E2D\u6587",
    "ja":    "\U0001F1EF\U0001F1F5 \u65E5\u672C\u8A9E",
    "de":    "\U0001F1E9\U0001F1EA Deutsch",
    "fr":    "\U0001F1EB\U0001F1F7 Fran\u00E7ais",
    "es":    "\U0001F1EA\U0001F1F8 Espa\u00F1ol",
    "it":    "\U0001F1EE\U0001F1F9 Italiano",
}

CACHE_FILE = "translations_cache.json"

QUOTES = [
    "Every small step you take today is building the person you're becoming.",
    "You have survived every hard day so far; today is no different.",
    "Progress is quiet; trust it even when you cannot see it.",
    "Your effort matters, even when no one is watching.",
    "Be patient with yourself; growth takes the time it takes.",
    "The courage to begin is already a kind of victory.",
    "You are allowed to start again, as many times as you need.",
    "Small consistent actions outlast bursts of motivation.",
    "What feels difficult today is making you stronger for tomorrow.",
    "Your worth is not measured by how much you accomplish.",
    "Rest is part of the work, not a betrayal of it.",
    "One honest attempt is worth more than a perfect plan.",
    "You don't have to feel ready to take the first step.",
    "The fact that you keep trying says everything about you.",
    "Today is a fresh page; write something kind on it.",
    "Difficult roads often lead to beautiful places.",
    "Believe in the work you are doing, even on slow days.",
    "You are closer than you think to where you want to be.",
    "Kindness toward yourself is not weakness; it is wisdom.",
    "Keep going; the world is better with you in it.",
    "You don't have to do it all at once; you just have to begin.",
    "Mistakes are proof that you are trying, not that you are failing.",
    "The hardest part of any journey is often the first quiet step.",
    "Give yourself the same patience you would give a good friend.",
    "Some days the bravest thing is simply to continue.",
    "Your pace is your own, and it is enough.",
    "Growth rarely feels like growth while it is happening.",
    "You are not behind; you are exactly where your story needs you.",
    "A small win today is still a win worth keeping.",
    "Let today be gentle, and let that be enough.",
    "The effort you cannot see is still shaping who you are.",
    "Courage is not the absence of fear, but moving forward with it.",
    "You have begun difficult things before, and you can begin again.",
    "Tend to today, and tomorrow will have something to stand on.",
    "What you practice quietly will one day show clearly.",
    "You are allowed to be proud of how far you have come.",
    "Even slow progress is still moving away from where you started.",
    "The version of you that keeps showing up is the one that grows.",
    "Be kind to the person you were before you knew better.",
    "Your story is still being written, and the good parts are coming.",
    "Doing your best looks different every day, and that is okay.",
    "Trust that the work you put in is not lost; it is gathering.",
    "A single deep breath can be the start of a better moment.",
    "You owe it to yourself to keep going a little longer.",
    "The light you are looking for is often closer than it seems.",
    "Hard seasons end, and you will still be standing when they do.",
    "You are learning, and learning is rarely tidy.",
    "Let your effort today be a quiet gift to your future self.",
    "Showing up imperfectly is far better than not showing up at all.",
    "You are stronger than the thought that says you cannot.",
    "Be brave enough to be a beginner again.",
    "The smallest act of care for yourself still counts.",
    "You don't have to earn your right to rest.",
    "Every sunrise is a fresh invitation to try again.",
    "Your potential is not erased by a single difficult day.",
    "Keep planting; not every seed shows its growth at once.",
    "You are doing better than the harsh voice in your head admits.",
    "Choose one small thing, and let that be your whole task for now.",
    "The path becomes clearer only as you walk it.",
    "You have permission to change your mind and to grow.",
    "What matters is not how fast, but that you keep facing forward.",
    "Today's effort is tomorrow's quiet confidence.",
    "You are worthy of the goals you are reaching toward.",
    "Gentleness with yourself is a strength, not a shortcut.",
    "The work you do in private builds the life you live in public.",
    "You can be both a work in progress and enough right now.",
    "Let go of the day you planned and embrace the day you have.",
    "Persistence is just patience wearing work clothes.",
    "You have made it through every single one of your worst days.",
    "Begin where you are, with what you have; it is plenty.",
    "Your kindness today may be the thing someone else remembers.",
    "A calm mind is built one steady breath at a time.",
    "The dream is worth the discomfort of the first awkward steps.",
    "You are not your worst moment; you are everything that follows it.",
    "Slow down enough to notice how far you have already come.",
    "Every effort, however small, adds to who you are becoming.",
    "You are allowed to want more and to be grateful at the same time.",
    "The road ahead is shaped by the steps you take today.",
    "Be the friend to yourself that you have always needed.",
    "Courage often looks like an ordinary person trying one more time.",
    "Your future self is grateful for the choices you make now.",
    "There is strength in beginning before you feel certain.",
    "Let progress, not perfection, be the measure of your day.",
    "You can rest without quitting and pause without giving up.",
    "The quiet effort of today becomes the strength of tomorrow.",
    "You are capable of more patience and grace than you realize.",
    "A gentle start still counts as a start.",
    "Hold on; the chapter you are in is not the whole book.",
    "You bring something to this world that no one else can.",
    "Keep your eyes on the next step, not the whole staircase.",
    "The fact that it is hard does not mean you are doing it wrong.",
    "You are growing roots even on the days you feel stuck.",
    "Let today's small effort be something you thank yourself for later.",
    "Be proud of every time you chose to keep going.",
    "Your willingness to try again is a quiet kind of bravery.",
    "You do not have to be fearless, only willing.",
    "The person you are becoming is worth every patient day.",
    "Treat yourself as someone worth taking care of, because you are.",
    "Every honest effort moves the world a little, including yours.",
    "You woke up to another chance today, and that alone is hopeful.",
]

# ---------------------------------------------------------------------------
# Keep-alive web server (for Render's free tier)
# ---------------------------------------------------------------------------

class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Quote bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

    def log_message(self, *args):
        pass

def start_web_server():
    port = int(os.environ.get("PORT", "8080"))
    HTTPServer(("0.0.0.0", port), PingHandler).serve_forever()

# ---------------------------------------------------------------------------
# Translation (free MyMemory API) with on-disk caching
# ---------------------------------------------------------------------------

def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_cache(cache: dict) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def translate(text: str, target_code: str) -> str:
    """Translate English -> target language. Returns text unchanged on failure."""
    cache = _load_cache()
    key = f"{target_code}::{text}"
    if key in cache:
        return cache[key]

    try:
        url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(
            {"q": text, "langpair": f"en|{target_code}"}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "quote-bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        translated = data["responseData"]["translatedText"].strip()
        if translated:
            cache[key] = translated
            _save_cache(cache)
            return translated
    except Exception as e:
        print("Translation failed:", e)

    return text  # graceful fallback: show English if translation unavailable

# ---------------------------------------------------------------------------
# Daily selection + message building
# ---------------------------------------------------------------------------

def _todays_pick():
    """Deterministic per date: same quote + same 'other' language all day."""
    seed = dt.date.today().toordinal()
    quote = QUOTES[seed % len(QUOTES)]
    rng = random.Random(seed)
    lang_code = rng.choice(list(LANGS.keys()))
    return quote, lang_code

async def build_message() -> str:
    quote, lang_code = _todays_pick()
    # Run the blocking network call off the event loop.
    translated = await asyncio.to_thread(translate, quote, lang_code)

    label = LANGS[lang_code]
    msg = (
        "\U0001F305 Today's encouragement\n\n"
        f"\U0001F1EC\U0001F1E7 English\n{quote}\n\n"
        f"{label}\n{translated}"
    )
    if translated == quote:  # translation API was unavailable
        msg += "\n\n(Translation unavailable today \u2014 English shown.)"
    return msg

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()

    hour, minute = map(int, SEND_TIME.split(":"))
    context.job_queue.run_daily(
        send_daily,
        time=dt.time(hour=hour, minute=minute, tzinfo=ZoneInfo(TIMEZONE)),
        chat_id=chat_id,
        name=str(chat_id),
    )

    await update.message.reply_text(
        "\U0001F30D You're subscribed!\n\n"
        f"Every day at {SEND_TIME} ({TIMEZONE}) I'll send one encouraging "
        "sentence in English plus one other language (chosen at random).\n\n"
        "/today \u2013 see today's sentence now\n"
        "/stop \u2013 unsubscribe"
    )
    await update.message.reply_text(await build_message())

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(await build_message())

async def send_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=await build_message(),
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    for job in context.job_queue.get_jobs_by_name(str(chat_id)):
        job.schedule_removal()
    await update.message.reply_text("\U0001F44B Unsubscribed. Send /start to resume.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise SystemExit("Set your bot token via the BOT_TOKEN environment variable.")

    threading.Thread(target=start_web_server, daemon=True).start()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("stop", stop))

    print(f"Quote bot is running with {len(QUOTES)} sentences. Ctrl+C to stop.")
    app.run_polling()

if __name__ == "__main__":
    main()
