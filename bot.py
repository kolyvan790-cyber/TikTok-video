import os
import asyncio
import tempfile
import yt_dlp
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "9260089561:AAHa7zVTRqXN6AQRJ-dN7W67bIbt2BsQZAA"
ADMIN_ID = 6664994954  # Твой числовой ID из @userinfobot
ADMIN_USERNAME = "BaRaShKa_Be0"  # Без @
STAR_TO_RUB = 1.7  # Примерный курс 1 звезды в рублях

# Цены подписок в звёздах
PRICES = {
    "1_month": {"stars": 50, "label": "1 месяц", "days": 30},
    "6_months": {"stars": 300, "label": "6 месяцев", "days": 180},
    "1_year": {"stars": 1000, "label": "1 год", "days": 365},
}

print("=== БОТ ЗАПУСКАЕТСЯ ===")

dp = Dispatcher()
user_limits = {}
subscriptions = {}

class DownloadStates(StatesGroup):
    waiting_for_choice = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def is_admin(user_id):
    return user_id == ADMIN_ID

def has_active_sub(user_id):
    if user_id not in subscriptions:
        return False
    return subscriptions[user_id]["expires"] > datetime.now()

def get_sub_days_left(user_id):
    if not has_active_sub(user_id):
        return 0
    delta = subscriptions[user_id]["expires"] - datetime.now()
    return max(0, delta.days)

def get_limit(user_id):
    if has_active_sub(user_id) or is_admin(user_id):
        return 999999
    today = datetime.now().date()
    if user_id not in user_limits or user_limits[user_id]["date"] != today:
        user_limits[user_id] = {"date": today, "count": 0}
    return user_limits[user_id]["count"]

def add_limit(user_id):
    if has_active_sub(user_id) or is_admin(user_id):
        return True
    today = datetime.now().date()
    if user_id not in user_limits or user_limits[user_id]["date"] != today:
        user_limits[user_id] = {"date": today, "count": 0}
    if user_limits[user_id]["count"] >= 5:
        return False
    user_limits[user_id]["count"] += 1
    return True

def get_start_keyboard(user_id):
    if has_active_sub(user_id):
        days_left = get_sub_days_left(user_id)
        sub_text = f"💎 Подписка (осталось {days_left} дн.)"
    else:
        sub_text = "💎 Купить подписку"
        
    kb = [
        [InlineKeyboardButton(text="📥 Как скачать", callback_data="how_to")],
        [InlineKeyboardButton(text=sub_text, callback_data="sub_menu")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    if is_admin(user_id):
        sub_status = "👑 Админ (безлимит)"
    elif has_active_sub(user_id):
        sub_status = f"✅ Подписка активна (осталось {get_sub_days_left(user_id)} дн.)"
    else:
        sub_status = f"❌ Нет (лимит {5 - get_limit(user_id)} из 5)"
    
    text = (
        f"Привет! 👋\n\n"
        f"Я скачиваю видео из TikTok, Instagram и YouTube Shorts.\n\n"
        f"📊 Твой статус: {sub_status}\n"
        f"Отправь ссылку на видео!"
    )
    await message.answer(text, reply_markup=get_start_keyboard(user_id))

@dp.callback_query(F.data == "how_to")
async def how_to(callback: CallbackQuery):
    await callback.message.answer("1. Скопируй ссылку на видео.\n2. Отправь её мне.\n3. Выбери: видео или музыка.")
    await callback.answer()

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.answer("Бот-загрузчик. Работает на yt-dlp. Без водяных знаков.")
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    if is_admin(user_id):
        sub_status = "👑 Админ (безлимит)"
    elif has_active_sub(user_id):
        sub_status = f"✅ Подписка активна (осталось {get_sub_days_left(user_id)} дн.)"
    else:
        sub_status = "❌ Нет"
        
    text = (
        f"Привет! 👋\n\n"
        f"Я скачиваю видео из TikTok, Instagram и YouTube Shorts.\n\n"
        f"📊 Твой статус: {sub_status}\n"
        f"Отправь ссылку на видео!"
    )
    await callback.message.edit_text(text, reply_markup=get_start_keyboard(user_id))
    await callback.answer()

# ========== МЕНЮ ПОДПИСКИ ==========
@dp.callback_query(F.data == "sub_menu")
async def sub_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    if has_active_sub(user_id):
        exp = subscriptions[user_id]["expires"].strftime("%d.%m.%Y %H:%M")
        days_left = get_sub_days_left(user_id)
        await callback.message.edit_text(
            f"✅ У тебя активна подписка до {exp}.\n"
            f"Осталось дней: {days_left}\n\n"
            f"Скачивания без ограничений!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
            ])
        )
        await callback.answer()
        return

    kb = []
    for key, data in PRICES.items():
        rub = int(data["stars"] * STAR_TO_RUB)
        kb.append([InlineKeyboardButton(
            text=f"⭐ {data['label']} — {data['stars']} звёзд (~{rub} ₽)",
            callback_data=f"buy_stars_{key}"
        )])
    kb.append([InlineKeyboardButton(text="💳 Оплатить картой", callback_data="pay_card")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")])
    
    text = (
        "💎 **Выбери подписку:**\n\n"
        "Бесплатно: 5 скачиваний в день\n"
        "С подпиской: безлимит\n\n"
        "Оплата звёздами — автоматически.\n"
        "Оплата картой — напиши админу."
    )
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    await callback.answer()

# ========== ОПЛАТА КАРТОЙ ==========
@dp.callback_query(F.data == "pay_card")
async def pay_card(callback: CallbackQuery):
    text = (
        "💳 **Оплата картой**\n\n"
        f"Мой юзернейм: `@{ADMIN_USERNAME}`\n\n"
        f"Скажи, какую подписку хочешь, и я скину реквизиты.\n\n"
        f"Цены:\n"
        f"1 месяц — {int(PRICES['1_month']['stars'] * STAR_TO_RUB)} ₽\n"
        f"6 месяцев — {int(PRICES['6_months']['stars'] * STAR_TO_RUB)} ₽\n"
        f"1 год — {int(PRICES['1_year']['stars'] * STAR_TO_RUB)} ₽"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Скопировать юзернейм", copy_text={"text": f"@{ADMIN_USERNAME}"})],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="sub_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ========== ОПЛАТА ЗВЁЗДАМИ ==========
@dp.callback_query(F.data.startswith("buy_stars_"))
async def buy_stars(callback: CallbackQuery):
    key = callback.data.replace("buy_stars_", "")
    if key not in PRICES:
        await callback.answer("Ошибка", show_alert=True)
        return
    
    price = PRICES[key]
    await callback.message.answer_invoice(
        title=f"Подписка: {price['label']}",
        description=f"Безлимитные скачивания на {price['label']}",
        payload=f"sub_{key}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=price['label'], amount=price['stars'])],
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    
    if payload.startswith("sub_"):
        key = payload.replace("sub_", "")
        if key in PRICES:
            days = PRICES[key]["days"]
            expires = datetime.now() + timedelta(days=days)
            subscriptions[user_id] = {"expires": expires}
            
            await message.answer(
                f"✅ **Оплата прошла!**\n\n"
                f"Подписка активирована до {expires.strftime('%d.%m.%Y')}.\n"
                f"Теперь ты можешь скачивать без ограничений! 🎉",
                parse_mode="Markdown"
            )

# ========== АДМИН-КОМАНДЫ ==========
@dp.message(Command("give"))
async def admin_give(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Использование: /give <user_id> <дни>")
        return
    try:
        target_id = int(args[1])
        days = int(args[2])
    except ValueError:
        await message.answer("ID и дни должны быть числами.")
        return
    expires = datetime.now() + timedelta(days=days)
    subscriptions[target_id] = {"expires": expires}
    await message.answer(f"✅ Выдал подписку пользователю {target_id} на {days} дней (до {expires.strftime('%d.%m.%Y')}).")

@dp.message(Command("take"))
async def admin_take(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Использование: /take <user_id>")
        return
    try:
        target_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    if target_id in subscriptions:
        del subscriptions[target_id]
        await message.answer(f"✅ Забрал подписку у пользователя {target_id}.")
    else:
        await message.answer(f"У пользователя {target_id} нет подписки.")

@dp.message(Command("subs"))
async def admin_subs(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    if not subscriptions:
        await message.answer("📭 Список подписок пуст. Ни у кого нет активной подписки.")
        return
    
    text = "📋 **Список активных подписок:**\n\n"
    now = datetime.now()
    
    # Фильтруем только активные и сортируем по дате окончания
    active_subs = {uid: data for uid, data in subscriptions.items() if data["expires"] > now}
    
    if not active_subs:
        await message.answer("📭 Список подписок пуст. Ни у кого нет активной подписки.")
        return
        
    sorted_subs = sorted(active_subs.items(), key=lambda item: item[1]["expires"])
    
    for i, (user_id, data) in enumerate(sorted_subs, 1):
        exp = data["expires"]
        days_left = (exp - now).days
        text += f"{i}. ID: `{user_id}` — осталось {days_left} дн. (до {exp.strftime('%d.%m.%Y')})\n"
    
    await message.answer(text, parse_mode="Markdown")

# ========== СКАЧИВАНИЕ ==========
@dp.message(F.text)
async def receive_link(message: Message, state: FSMContext):
    url = message.text.strip()
    if not any(x in url for x in ["tiktok.com", "instagram.com", "youtube.com/shorts"]):
        await message.answer("Это не похоже на ссылку из TikTok, Instagram или YouTube Shorts.")
        return

    if not add_limit(message.from_user.id):
        await message.answer(
            "⛔ **Лимит исчерпан!**\n\n"
            "Бесплатно можно скачать 5 видео в день.\n"
            "Оформи подписку для безлимита!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить подписку", callback_data="sub_menu")]
            ]),
            parse_mode="Markdown"
        )
        return

    await state.update_data(url=url)
    await state.set_state(DownloadStates.waiting_for_choice)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Видео", callback_data="dl_video")],
        [InlineKeyboardButton(text="🎵 Музыка (MP3)", callback_data="dl_audio")]
    ])
    await message.answer("Что скачать?", reply_markup=kb)

@dp.callback_query(F.data == "dl_video", DownloadStates.waiting_for_choice)
async def dl_video(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url = data.get("url")
    await state.clear()
    await callback.message.edit_text("⏳ Качаю видео...")
    await process_download(callback.message, url, is_audio=False)

@dp.callback_query(F.data == "dl_audio", DownloadStates.waiting_for_choice)
async def dl_audio(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    url = data.get("url")
    await state.clear()
    await callback.message.edit_text("⏳ Извлекаю музыку...")
    await process_download(callback.message, url, is_audio=True)

async def process_download(message: Message, url: str, is_audio: bool):
    temp_dir = tempfile.mkdtemp()
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")

    ydl_opts = {'outtmpl': output_template, 'quiet': True, 'no_warnings': True}

    if is_audio:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        ydl_opts.update({'format': 'best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if is_audio:
                filename = os.path.splitext(filename)[0] + ".mp3"

        file_to_send = FSInputFile(filename)
        if is_audio:
            await message.answer_audio(audio=file_to_send, caption="🎵 Готово!")
        else:
            await message.answer_video(video=file_to_send, caption="🎬 Готово!")

        os.remove(filename)
        os.rmdir(temp_dir)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)[:200]}")
        try:
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)
        except:
            pass

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
