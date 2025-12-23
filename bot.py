import asyncio
import sqlite3
import random
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Render Environment Variable
ADMINS = [8588404131]               # ID админ
# ==========================

bot = Bot(BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ========= DATABASE =========
db = sqlite3.connect("bot.db")
sql = db.cursor()

sql.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)""")
sql.execute("""CREATE TABLE IF NOT EXISTS channels(username TEXT)""")
sql.execute("""CREATE TABLE IF NOT EXISTS media(
    code INTEGER UNIQUE,
    file_id TEXT,
    type TEXT
)""")
db.commit()

# ========= STATES =========
class SearchCode(StatesGroup):
    code = State()

class AddChannel(StatesGroup):
    username = State()

# ========= KEYBOARDS =========
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Ҷустуҷӯ бо код")],
        [KeyboardButton(text="🎵 Заказ музыка"), KeyboardButton(text="🖼 Заказ акс")],
        [KeyboardButton(text="📁 Заказ файл")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Илова файл")],
        [KeyboardButton(text="📢 Каналҳо"), KeyboardButton(text="📊 Статистика")]
    ],
    resize_keyboard=True
)

channel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Илова канал"), KeyboardButton(text="➖ Удалит канал")],
        [KeyboardButton(text="⬅️ Бозгашт")]
    ],
    resize_keyboard=True
)

# ========= FUNCTIONS =========
async def check_sub(user_id):
    channels = sql.execute("SELECT username FROM channels").fetchall()
    for ch in channels:
        try:
            m = await bot.get_chat_member(ch[0], user_id)
            if m.status == "left":
                return False
        except:
            return False
    return True

def generate_code():
    while True:
        code = random.randint(1, 9999)
        if not sql.execute("SELECT 1 FROM media WHERE code=?", (code,)).fetchone():
            return code

# ========= START =========
@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    sql.execute("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
    db.commit()

    if not await check_sub(uid):
        await message.answer("❗ Аввал ба каналҳо обуна шавед")
        return

    # START WITH CODE
    if message.text.startswith("/start "):
        code = message.text.split()[1]
        media = sql.execute(
            "SELECT file_id,type FROM media WHERE code=?",
            (code,)
        ).fetchone()

        if not media:
            await message.answer("❌ Код нодуруст аст")
            return

        if media[1] == "audio":
            await bot.send_audio(uid, media[0])
        elif media[1] == "photo":
            await bot.send_photo(uid, media[0])
        else:
            await bot.send_document(uid, media[0])
        return

    if uid in ADMINS:
        await message.answer("👑 <b>Панели админ</b>", reply_markup=admin_kb)
    else:
        await message.answer(
            "🌟 <b>Хуш омадед!</b>\n\n"
            "Бо код файл гиред ё заказ диҳед 👇",
            reply_markup=user_kb
        )

# ========= SEARCH BY CODE =========
@dp.message(F.text == "🔍 Ҷустуҷӯ бо код")
async def ask_code(message: Message, state: FSMContext):
    await message.answer("🔢 Кодро нависед:")
    await state.set_state(SearchCode.code)

@dp.message(SearchCode.code)
async def get_code(message: Message, state: FSMContext):
    code = message.text
    media = sql.execute(
        "SELECT file_id,type FROM media WHERE code=?",
        (code,)
    ).fetchone()

    if not media:
        await message.answer("❌ Ёфт нашуд")
    else:
        if media[1] == "audio":
            await bot.send_audio(message.chat.id, media[0])
        elif media[1] == "photo":
            await bot.send_photo(message.chat.id, media[0])
        else:
            await bot.send_document(message.chat.id, media[0])

    await state.clear()

# ========= ADD MEDIA (ADMIN) =========
@dp.message(F.text == "➕ Илова файл")
async def ask_media(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("🎵🖼📁 Файл фиристед")

@dp.message(F.audio | F.photo | F.document)
async def save_media(message: Message):
    if message.from_user.id not in ADMINS:
        return

    if message.audio:
        fid, tp = message.audio.file_id, "audio"
    elif message.photo:
        fid, tp = message.photo[-1].file_id, "photo"
    else:
        fid, tp = message.document.file_id, "file"

    code = generate_code()
    sql.execute("INSERT INTO media VALUES(?,?,?)", (code, fid, tp))
    db.commit()

    bot_user = await bot.get_me()
    link = f"https://t.me/{bot_user.username}?start={code}"

    await message.answer(
        f"✅ <b>Илова шуд</b>\n\n"
        f"🔢 Код: <code>{code}</code>\n"
        f"🔗 Линк:\n{link}"
    )

# ========= ORDERS =========
@dp.message(F.text.startswith("🎵 Заказ") | F.text.startswith("🖼 Заказ") | F.text.startswith("📁 Заказ"))
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

# ========= CHANNELS =========
@dp.message(F.text == "📢 Каналҳо")
async def ch_menu(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("📢 Каналҳо", reply_markup=channel_kb)

@dp.message(F.text == "➕ Илова канал")
async def add_ch(message: Message, state: FSMContext):
    await message.answer("@канал нависед")
    await state.set_state(AddChannel.username)

@dp.message(AddChannel.username)
async def save_ch(message: Message, state: FSMContext):
    sql.execute("INSERT INTO channels VALUES(?)", (message.text,))
    db.commit()
    await message.answer("✅ Канал илова шуд", reply_markup=admin_kb)
    await state.clear()

@dp.message(F.text == "➖ Удалит канал")
async def del_ch(message: Message):
    sql.execute("DELETE FROM channels")
    db.commit()
    await message.answer("🗑 Ҳама каналҳо удалит шуд", reply_markup=admin_kb)

# ========= STATS =========
@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):
    if message.from_user.id not in ADMINS:
        return
    u = sql.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m = sql.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    c = sql.execute("SELECT COUNT(*) FROM channels").fetchone()[0]

    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Корбарон: {u}\n"
        f"📦 Файлҳо: {m}\n"
        f"📢 Каналҳо: {c}"
    )

# ========= RUN =========
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
