import os
import asyncio
import random
import string
import logging
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardRemove
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
        "🤖 Бот запущен\n\n"
        "📥 YouTube — отправь ссылку\n"
        "/course — курс валют\n"
        "/pass — пароль"
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
@dp.message(lambda msg: msg.text and ('youtube.com' in msg.text or 'youtu.be' in msg.text))
async def youtube(msg: types.Message):
    url = msg.text.strip()
    wait = await msg.answer("⏳ Загружаю видео...")

    try:
        ydl_opts = {
            "format": "best",
            "outtmpl": "video.%(ext)s",

            "cookiefile": "cookies.txt",

            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,

            "extractor_args": {
                "youtube": {
                    "player_client": ["android"]
                }
            },

            "force_ipv4": True,

"js_runtimes": {
    "deno": {}
},
            "retries": 10,
            "socket_timeout": 30,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            filename = ydl.prepare_filename(info)
            title = info.get("title", "Видео")[:100]

            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                for ext in [".mp4", ".mkv", ".webm"]:
                    if os.path.exists(base + ext):
                        filename = base + ext
                        break

        await msg.answer_video(
            types.FSInputFile(filename),
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
