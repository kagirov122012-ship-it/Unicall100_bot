import os
import asyncio
import random
import string
import logging
import aiohttp
import qrcode

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandObject
from aiogram.types import ReplyKeyboardRemove

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
    await msg.answer(" ", reply_markup=ReplyKeyboardRemove())
    await msg.answer(
        "🤖 Helper Tools Bot\n\n"
        "📷 /qr текст или ссылка — создать QR\n"
        "/course — курс валют\n"
        "/pass — пароль\n"
        "🧮 Пример: 2+2"
    )


# ================= /help =================
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(
        "/qr текст_или_ссылка — создать QR\n"
        "/course — курс валют\n"
        "/pass — пароль\n"
        "или отправь пример: 2+2"
    )


# ================= /course =================
@dp.message(Command("course"))
async def course(msg: types.Message):
    await msg.answer(await get_rates())


# ================= /pass =================
@dp.message(Command("pass"))
async def password(msg: types.Message, command: CommandObject):
    length = 12

    if command.args and command.args.isdigit():
        length = min(int(command.args), 32)

    await msg.answer(
        f"🔐 `{generate_password(length)}`",
        parse_mode="Markdown"
    )


# ================= QR =================
@dp.message(Command("qr"))
async def make_qr(msg: types.Message, command: CommandObject):
    if not command.args:
        await msg.answer("Напиши так:\n/qr текст_или_ссылка")
        return

    try:
        text = command.args.strip()

        img = qrcode.make(text)
        img.save("qr.png")

        photo = types.FSInputFile("qr.png")
        await msg.answer_photo(photo, caption="✅ QR готов")

        os.remove("qr.png")

    except Exception as e:
        logging.error(f"QR ошибка: {e}")
        await msg.answer("⚠️ Ошибка создания QR")


# ================= КАЛЬКУЛЯТОР =================
@dp.message(
    lambda msg:
    msg.text
    and any(op in msg.text for op in "+-*/")
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
