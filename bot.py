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
ADMIN_USERNAME = "BaRaShKa_Be0"
OPENROUTER_API_KEY = "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"

# Выбери рабочую модель из списка:
# "nvidia/nemotron-nano-12b-v2-vl:free"
# "google/gemma-3-27b-it:free"
# "qwen/qwen-2.5-vl-7b-instruct:free"
MODEL = "qwen/qwen-2.5-vl-7b-instruct:free"

STAR_TO_RUB = 1.7
PRICES = {
    "1_month": {"stars": 50, "label": "1 месяц", "days": 30},
    "6_months": {"stars": 300, "label": "6 месяцев", "days": 180},
    "1_year": {"stars": 1000, "label": "1 год", "days": 365},
}

client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

print("=== БОТ ЗАПУСКАЕТСЯ ===")
dp = Dispatcher()
user_limits = {}
subscriptions = {}

class ChatStates(StatesGroup):
    waiting_for_question = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ==========
def is_admin(user_id): return user_id == ADMIN_ID
def has_active_sub(user_id):
    return user_id in subscriptions and subscriptions[user_id]["expires"] > datetime.now()
def get_sub_days_left(user_id):
    if not has_active_sub(user_id): return 0
    return max(0, (subscriptions[user_id]["expires"] - datetime.now()).days)

def get_limit(user_id):
    if has_active_sub(user_id) or is_admin(user_id): return 999999
    today = datetime.now().date()
    if user_id not in user_limits or user_limits[user_id]["date"] != today:
        user_limits[user_id] = {"date": today, "count": 0}
    return user_limits[user_id]["count"]

def add_limit(user_id):
    if has_active_sub(user_id) or is_admin(user_id): return True
    today = datetime.now().date()
    if user_id not in user_limits or user_limits[user_id]["date"] != today:
        user_limits[user_id] = {"date": today, "count": 0}
    if user_limits[user_id]["count"] >= 5: return False
    user_limits[user_id]["count"] += 1
    return True

def get_main_menu(user_id):
    if has_active_sub(user_id):
        sub_text = f"💎 Подписка (осталось {get_sub_days_left(user_id)} дн.)"
    else:
        sub_text = "💎 Купить подписку"
    kb = [
        [InlineKeyboardButton(text="🧠 Решить задачу", callback_data="solve_mode")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_menu")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text=sub_text, callback_data="sub_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if is_admin(user_id): status = "👑 Админ (безлимит)"
    elif has_active_sub(user_id): status = f"✅ Подписка (осталось {get_sub_days_left(user_id)} дн.)"
    else: status = f"🆓 Бесплатно (лимит {5 - get_limit(user_id)} из 5)"
    
    text = (
        f"✨ **Привет, {message.from_user.first_name}!**\n\n"
        f"Я — твой умный помощник по учёбе. Пришли мне фото задания или напиши текст, и я решу его по шагам.\n\n"
        f"📊 **Твой статус:** {status}\n"
        f"👇 Выбери действие:"
    )
    await message.answer(text, reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("📖 **Как пользоваться:**\n\n1. Нажми «🧠 Решить задачу»\n2. Отправь фото задания или напиши текст\n3. Получи пошаговое решение\n\n⚠️ **Важно:** я не волшебник. Если фото размытое или задача непонятная, я честно скажу, что не могу решить, а не буду выдумывать.", parse_mode="Markdown")

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    if not is_admin(message.from_user.id): return
    total_subs = len([s for s in subscriptions.values() if s["expires"] > datetime.now()])
    await message.answer(f"📊 **Статистика:**\nАктивных подписок: {total_subs}\nВсего в памяти: {len(subscriptions)}", parse_mode="Markdown")

# ========== КНОПКИ МЕНЮ ==========
@dp.callback_query(F.data == "help_menu")
async def cb_help(callback: CallbackQuery):
    await callback.message.answer("📖 **Как пользоваться:**\n\n1. Нажми «🧠 Решить задачу»\n2. Отправь фото задания или напиши текст\n3. Получи пошаговое решение\n\n⚠️ Я не выдумываю ответы. Если не смогу — скажу об этом.", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "about_bot")
async def cb_about(callback: CallbackQuery):
    await callback.message.answer("🤖 **О боте**\n\nЯ — честный ИИ-решебник. Работаю на базе нейросетей. Не ищу ответы в базе (как некоторые), а решаю задачи с нуля.\n\nМоя фишка: если я не уверен — я признаюсь, а не вру.", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "solve_mode")
async def cb_solve_mode(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ChatStates.waiting_for_question)
    await callback.message.answer("📸 **Жду задачу!**\n\nОтправь фото или напиши текст задания. Я решу его по шагам.", parse_mode="Markdown")
    await callback.answer()

# ========== ПОДПИСКА (без изменений) ==========
@dp.callback_query(F.data == "sub_menu")
async def sub_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    if has_active_sub(user_id):
        exp = subscriptions[user_id]["expires"].strftime("%d.%m.%Y %H:%M")
        await callback.message.edit_text(f"✅ Подписка до {exp}.\nОсталось дней: {get_sub_days_left(user_id)}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]]))
        await callback.answer(); return
    kb = [[InlineKeyboardButton(text=f"⭐ {d['label']} — {d['stars']} звёзд (~{int(d['stars']*STAR_TO_RUB)} ₽)", callback_data=f"buy_stars_{k}")] for k, d in PRICES.items()]
    kb.append([InlineKeyboardButton(text="💳 Оплатить картой", callback_data="pay_card")])
    kb.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")])
    await callback.message.edit_text("💎 **Выбери подписку:**\n\nБесплатно: 5 решений в день\nС подпиской: безлимит", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "pay_card")
async def pay_card(callback: CallbackQuery):
    await callback.message.edit_text(f"💳 **Оплата картой**\n\nМой юзернейм: `@{ADMIN_USERNAME}`\n\nНапиши мне, и я скину реквизиты.\n\nЦены:\n1 месяц — {int(PRICES['1_month']['stars']*STAR_TO_RUB)} ₽\n6 месяцев — {int(PRICES['6_months']['stars']*STAR_TO_RUB)} ₽\n1 год — {int(PRICES['1_year']['stars']*STAR_TO_RUB)} ₽", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📋 Скопировать юзернейм", copy_text={"text": f"@{ADMIN_USERNAME}"})],[InlineKeyboardButton(text="🔙 Назад", callback_data="sub_menu")]]), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    if is_admin(user_id): status = "👑 Админ"
    elif has_active_sub(user_id): status = f"✅ Подписка (осталось {get_sub_days_left(user_id)} дн.)"
    else: status = "🆓 Бесплатно"
    await callback.message.edit_text(f"✨ **Главное меню**\n\n📊 Статус: {status}\n👇 Выбери действие:", reply_markup=get_main_menu(user_id), parse_mode="Markdown")
    await callback.answer()

# ========== ОПЛАТА ЗВЁЗДАМИ ==========
@dp.callback_query(F.data.startswith("buy_stars_"))
async def buy_stars(callback: CallbackQuery):
    key = callback.data.replace("buy_stars_", "")
    if key not in PRICES: return
    p = PRICES[key]
    await callback.message.answer_invoice(title=f"Подписка: {p['label']}", description=f"Безлимитные решения на {p['label']}", payload=f"sub_{key}", provider_token="", currency="XTR", prices=[LabeledPrice(label=p['label'], amount=p['stars'])])
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery): await query.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    if payload.startswith("sub_"):
        key = payload.replace("sub_", "")
        if key in PRICES:
            expires = datetime.now() + timedelta(days=PRICES[key]["days"])
            subscriptions[message.from_user.id] = {"expires": expires}
            await message.answer(f"✅ **Оплата прошла!**\nПодписка до {expires.strftime('%d.%m.%Y')}.", parse_mode="Markdown")

# ========== АДМИНКА ==========
@dp.message(Command("give"))
async def admin_give(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) != 3: return
    try:
        target_id, days = int(args[1]), int(args[2])
        subscriptions[target_id] = {"expires": datetime.now() + timedelta(days=days)}
        await message.answer(f"✅ Выдал {target_id} на {days} дней.")
    except: await message.answer("Ошибка. Формат: /give ID ДНИ")

@dp.message(Command("take"))
async def admin_take(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split()
    if len(args) != 2: return
    try:
        target_id = int(args[1])
        if target_id in subscriptions: del subscriptions[target_id]; await message.answer(f"✅ Забрал у {target_id}.")
        else: await message.answer("Нет подписки.")
    except: await message.answer("Ошибка. Формат: /take ID")

@dp.message(Command("subs"))
async def admin_subs(message: Message):
    if not is_admin(message.from_user.id): return
    now = datetime.now()
    active = {uid: d for uid, d in subscriptions.items() if d["expires"] > now}
    if not active: await message.answer("📭 Список пуст."); return
    text = "📋 **Активные подписки:**\n\n"
    for uid, d in sorted(active.items(), key=lambda x: x[1]["expires"]):
        text += f"`{uid}` — {(d['expires'] - now).days} дн. (до {d['expires'].strftime('%d.%m')})\n"
    await message.answer(text, parse_mode="Markdown")

# ========== РЕШЕНИЕ ЗАДАЧ (ИИ) ==========
@dp.message(F.photo | F.text, ChatStates.waiting_for_question)
async def handle_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if not add_limit(user_id):
        await message.answer("⛔ **Лимит исчерпан!**\n\nБесплатно: 5 решений в день.\nОформи подписку для безлимита!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Купить подписку", callback_data="sub_menu")]]), parse_mode="Markdown")
        return

    await message.answer("🧠 Думаю над решением...")
    try:
        if message.photo:
            photo = message.photo[-1]
            file = await message.bot.download_file((await message.bot.get_file(photo.file_id)).file_path)
            b64 = base64.b64encode(file.read()).decode('utf-8')
            messages = [{"role": "user", "content": [{"type": "text", "text": "Реши эту задачу по шагам. Если условие непонятно или на фото не видно текст, честно скажи об этом, не выдумывай."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]
        else:
            messages = [{"role": "user", "content": f"Реши эту задачу по шагам. Если условие непонятно, честно скажи об этом, не выдумывай.\n\nЗадача: {message.text}"}]
        
        response = await client.chat.completions.create(model=MODEL, messages=messages, max_tokens=1500)
        await message.answer(response.choices[0].message.content)
    except Exception as e:
        print(f"Ошибка ИИ: {e}")
        await message.answer("❌ Не смог обработать задачу. Попробуй ещё раз или напиши текстом.")
    finally:
        await state.clear()

# ========== ЗАПУСК ==========
async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
