import os
import asyncio
import random
import string
import logging
import sqlite3

import aiohttp
from yt_dlp import YoutubeDL

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = Bot(token=TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# ================= DB =================
conn = sqlite3.connect("bot.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    downloads INTEGER DEFAULT 0,
    premium INTEGER DEFAULT 0
)
""")
conn.commit()


# ================= MENU =================
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 YouTube")],
        [KeyboardButton(text="🎧 MP3")],
        [KeyboardButton(text="💰 Premium")],
        [KeyboardButton(text="📊 Stats")]
    ],
    resize_keyboard=True
)


# ================= UTIL =================
def add_user(user_id):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()


def inc_download(user_id):
    cur.execute("UPDATE users SET downloads = downloads + 1 WHERE id=?", (user_id,))
    conn.commit()


def is_premium(user_id):
    cur.execute("SELECT premium FROM users WHERE id=?", (user_id,))
    return cur.fetchone()[0] == 1


# ================= START =================
@dp.message(Command("start"))
async def start(msg: types.Message):
    add_user(msg.from_user.id)
    await msg.answer("🚀 PRO Bot запущен", reply_markup=menu)


# ================= PREMIUM =================
@dp.message(lambda m: m.text == "💰 Premium")
async def premium(msg: types.Message):
    await msg.answer(
        "💎 Premium:\n"
        "- Без лимитов\n"
        "- 1080p\n"
        "- MP3\n\n"
        "Свяжитесь с админом для покупки"
    )


# ================= STATS =================
@dp.message(lambda m: m.text == "📊 Stats")
async def stats(msg: types.Message):
    cur.execute("SELECT downloads FROM users WHERE id=?", (msg.from_user.id,))
    d = cur.fetchone()[0]
    await msg.answer(f"📊 Твои скачивания: {d}")


# ================= SAFE DOWNLOAD =================
def download_youtube(url, mp3=False, quality="best"):
    outtmpl = "video.%(ext)s"

    ydl_opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "force_ipv4": True,
        "retries": 15,
        "fragment_retries": 15,
    }

    if mp3:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts["format"] = "bestvideo+bestaudio/best"

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

        if mp3:
            filename = filename.rsplit(".", 1)[0] + ".mp3"

        return filename, info.get("title", "video")


# ================= YOUTUBE HANDLER =================
@dp.message(lambda m: m.text and ("youtube.com" in m.text or "youtu.be" in m.text))
async def youtube(msg: types.Message):
    add_user(msg.from_user.id)

    url = msg.text.strip()
    wait = await msg.answer("⏳ Загружаю...")

    try:
        mp3_mode = False

        # premium check
        premium = is_premium(msg.from_user.id)

        filename, title = download_youtube(url, mp3=mp3_mode)

        video = FSInputFile(filename)

        await msg.answer_video(video, caption=f"🎬 {title}")

        inc_download(msg.from_user.id)

        await wait.delete()

        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        await wait.edit_text(f"⚠️ Ошибка:\n{repr(e)}")


# ================= MP3 =================
@dp.message(lambda m: m.text == "🎧 MP3")
async def mp3_hint(msg: types.Message):
    await msg.answer("🎧 Отправь YouTube ссылку с командой:\n\nmp3 https://...")

@dp.message(lambda m: m.text and m.text.startswith("mp3 "))
async def mp3_download(msg: types.Message):
    url = msg.text.replace("mp3 ", "").strip()
    wait = await msg.answer("🎧 Скачиваю MP3...")

    try:
        filename, title = download_youtube(url, mp3=True)

        audio = FSInputFile(filename)

        await msg.answer_audio(audio, caption=f"🎧 {title}")

        inc_download(msg.from_user.id)

        await wait.delete()

        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        await wait.edit_text(f"⚠️ Ошибка:\n{repr(e)}")


# ================= SIMPLE FLOOD CONTROL =================
user_last = {}

@dp.message()
async def anti_flood(msg: types.Message):
    uid = msg.from_user.id
    now = asyncio.get_event_loop().time()

    if uid in user_last and now - user_last[uid] < 5:
        return

    user_last[uid] = now


# ================= RUN =================
async def main():
    logging.info("PRO BOT STARTED")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
