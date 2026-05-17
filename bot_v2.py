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

# ================= ТОКЕНЫ =================
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ Не найден BOT_TOKEN!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================= ПАМЯТЬ =================
temp_mails = {}
waiting_service = {}

# ================= TEMPMAIL DOMAINS =================
TEMP_DOMAINS = {
    "tiktok": "esiix.com",
    "discord": "wwjmp.com",
    "steam": "xojxe.com",
    "telegram": "yoggm.com",
    "default": "1secmail.com"
}

def generate_temp_login():
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))

async def get_mail_messages(login, domain):
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={login}&domain={domain}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status != 200:
                    return []
                return await resp.json(content_type=None)
    except:
        return []

# ================= ПАРОЛИ =================
def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

# ================= КУРСЫ =================
async def get_rates():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://open.er-api.com/v6/latest/USD", timeout=10) as resp:
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
    except:
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

# ================= START =================
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        "🚀 UTILITY HUB\n\n"
        "📷 /qr — создать QR\n"
        "📩 /tempmail — временная почта\n"
        "📬 /checkmail — проверить почту\n"
        "🔗 /short — сократить ссылку\n"
        "🌤 /weather — погода\n"
        "💰 /course — курс валют\n"
        "🔐 /pass — пароль\n"
        "🧮 Пример: 2+2",
        reply_markup=ReplyKeyboardRemove()
    )

# ================= HELP =================
@dp.message(Command("help"))
async def help_cmd(msg: types.Message):
    await msg.answer(
        "/qr текст_или_ссылка\n"
        "/tempmail\n"
        "/checkmail\n"
        "/short ссылка\n"
        "/weather город\n"
        "/course\n"
        "/pass\n"
        "или пример: 2+2"
    )

# ================= COURSE =================
@dp.message(Command("course"))
async def course(msg: types.Message):
    await msg.answer(await get_rates())

# ================= PASS =================
@dp.message(Command("pass"))
async def password(msg: types.Message, command: CommandObject):
    length = 12
    if command.args and command.args.isdigit():
        length = min(int(command.args), 32)

    await msg.answer(f"🔐 `{generate_password(length)}`", parse_mode="Markdown")

# ================= QR =================
@dp.message(Command("qr"))
async def make_qr(msg: types.Message, command: CommandObject):
    if not command.args:
        await msg.answer("Напиши так:\n/qr текст_или_ссылка")
        return

    try:
        img = qrcode.make(command.args.strip())
        img.save("qr.png")
        photo = types.FSInputFile("qr.png")
        await msg.answer_photo(photo, caption="✅ QR готов")
        os.remove("qr.png")
    except:
        await msg.answer("⚠️ Ошибка создания QR")

# ================= TEMPMAIL =================
@dp.message(Command("tempmail"))
async def tempmail(msg: types.Message):
    waiting_service[msg.from_user.id] = True
    await msg.answer(
        "Где регистрируешься?\n\n"
        "Напиши: tiktok / discord / steam / telegram\n"
        "или другое слово"
    )

@dp.message(lambda msg: msg.from_user.id in waiting_service)
async def choose_service(msg: types.Message):
    service = msg.text.lower().strip()
    domain = TEMP_DOMAINS.get(service, TEMP_DOMAINS["default"])
    login = generate_temp_login()

    temp_mails[msg.from_user.id] = {
        "login": login,
        "domain": domain
    }

    del waiting_service[msg.from_user.id]

    await msg.answer(
        f"📩 Временная почта:\n`{login}@{domain}`\n\nПроверка: /checkmail",
        parse_mode="Markdown"
    )

@dp.message(Command("checkmail"))
async def checkmail(msg: types.Message):
    user_id = msg.from_user.id

    if user_id not in temp_mails:
        await msg.answer("❌ Сначала создай почту: /tempmail")
        return

    login = temp_mails[user_id]["login"]
    domain = temp_mails[user_id]["domain"]

    wait = await msg.answer("⏳ Ищу письма до 60 секунд...")

    for _ in range(12):
        mails = await get_mail_messages(login, domain)

        if mails:
            text = "📬 Входящие:\n\n"
            for i, mail in enumerate(mails[:5], 1):
                sender = mail.get("from", "Unknown")
                subject = mail.get("subject", "Без темы")
                text += f"{i}. От: {sender}\nТема: {subject}\n\n"

            await wait.edit_text(text)
            return

        await asyncio.sleep(5)

    await wait.edit_text(
        "📭 Письма не пришли.\n\n"
        "💡 Возможно сервис не поддерживает эту почту.\n"
        "Попробуй новую через /tempmail"
    )

# ================= SHORT =================
@dp.message(Command("short"))
async def short_link(msg: types.Message, command: CommandObject):
    if not command.args:
        await msg.answer("Напиши так:\n/short https://example.com")
        return

    try:
        url = command.args.strip()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://tinyurl.com/api-create.php?url={url}",
                timeout=15
            ) as resp:
                shorted = await resp.text()

        if "Error" in shorted or "http" not in shorted:
            await msg.answer(
                "⚠️ Не удалось сократить ссылку.\n"
                "Проверь правильность ссылки или попробуй другую."
            )
            return

        await msg.answer(f"🔗 Короткая ссылка:\n{shorted}")

    except:
        await msg.answer(
            "⚠️ Не удалось сократить ссылку.\n"
            "Сервис временно недоступен, попробуй позже."
        )
# ================= CALC =================
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

# ================= ERROR =================
@dp.errors()
async def error_handler(event):
    logging.error(f"Ошибка: {event.exception}")
    return True

# ================= RUN =================
async def main():
    logging.info("🚀 Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
