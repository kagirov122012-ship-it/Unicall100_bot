import asyncio
import re
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from yt_dlp import YoutubeDL

TOKEN = "8923460729:AAFsYNOSDRVCMH-t5_6HKCn-Y1EV9PBs44Q"

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def get_tiktok_video(url):
    """Получает прямую ссылку на видео TikTok через tikmate"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://tikmate.online/api/get?url={url}") as resp:
                data = await resp.json()
                return data.get("video_url")
        except:
            return None

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("📥 Отправь ссылку на YouTube или TikTok\nYouTube — работает всегда\nTikTok — может не сработать, пробуй")

@dp.message(lambda msg: 'tiktok.com' in msg.text)
async def handle_tiktok(msg: types.Message):
    url = msg.text.strip()
    await msg.answer("⏳ Загружаю TikTok...")
    video_url = await get_tiktok_video(url)
    if video_url:
        await msg.answer_video(video_url, caption="🎬 TikTok")
    else:
        await msg.answer("❌ TikTok не загрузился. Попробуй позже или скачай вручную через tikmate.online")

@dp.message(lambda msg: 'youtube.com' in msg.text or 'youtu.be' in msg.text)
async def handle_youtube(msg: types.Message):
    url = msg.text.strip()
    await msg.answer("⏳ Загружаю YouTube...")

    ydl_opts = {
        'format': 'best[height<=720]',
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url')
            title = info.get('title', 'Видео')[:100]
            await msg.answer_video(video_url, caption=f"🎬 {title}")
    except Exception as e:
        await msg.answer(f"⚠️ Ошибка: {str(e)[:100]}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
