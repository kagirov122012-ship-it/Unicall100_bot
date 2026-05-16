import os
import asyncio
import random
import string
import logging
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
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
        "🧮 Пример 2+2"
    )


# ================= /help =================
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer("/course /pass\nИли отправь YouTube ссылку или пример")


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


# ================= YOUTUBE =================
import os
import asyncio
from yt_dlp import YoutubeDL
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile


# ===== КНОПКИ =====
@dp.message(lambda msg: msg.text and ('youtube.com' in msg.text or 'youtu.be' in msg.text))
async def youtube(msg: types.Message):
    url = msg.text.strip()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 720p", callback_data=f"yt|720|{url}"),
            InlineKeyboardButton(text="🔥 1080p", callback_data=f"yt|1080|{url}")
        ]
    ])

    await msg.answer("Выбери качество 👇", reply_markup=keyboard)


# ===== ЗАГРУЗКА =====
@dp.callback_query(lambda c: c.data.startswith("yt|"))
async def yt_download(call: types.CallbackQuery):
    try:
        _, quality, url = call.data.split("|")

        status_msg = await call.message.answer("⏳ Скачиваю видео...")

        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%').strip()
                asyncio.create_task(status_msg.edit_text(f"⬇️ {percent}"))

        ydl_opts = {
            'format': f'best[height<={quality}]',
            'outtmpl': 'video.%(ext)s',
            'noplaylist': True,
            'quiet': True,
            'progress_hooks': [progress_hook],
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get("title", "Видео")[:100]

        video = FSInputFile(filename)

        await call.message.answer_video(
            video,
            caption=f"🎬 {title}"
        )

        os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        await call.message.answer(f"⚠️ Ошибка:\n{e}")

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
