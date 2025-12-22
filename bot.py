import telebot
from telebot import types
import sqlite3
import time
import os

# ============ CONFIG ============
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8588404131   # <-- ID админ
# ================================

if not TOKEN:
    raise ValueError("BOT_TOKEN not set")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ============ DATABASE ============
db = sqlite3.connect("bot.db", check_same_thread=False)
sql = db.cursor()

sql.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
sql.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
sql.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    file_id TEXT
)
""")
sql.execute("""
CREATE TABLE IF NOT EXISTS ads (
    text TEXT,
    end_time INTEGER
)
""")
db.commit()

# ============ FUNCTIONS ============
def check_sub(user_id):
    for (ch,) in sql.execute("SELECT username FROM channels"):
        try:
            s = bot.get_chat_member(ch, user_id).status
            if s not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def sub_keyboard():
    kb = types.InlineKeyboardMarkup()
    for (ch,) in sql.execute("SELECT username FROM channels"):
        kb.add(types.InlineKeyboardButton(f"➕ {ch}", url=f"https://t.me/{ch[1:]}"))
    kb.add(types.InlineKeyboardButton("✅ Санҷиш", callback_data="check_sub"))
    return kb

def get_ad():
    now = int(time.time())
    ad = sql.execute(
        "SELECT text FROM ads WHERE end_time > ?", (now,)
    ).fetchone()
    return ad[0] if ad else None

def admin_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Реклама", callback_data="set_ad"))
    kb.add(types.InlineKeyboardButton("➕ Канал", callback_data="add_ch"))
    kb.add(types.InlineKeyboardButton("➖ Удалит канал", callback_data="del_ch"))
    kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    return kb

# ============ START ============
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    args = message.text.split()

    # ---- FILE LINK ----
    if len(args) > 1:
        fid = args[1]
        sql.execute("SELECT type, file_id FROM files WHERE id=?", (fid,))
        f = sql.fetchone()
        if not f:
            bot.send_message(uid, "❌ Файл ёфт нашуд")
            return

        if not check_sub(uid):
            bot.send_message(
                uid,
                "❗ Барои гирифтани файл аввал обуна шав 👇",
                reply_markup=sub_keyboard()
            )
            return

        if f[0] == "photo":
            bot.send_photo(uid, f[1])
        elif f[0] == "audio":
            bot.send_audio(uid, f[1])
        elif f[0] == "document":
            bot.send_document(uid, f[1])

        ad = get_ad()
        if ad:
            bot.send_message(uid, f"📢 <b>Реклама</b>\n\n{ad}")
        return

    # ---- ADMIN ----
    if uid == ADMIN_ID:
        bot.send_message(
            uid,
            "👑 <b>Панели админ</b>\n"
            "Файл фирист → бот ссылка месозад",
            reply_markup=admin_menu()
        )
        return

    # ---- USER ----
    if not check_sub(uid):
        bot.send_message(
            uid,
            "🌟 <b>Хуш омадед!</b>\n"
            "Барои истифодаи бот аввал обуна шав 👇",
            reply_markup=sub_keyboard()
        )
        return

    sql.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    db.commit()

    bot.send_message(uid, "🌟 <b>Хуш омадед!</b>")

# ============ CHECK SUB ============
@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def recheck(c):
    if check_sub(c.from_user.id):
        sql.execute("INSERT OR IGNORE INTO users VALUES (?)", (c.from_user.id,))
        db.commit()
        bot.edit_message_text(
            "✅ Обуна тасдиқ шуд",
            c.message.chat.id,
            c.message.message_id
        )
    else:
        bot.answer_callback_query(c.id, "❌ Ҳоло ҳам обуна нестӣ", show_alert=True)

# ============ ADMIN FILES ============
def save_file(ftype, fid, chat_id):
    sql.execute(
        "INSERT INTO files (type, file_id) VALUES (?,?)",
        (ftype, fid)
    )
    db.commit()
    file_id = sql.lastrowid
    link = f"https://t.me/{bot.get_me().username}?start={file_id}"
    bot.send_message(chat_id, f"🔗 <b>Ссылка тайёр:</b>\n{link}")

@bot.message_handler(content_types=["photo"])
def photo(m):
    if m.from_user.id == ADMIN_ID:
        save_file("photo", m.photo[-1].file_id, m.chat.id)

@bot.message_handler(content_types=["audio"])
def audio(m):
    if m.from_user.id == ADMIN_ID:
        save_file("audio", m.audio.file_id, m.chat.id)

@bot.message_handler(content_types=["document"])
def doc(m):
    if m.from_user.id == ADMIN_ID:
        save_file("document", m.document.file_id, m.chat.id)

# ============ ADS ============
@bot.callback_query_handler(func=lambda c: c.data == "set_ad")
def set_ad(c):
    msg = bot.send_message(ADMIN_ID, "✍️ Матни реклама:")
    bot.register_next_step_handler(msg, get_ad_text)

def get_ad_text(m):
    text = m.text
    msg = bot.send_message(ADMIN_ID, "⏰ Вақт (дақиқа):")
    bot.register_next_step_handler(msg, lambda x: save_ad(text, x))

def save_ad(text, m):
    try:
        minutes = int(m.text)
    except:
        bot.send_message(ADMIN_ID, "❌ Фақат рақам навис")
        return

    end = int(time.time()) + minutes * 60
    sql.execute("DELETE FROM ads")
    sql.execute("INSERT INTO ads VALUES (?,?)", (text, end))
    db.commit()
    bot.send_message(ADMIN_ID, "✅ Реклама фаъол шуд", reply_markup=admin_menu())

# ============ CHANNELS ============
@bot.callback_query_handler(func=lambda c: c.data == "add_ch")
def add_ch(c):
    msg = bot.send_message(ADMIN_ID, "@канал:")
    bot.register_next_step_handler(msg, save_ch)

def save_ch(m):
    if m.text.startswith("@"):
        sql.execute("INSERT INTO channels VALUES (?)", (m.text,))
        db.commit()
        bot.send_message(ADMIN_ID, "✅ Канал илова шуд", reply_markup=admin_menu())

@bot.callback_query_handler(func=lambda c: c.data == "del_ch")
def del_ch(c):
    chs = sql.execute("SELECT username FROM channels").fetchall()
    kb = types.InlineKeyboardMarkup()
    for (ch,) in chs:
        kb.add(types.InlineKeyboardButton(ch, callback_data=f"rm_{ch}"))
    bot.send_message(ADMIN_ID, "Каналро интихоб кун:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def rm_ch(c):
    ch = c.data[3:]
    sql.execute("DELETE FROM channels WHERE username=?", (ch,))
    db.commit()
    bot.edit_message_text("🗑 Канал удалит шуд", c.message.chat.id, c.message.message_id)

# ============ STATS ============
@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    count = sql.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    bot.send_message(ADMIN_ID, f"👥 Корбарон: {count}")

# ============ RUN ============
print("Bot started")
bot.infinity_polling()
