import os
import asyncio
import tempfile
import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command

# ТОКЕН ВСТАВЬ СЮДА
BOT_TOKEN = "9260089561:AAHa7zVTRqXN6AQRJ-dN7W67bIbt2BsQZAA"

print("=== БОТ ЗАПУСКАЕТСЯ ===")

dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: Message):
    print(f"Получен /start от {message.from_user.id}")
    await message.answer("Кидай ссылку на видео из TikTok, и я скачаю его без водяного знака.")

@dp.message(F.text)
async def download_tiktok(message: Message):
    url = message.text.strip()
    print(f"Получена ссылка: {url}")
    
    if "tiktok.com" not in url:
        await message.answer("Это не похоже на ссылку из TikTok. Попробуй ещё раз.")
        return

    await message.answer("⏳ Качаю видео, подожди...")

    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        print("Начинаю скачивание...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
        
        print(f"Скачано: {video_path}")

        video_file = FSInputFile(video_path)
        await message.answer_video(video=video_file, caption="Готово! 🎬")
        print("Видео отправлено!")

        os.remove(video_path)
        os.rmdir(temp_dir)

    except Exception as e:
        print(f"Ошибка: {e}")
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except:
            pass

async def main():
    bot = Bot(token=BOT_TOKEN)
    print("Бот подключен, начинаю polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
