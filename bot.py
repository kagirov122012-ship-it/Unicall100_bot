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
@dp.message(lambda msg: msg.text and ('youtube.com' in msg.text or 'youtu.be' in msg.text))
async def youtube(msg: types.Message):
    url = msg.text.strip()

    await msg.answer("⏳ Загружаю видео...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.cobalt.best/",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "Unicall100Bot/1.0"
                },
                json={
                    "url": url,
                    "videoQuality": "720",
                    "filenameStyle": "basic"
                }
            ) as resp:
                data = await resp.json()

        if data.get("status") in ["tunnel", "redirect"]:
            await msg.answer_video(
                data["url"],
                caption="🎬 Готово!"
            )
        else:
            await msg.answer(f"⚠️ API ответ: {data}")

    except Exception as e:
        logging.error(f"YouTube ошибка: {e}")
        await msg.answer(f"⚠️ Ошибка: {e}")
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
