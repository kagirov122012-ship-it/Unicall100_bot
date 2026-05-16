import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

TOKEN = "8923460729:AAFsYNOSDRVCMH-t5_6HKCn-Y1EV9PBs44Q"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Привет! Бот работает через Termux")

@dp.message(Command("help"))
async def help(msg: types.Message):
    await msg.answer("Команды: /start, /help")

@dp.message()
async def echo(msg: types.Message):
    await msg.answer(f"Ты написал: {msg.text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
