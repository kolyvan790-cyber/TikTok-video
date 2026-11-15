import os
import asyncio
import base64
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, LabeledPrice, PreCheckoutQuery
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from openai import AsyncOpenAI

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "9260089561:AAHa7zVTRqXN6AQRJ-dN7W67bIbt2BsQZAA"
ADMIN_ID = 6664994954  # Твой ID
ADMIN_USERNAME = "BaRaShKa_Be0"  # Без @
OPENROUTER_API_KEY = "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"

STAR_TO_RUB = 1.7
PRICES = {
    "1_month": {"stars": 50, "label": "1 месяц", "days": 30},
    "6_months": {"stars": 300, "label": "6 месяцев", "days": 180},
    "1_year": {"stars": 1000, "label": "1 год", "days": 365},
}

# Клиент для OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Бесплатная модель с поддержкой зрения (картинок)
MODEL = "google/gemma-3-27b-it:free"

print("=== БОТ ЗАПУСКАЕТСЯ ===")

dp = Dispatcher()
user_limits = {}
subscriptions = {}

class ChatStates(StatesGroup):
    waiting_for_question = State()

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
        [InlineKeyboardButton(text="📥 Как решать", callback_data="how_to")],
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
        f"Я — твой ИИ-решебник. Отправь мне фото или текст задания, и я решу его по шагам.\n\n"
        f"📊 Твой статус: {sub_status}\n"
        f"Кидай задачу!"
    )
    await message.answer(text, reply_markup=get_start_keyboard(user_id))

@dp.callback_query(F.data == "how_to")
async def how_to(callback: CallbackQuery):
    await callback.message.answer("1. Сфоткай задание (или напиши текстом).\n2. Отправь мне.\n3. Подожди пару секунд — я пришлю решение.")
    await callback.answer()

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.answer("Я бот-решебник на базе ИИ. Решаю задачи по фото и тексту. Без базы ответов — только чистая логика.")
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
        f"Я — твой ИИ-решебник. Отправь мне фото или текст задания, и я решу его по шагам.\n\n"
        f"📊 Твой статус: {sub_status}\n"
        f"Кидай задачу!"
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
            f"Решения без ограничений!",
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
        "Бесплатно: 5 решений в день\n"
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
        description=f"Безлимитные решения на {price['label']}",
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
                f"Теперь ты можешь решать без ограничений! 🎉",
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
    
    now = datetime.now()
    active_subs = {uid: data for uid, data in subscriptions.items() if data["expires"] > now}
    
    if not active_subs:
        await message.answer("📭 Список подписок пуст. Ни у кого нет активной подписки.")
        return
        
    text = "📋 **Список активных подписок:**\n\n"
    sorted_subs = sorted(active_subs.items(), key=lambda item: item[1]["expires"])
    
    for i, (user_id, data) in enumerate(sorted_subs, 1):
        exp = data["expires"]
        days_left = (exp - now).days
        text += f"{i}. ID: `{user_id}` — осталось {days_left} дн. (до {exp.strftime('%d.%m.%Y')})\n"
    
    await message.answer(text, parse_mode="Markdown")

# ========== ЛОГИКА РЕШЕНИЯ ЗАДАЧ ==========
@dp.message(F.photo | F.text)
async def handle_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Пропускаем команды (начинаются с /)
    if message.text and message.text.startswith('/'):
        return

    if not add_limit(user_id):
        await message.answer(
            "⛔ **Лимит исчерпан!**\n\n"
            "Бесплатно можно решить 5 задач в день.\n"
            "Оформи подписку для безлимита!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Купить подписку", callback_data="sub_menu")]
            ]),
            parse_mode="Markdown"
        )
        return

    await message.answer("🧠 Думаю над решением, подожди...")
    
    try:
        if message.photo:
            # Скачиваем фото в память
            photo = message.photo[-1]
            file_info = await message.bot.get_file(photo.file_id)
            downloaded_file = await message.bot.download_file(file_info.file_path)
            
            # Кодируем в base64 для OpenRouter
            base64_image = base64.b64encode(downloaded_file.read()).decode('utf-8')
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Реши эту задачу по шагам. Если условие непонятно или на фото не видно текст, честно скажи об этом, не выдумывай."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        else:
            # Текстовая задача
            messages = [
                {
                    "role": "user", 
                    "content": f"Реши эту задачу по шагам. Если условие непонятно, честно скажи об этом, не выдумывай.\n\nЗадача: {message.text}"
                }
            ]

        response = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1500,
        )
        
        answer = response.choices[0].message.content
        await message.answer(answer)

    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        await message.answer("❌ Не смог обработать задачу. Попробуй ещё раз или напиши текстом.")

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
