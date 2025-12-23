import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

BOT_TOKEN = "TOKEN_BOT"
ADMINS = [8588404131]

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ===== DATABASE =====
db = sqlite3.connect("bot.db")
sql = db.cursor()

sql.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)""")
sql.execute("""CREATE TABLE IF NOT EXISTS channels(username TEXT)""")
sql.execute("""CREATE TABLE IF NOT EXISTS media(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    type TEXT
)""")
db.commit()

# ===== STATES =====
class AddChannel(StatesGroup):
    username = State()

class DeleteMedia(StatesGroup):
    media_id = State()

# ===== KEYBOARDS =====
user_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎬 Филмҳо")],
        [KeyboardButton(text="🎵 Мусиқӣ"), KeyboardButton(text="🖼 Аксҳо")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="➕ Илова файл"), KeyboardButton(text="➖ Удалит файл")],
        [KeyboardButton(text="📢 Каналҳо")]
    ],
    resize_keyboard=True
)

def channel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Илова канал"), KeyboardButton(text="➖ Удалит канал")],
            [KeyboardButton(text="⬅️ Бозгашт")]
        ],
        resize_keyboard=True
    )

# ===== CHECK SUB =====
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

# ===== START =====
@dp.message(CommandStart())
async def start(message: Message):
    uid = message.from_user.id
    sql.execute("INSERT OR IGNORE INTO users VALUES(?)", (uid,))
    db.commit()

    if not await check_sub(uid):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Канал", url="https://t.me/example")],
            [InlineKeyboardButton(text="✅ Санҷиш", callback_data="check")]
        ])
        await message.answer("❗ Аввал обуна шавед", reply_markup=kb)
        return

    if message.text.startswith("/start ") and message.text.split()[1].isdigit():
        mid = message.text.split()[1]
        media = sql.execute("SELECT file_id,type FROM media WHERE id=?", (mid,)).fetchone()
        if not media:
            await message.answer("❌ Мавҷуд нест ё удалит шудааст")
            return
        if media[1] == "video":
            await bot.send_video(uid, media[0])
        elif media[1] == "audio":
            await bot.send_audio(uid, media[0])
        else:
            await bot.send_photo(uid, media[0])
        return

    if uid in ADMINS:
        await message.answer("👑 Панели админ", reply_markup=admin_kb)
    else:
        await message.answer("Хуш омадед 👋", reply_markup=user_kb)

# ===== CALLBACK =====
@dp.callback_query(F.data == "check")
async def recheck(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await start(call.message)
    else:
        await call.answer("❌ Ҳанӯз обуна нестед", show_alert=True)

# ===== ADD MEDIA =====
@dp.message(F.text == "➕ Илова файл")
async def ask_media(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("🎬🎵🖼 Файл фиристед")

@dp.message(F.video | F.audio | F.photo)
async def save_media(message: Message):
    if message.from_user.id not in ADMINS:
        return

    if message.video:
        fid, tp = message.video.file_id, "video"
    elif message.audio:
        fid, tp = message.audio.file_id, "audio"
    else:
        fid, tp = message.photo[-1].file_id, "photo"

    sql.execute("INSERT INTO media(file_id,type) VALUES(?,?)", (fid, tp))
    db.commit()
    mid = sql.execute("SELECT last_insert_rowid()").fetchone()[0]
    link = f"https://t.me/{(await bot.get_me()).username}?start={mid}"
    await message.answer(f"✅ Илова шуд\n🔗 Линк:\n{link}")

# ===== DELETE MEDIA =====
@dp.message(F.text == "➖ Удалит файл")
async def del_media(message: Message, state: FSMContext):
    if message.from_user.id in ADMINS:
        await message.answer("ID нависед:")
        await state.set_state(DeleteMedia.media_id)

@dp.message(DeleteMedia.media_id)
async def confirm_del(message: Message, state: FSMContext):
    mid = message.text
    sql.execute("DELETE FROM media WHERE id=?", (mid,))
    db.commit()
    await message.answer("🗑 Удалит шуд")
    await state.clear()

# ===== CHANNEL MANAGE =====
@dp.message(F.text == "📢 Каналҳо")
async def ch_menu(message: Message):
    if message.from_user.id in ADMINS:
        await message.answer("📢 Идоракунии канал", reply_markup=channel_kb())

@dp.message(F.text == "➕ Илова канал")
async def add_ch(message: Message, state: FSMContext):
    await message.answer("@username каналро нависед")
    await state.set_state(AddChannel.username)

@dp.message(AddChannel.username)
async def save_ch(message: Message, state: FSMContext):
    sql.execute("INSERT INTO channels VALUES(?)", (message.text,))
    db.commit()
    await message.answer("✅ Канал илова шуд", reply_markup=admin_kb)
    await state.clear()

@dp.message(F.text == "➖ Удалит канал")
async def del_ch(message: Message):
    chs = sql.execute("SELECT username FROM channels").fetchall()
    if not chs:
        await message.answer("❌ Канал нест")
        return
    for ch in chs:
        sql.execute("DELETE FROM channels WHERE username=?", (ch[0],))
    db.commit()
    await message.answer("🗑 Ҳама каналҳо удалит шуд")

# ===== STATS =====
@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):
    if message.from_user.id not in ADMINS:
        return
    u = sql.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    m = sql.execute("SELECT COUNT(*) FROM media").fetchone()[0]
    c = sql.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    await message.answer(
        f"📊 Статистика\n\n"
        f"👥 Корбарон: {u}\n"
        f"📦 Файлҳо: {m}\n"
        f"📢 Каналҳо: {c}"
    )

# ===== RUN =====
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
