import asyncio
import sqlite3
import random
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")   # аз Render Environment Variable
ADMINS = [8588404131]                # ID админ
# =========================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN нест! Дар Render Environment Variable гузор.")

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ================= DATABASE =================
db = sqlite3.connect("bot.db")
sql = db.cursor()

sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS channels (
    username TEXT
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS media (
    code INTEGER UNIQUE,
    file_id TEXT,
    type TEXT
)
""")

db.commit()
# ===========================================


# ================= STATES =================
class SearchCode(StatesGroup):
    code = State()

class AddChannel(StatesGroup):
    username = State()
# =========================================


# ================= KEYBOARDS =================
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Ҷустуҷӯ бо код")],
        [KeyboardButton(text="🎵 Заказ музыка"), KeyboardButton(text="🖼 Заказ акс")],
        [KeyboardButton(text="📁 Заказ файл")],
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Илова файл")],
        [KeyboardButton(text="📢 Каналҳо"), KeyboardButton(text="📊 Статистика")],
    ],
    resize_keyboard=True
)

channel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Илова канал"), KeyboardButton(text="➖ Удалит канал")],
        [KeyboardButton(text="⬅️ Бозгашт")],
    ],
    resize_keyboard=True
)
# ============================================


# ================= FUNCTIONS =================
async def check_sub(user_id: int) -> bool:
    channels = sql.execute("SELECT username FROM channels").fetchall()
    for (ch,) in channels:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status == "left":
                return False
        except:
            return False
    return True


def generate_code() -> int:
    while True:
        code = random.randint(1, 9999)
        exists = sql.execute(
            "SELECT 1 FROM media WHERE code=?",
            (code,)
        ).fetchone()
        if not exists:
            return code
# ============================================


# ================= START =================
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    sql.execute("INSERT OR IGNORE INTO users VALUES(?)", (user_id,))
    db.commit()

    if not await check_sub(user_id):
        await message.answer("❗ Аввал ба каналҳо обуна шавед")
        return

    # Агар /start CODE бошад
    if message.text and message.text.startswith("/start "):
        code = message.text.split()[1]
        media = sql.execute(
            "SELECT file_id, type FROM media WHERE code=?",
            (code,)
        ).fetchone()

        if not media:
            await message.answer("❌ Код нодуруст аст")
            return

        file_id, mtype = media

        if mtype == "audio":
            await bot.send_audio(message.chat.id, file_id)
        elif mtype == "photo":
            await bot.send_photo(message.chat.id, file_id)
        else:
            await bot.send_document(message.chat.id, file_id)
        return

    if user_id in ADMINS:
        await message.answer("👑 <b>Панели админ</b>", reply_markup=admin_kb)
    else:
        await message.answer(
            "🌟 <b>Хуш омадед!</b>\n\n"
            "Бо код файл гиред ё заказ диҳед 👇",
            reply_markup=user_kb
        )
# ==========================================


# ================= SEARCH BY CODE =================
@dp.message(F.text == "🔍 Ҷустуҷӯ бо код")
async def ask_code(message: Message, state: FSMContext):
    await message.answer("🔢 Кодро нависед:")
    await state.set_state(SearchCode.code)

@dp.message(SearchCode.code)
async def search_code(message: Message, state: FSMContext):
    code = message.text.strip()

    media = sql.execute(
        "SELECT file_id, type FROM media WHERE code=?",
        (code,)
    ).fetchone()

    if not media:
        await message.answer("❌ Ёфт нашуд")
    else:
        file_id, mtype = media
        if mtype == "audio":
            await bot.send_audio(message.chat.id, file_id)
        elif mtype == "photo":
            await bot.send_photo(message.chat.id, file_id)
        else:
            await bot.send_document(message.chat.id, file_id)

    await state.clear()
# =================================================


# ================= ADD MEDIA (ADMIN) =================
@dp.message(F.text == "➕ Илова файл")
async def add_media_prompt(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("🎵 🖼 📁 Файл фиристед")

@dp.message(F.audio | F.photo | F.document)
async def save_media(message: Message):
    if message.from_user.id not in ADMINS:
        return

    if message.audio:
        file_id = message.audio.file_id
        mtype = "audio"
    elif message.photo:
        file_id = message.photo[-1].file_id
        mtype = "photo"
    else:
        file_id = message.document.file_id
        mtype = "file"

    code = generate_code()
    sql.execute(
        "INSERT INTO media VALUES (?, ?, ?)",
        (code, file_id, mtype)
    )
    db.commit()

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={code}"

    await message.answer(
        f"✅ <b>Файл илова шуд</b>\n\n"
        f"🔢 Код: <code>{code}</code>\n"
        f"🔗 Линк:\n{link}"
    )
# ====================================================


# ================= ORDERS =================
@dp.message(
    F.text.startswith("🎵 Заказ") |
    F.text.startswith("🖼 Заказ") |
    F.text.startswith("📁 Заказ")
)
async def order(message: Message):
    for admin in ADMINS:
        await bot.send_message(
            admin,
            f"🆕 <b>ЗАКАЗ</b>\n\n"
            f"{message.text}\n"
            f"👤 @{message.from_user.username}\n"
            f"🆔 {message.from_user.id}"
        )

    await message.answer("✅ Заказ ба админ фиристода шуд")
# =========================================


# ================= CHANNELS =================
@dp.message(F.text == "📢 Каналҳо")
async def channels_menu(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("📢 Идоракунии канал", reply_markup=channel_kb)

@dp.message(F.text == "➕ Илова канал")
async def add_channel(message: Message, state: FSMContext):
    await message.answer("@username каналро нависед")
    await state.set_state(AddChannel.username)

@dp.message(AddChannel.username)
async def save_channel(message: Message, state: FSMContext):
    sql.execute("INSERT INTO channels VALUES (?)", (message.text,))
    db.commit()
    await message.answer("✅ Канал илова шуд", reply_markup=admin_kb)
    await state.clear()

@dp.message(F.text == "➖ Удалит канал")
async def delete_channels(message: Message):
    sql.execute("DELETE FROM channels")
    db.commit()
    await message.answer("🗑 Ҳама каналҳо удалит шуд", reply_markup=admin_kb)
# ===========================================


# ================= STATS =================
@dp.message(F.text == "📊 Статистика")
async def statistics(message: Message):
    if message.from_user.id not in ADMINS:
        return

    users = sql.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    media = sql.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    channels = sql.execute("SELECT COUNT(*) FROM channels").fetchone()[0]

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Корбарон: {users}\n"
        f"📦 Файлҳо: {media}\n"
        f"📢 Каналҳо: {channels}"
    )
# =========================================


# ================= RUN =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
# ======================================
