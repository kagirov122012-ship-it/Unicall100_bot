import os
import asyncio
import random
import string
import logging
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from yt_dlp import YoutubeDL


# ================= ЛОГИ =================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ================= ТОКЕН =================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Не найден BOT_TOKEN!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# хранение ссылок пользователей
user_links = {}

# антиспам
user_last = {}


# ================= ПАРОЛИ =================
def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))


# ================= КУРС ВАЛЮТ =================
async def get_rates():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=10
            ) as resp:
                data = await resp.json()

                usd = data['rates']['RUB']
                eur = data['rates']['EUR'] * usd
                cny = data['rates']['CNY'] * usd

                return (
                    f"💰 Курс:\n"
                    f"🇺🇸 USD: {usd:.2f} ₽\n"
                    f"🇪🇺 EUR: {eur:.2f} ₽\n"
                    f"🇨🇳 CNY: {cny:.2f} ₽"
                )
    except Exception as e:
        logging.error(f"Ошибка курса: {e}")
        return "❌ Ошибка получения курса"


# ================= КАЛЬКУЛЯТОР =================
def calc(expr):
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expr):
            return None
        return eval(expr)
    except:
        return None


# ================= /start =================
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        "🤖 Бот-помощник\n\n"
        "📥 YouTube ссылка — скачаю видео\n"
        "/course — курс валют\n"
        "/pass — пароль\n"
        "🧮 Просто отправь пример: 2+2"
    )


# ================= /help =================
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(
        "Команды:\n"
        "/course\n"
        "/pass [длина]\n"
        "или YouTube ссылка\n"
        "или пример 2+2"
    )


# ================= /course =================
@dp.message(Command("course"))
async def course(msg: types.Message):
    await msg.answer(await get_rates())


# ================= /pass =================
@dp.message(Command("pass"))
async def password(msg: types.Message):
    parts = msg.text.split()
    length = 12

    if len(parts) > 1 and parts[1].isdigit():
        length = min(int(parts[1]), 32)

    await msg.answer(
        f"🔐 `{generate_password(length)}`",
        parse_mode="Markdown"
    )


# ================= YOUTUBE: ПОЛУЧЕНИЕ ССЫЛКИ =================
@dp.message(lambda msg: msg.text and ('youtube.com' in msg.text or 'youtu.be' in msg.text))
async def youtube(msg: types.Message):
    uid = msg.from_user.id
    now = asyncio.get_event_loop().time()

    # антиспам
    if uid in user_last and now - user_last[uid] < 5:
        await msg.answer("⏳ Подожди 5 секунд перед следующим запросом")
        return

    user_last[uid] = now

    url = msg.text.strip()
    user_links[uid] = url

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="360p", callback_data="q360"),
                InlineKeyboardButton(text="720p", callback_data="q720"),
                InlineKeyboardButton(text="1080p", callback_data="q1080")
            ]
        ]
    )

    await msg.answer(
        "🎬 Выбери качество:",
        reply_markup=kb
    )


# ================= CALLBACK КАЧЕСТВА =================
@dp.callback_query(lambda c: c.data.startswith("q"))
async def quality_selected(callback: types.CallbackQuery):
    uid = callback.from_user.id

    if uid not in user_links:
        await callback.message.edit_text("❌ Ссылка устарела, отправь заново")
        return

    url = user_links[uid]

    quality_map = {
        "q360": "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "q720": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "q1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    }

    fmt = quality_map[callback.data]

    wait = callback.message
    await wait.edit_text("⏳ Начинаю загрузку...")

    try:
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)

                if total:
                    percent = int(downloaded / total * 100)
                    asyncio.create_task(
                        wait.edit_text(f"📥 Загрузка: {percent}%")
                    )

        ydl_opts = {
            "format": fmt,
            "merge_output_format": "mp4",
            "outtmpl": "video.%(ext)s",

            # 🔥 cookies для обхода "Sign in to confirm you're not a bot"
            "cookiefile": "cookies.txt",

            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,

            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"]
                }
            },

            "force_ipv4": True,
            "retries": 20,
            "fragment_retries": 20,
            "socket_timeout": 30,

            "progress_hooks": [progress_hook]
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if not info:
                await wait.edit_text("⚠️ Не удалось получить данные видео")
                return

            filename = ydl.prepare_filename(info)
            title = info.get("title", "Видео")[:100]

            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in [".mp4", ".mkv", ".webm"]:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break

        video = FSInputFile(filename)

        await callback.message.answer_video(
            video,
            caption=f"🎬 {title}"
        )

        await wait.delete()

        if os.path.exists(filename):
            os.remove(filename)

    except Exception as e:
        logging.error(f"YouTube ошибка: {e}")
        await wait.edit_text(f"⚠️ ОШИБКА:\n{repr(e)}")
# ================= КАЛЬКУЛЯТОР =================
@dp.message(
    lambda msg:
    msg.text
    and any(op in msg.text for op in "+-*/")
    and "youtube.com" not in msg.text
    and not msg.text.startswith("/")
)
async def calculator(msg: types.Message):
    result = calc(msg.text.strip())

    if result is not None:
        await msg.answer(f"🧮 `{result}`", parse_mode="Markdown")
    else:
        await msg.answer("❌ Ошибка")


# ================= ГЛОБАЛЬНЫЕ ОШИБКИ =================
@dp.errors()
async def error_handler(event):
    logging.error(f"Ошибка: {event.exception}")
    return True


# ================= АВТОПЕРЕЗАПУСК =================
async def main():
    while True:
        try:
            logging.info("🚀 Бот запущен")
            await dp.start_polling(bot)

        except Exception as e:
            logging.error(f"Бот упал: {e}")
            logging.info("♻️ Перезапуск через 5 секунд...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
