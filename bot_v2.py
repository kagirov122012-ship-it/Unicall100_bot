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

# хранение tempmail в памяти: {telegram_id: (login, domain)}
temp_mails = {}

# ================= ПАРОЛИ =================
def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

# ================= TEMPMAIL =================
def generate_temp_login():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

TEMP_DOMAIN = "1secmail.com"

async def get_mail_messages(login, domain):
    url = (
        f"https://www.1secmail.com/api/v1/"
        f"?action=getMessages&login={login}&domain={domain}"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=15) as resp:
            return await resp.json()

# ================= КУРС ВАЛЮТ =================
async def get_rates():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://open.er-api.com/v6/latest/USD",
                timeout=10
            ) as resp:
                data = await resp.json()

                usd = data["rates"]["RUB"]
                eur = data["rates"]["EUR"] * usd
                cny = data["rates"]["CNY"] * usd

                return (
                    "💰 Курс валют:\n"
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
        "🤖 Helper Tools Bot PRO\n\n"
        "📷 /qr текст или ссылка — создать QR\n"
        "📩 /tempmail — временная почта\n"
        "📬 /checkmail — проверить письма\n"
        "/course — курс валют\n"
        "/pass — пароль\n"
        "🧮 Пример: 2+2",
        reply_markup=ReplyKeyboardRemove()
    )

# ================= /help =================
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(
        "/qr текст_или_ссылка — создать QR\n"
        "/tempmail — создать временную почту\n"
        "/checkmail — проверить письма\n"
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

# ================= TEMPMAIL =================
@dp.message(Command("tempmail"))
async def create_tempmail(msg: types.Message):
    login = generate_temp_login()
    temp_mails[msg.from_user.id] = (login, TEMP_DOMAIN)

    await msg.answer(
        f"📩 Временная почта создана:\n"
        f"`{login}@{TEMP_DOMAIN}`\n\n"
        f"Проверка: /checkmail",
        parse_mode="Markdown"
    )

@dp.message(Command("checkmail"))
async def checkmail(msg: types.Message):
    user_id = msg.from_user.id

    if user_id not in temp_mails:
        await msg.answer("❌ Сначала создай почту: /tempmail")
        return

    login, domain = temp_mails[user_id]

    try:
        mails = await get_mail_messages(login, domain)

        if not mails:
            await msg.answer("📭 Писем пока нет")
            return

        text = "📬 Входящие:\n\n"
        for i, mail in enumerate(mails[:5], 1):
            sender = mail.get("from", "Unknown")
            subject = mail.get("subject", "Без темы")
            text += f"{i}. От: {sender}\nТема: {subject}\n\n"

        await msg.answer(text)

    except Exception as e:
        logging.error(f"TempMail ошибка: {e}")
        await msg.answer("⚠️ Ошибка проверки почты")

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

# ================= ЗАПУСК =================
async def main():
    logging.info("🚀 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
