import telebot
from telebot import types
import sqlite3
import os
import time

# ========= CONFIG =========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8588404131
BOT_USERNAME = "my_file_bot"   # бе @
# ==========================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= DATABASE =========
db = sqlite3.connect("bot.db", check_same_thread=False)
sql = db.cursor()

sql.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
sql.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
sql.execute("""
CREATE TABLE IF NOT EXISTS files (
    code INTEGER PRIMARY KEY,
    file_id TEXT,
    type TEXT
)
""")
db.commit()

# ========= KEYBOARDS =========
def user_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔍 Ҷустуҷӯ бо код")
    return kb

def admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Статистика")
    kb.add("➕ Иловаи канал", "➖ Удалить канал")
    kb.add("🧹 Удалить файл")
    return kb

# ========= FUNCTIONS =========
def next_code():
    r = sql.execute("SELECT MAX(code) FROM files").fetchone()[0]
    return 1 if r is None else r + 1

def check_sub(uid):
    for (ch,) in sql.execute("SELECT username FROM channels"):
        try:
            s = bot.get_chat_member(ch, uid).status
            if s not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ========= START =========
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    args = m.text.split()

    # старт бо код
    if len(args) == 2 and args[1].isdigit():
        send_file(uid, int(args[1]))
        return

    if uid == ADMIN_ID:
        bot.send_message(
            uid,
            "👑 <b>Панели админ</b>\nФайл фирист → код мегирӣ",
            reply_markup=admin_kb()
        )
        return

    if not check_sub(uid):
        bot.send_message(uid, "❗ Аввал ба каналҳо обуна шав")
        return

    sql.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    db.commit()

    bot.send_message(
        uid,
        "🌟 <b>Хуш омадед!</b>\n\n"
        "🔍 Барои гирифтани файл кнопкаро зер кун",
        reply_markup=user_kb()
    )

# ========= USER SEARCH =========
@bot.message_handler(func=lambda m: m.text == "🔍 Ҷустуҷӯ бо код")
def ask_code(m):
    msg = bot.send_message(m.chat.id, "🔢 Лутфан коди файлро навис:")
    bot.register_next_step_handler(msg, get_code)

def get_code(m):
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ Фақат рақам навис")
        return
    send_file(m.from_user.id, int(m.text))

# ========= SEND FILE =========
def send_file(uid, code):
    f = sql.execute(
        "SELECT file_id, type FROM files WHERE code=?",
        (code,)
    ).fetchone()

    if not f:
        bot.send_message(uid, "❌ Код нодуруст аст")
        return

    file_id, t = f
    if t == "photo":
        bot.send_photo(uid, file_id)
    elif t == "audio":
        bot.send_audio(uid, file_id)
    else:
        bot.send_document(uid, file_id)

# ========= ADMIN UPLOAD =========
@bot.message_handler(content_types=["photo", "audio", "document"])
def upload(m):
    if m.from_user.id != ADMIN_ID:
        return

    if m.content_type == "photo":
        file_id = m.photo[-1].file_id
        t = "photo"
    elif m.content_type == "audio":
        file_id = m.audio.file_id
        t = "audio"
    else:
        file_id = m.document.file_id
        t = "document"

    code = next_code()
    sql.execute("INSERT INTO files VALUES (?,?,?)", (code, file_id, t))
    db.commit()

    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.send_message(
        ADMIN_ID,
        f"✅ <b>Файл сабт шуд</b>\n\n"
        f"🔢 Код: <code>{code}</code>\n"
        f"🔗 {link}"
    )

# ========= ADMIN COMMANDS =========
@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(m):
    if m.from_user.id != ADMIN_ID:
        return
    u = sql.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    f = sql.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    bot.send_message(ADMIN_ID, f"👥 Корбарон: {u}\n📁 Файлҳо: {f}")

@bot.message_handler(func=lambda m: m.text == "➕ Иловаи канал")
def add_ch(m):
    if m.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "@канал:")
    bot.register_next_step_handler(msg, save_ch)

def save_ch(m):
    sql.execute("INSERT INTO channels VALUES (?)", (m.text,))
    db.commit()
    bot.send_message(ADMIN_ID, "✅ Канал илова шуд", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "➖ Удалить канал")
def del_ch(m):
    if m.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "@канал барои удалит:")
    bot.register_next_step_handler(msg, do_del_ch)

def do_del_ch(m):
    sql.execute("DELETE FROM channels WHERE username=?", (m.text,))
    db.commit()
    bot.send_message(ADMIN_ID, "🗑 Канал удалит шуд", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "🧹 Удалить файл")
def del_file(m):
    if m.from_user.id != ADMIN_ID:
        return
    msg = bot.send_message(ADMIN_ID, "Коди файл:")
    bot.register_next_step_handler(msg, do_del_file)

def do_del_file(m):
    if not m.text.isdigit():
        bot.send_message(ADMIN_ID, "❌ Фақат рақам")
        return
    sql.execute("DELETE FROM files WHERE code=?", (int(m.text),))
    db.commit()
    bot.send_message(ADMIN_ID, "🧹 Файл удалит шуд", reply_markup=admin_kb())

# ========= RUN =========
print("Bot started")
bot.infinity_polling()
