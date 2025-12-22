import telebot
from telebot import types
import sqlite3
import time

# ========= ТАНЗИМОТ =========
TOKEN = "PASTE_BOT_TOKEN"
ADMIN_ID = 123456789
# ============================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ========= БАЗА =========
db = sqlite3.connect("bot.db", check_same_thread=False)
sql = db.cursor()

sql.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
sql.execute("CREATE TABLE IF NOT EXISTS channels (username TEXT)")
sql.execute("CREATE TABLE IF NOT EXISTS ads (text TEXT, end_time INTEGER)")
db.commit()

# ========= ФУНКСИЯҲО =========
def check_sub(user_id):
    for (ch,) in sql.execute("SELECT username FROM channels"):
        try:
            s = bot.get_chat_member(ch, user_id).status
            if s not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def get_ad():
    now = int(time.time())
    ad = sql.execute("SELECT text FROM ads WHERE end_time > ?", (now,)).fetchone()
    return ad[0] if ad else None

def user_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎵 Заказать музыку", callback_data="music"))
    kb.add(types.InlineKeyboardButton("📷 Заказать фото", callback_data="photo"))
    kb.add(types.InlineKeyboardButton("📁 Заказать файл", callback_data="file"))
    return kb

def admin_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Реклама", callback_data="set_ad"))
    kb.add(types.InlineKeyboardButton("➕ Канал", callback_data="add_ch"))
    kb.add(types.InlineKeyboardButton("➖ Удалить канал", callback_data="del_ch"))
    kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="stats"))
    return kb

# ========= START =========
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id

    if uid == ADMIN_ID:
        bot.send_message(uid, "👑 <b>Панели админ</b>", reply_markup=admin_menu())
        return

    user = sql.execute("SELECT 1 FROM users WHERE id=?", (uid,)).fetchone()

    if not user:
        if not check_sub(uid):
            bot.send_message(uid, "❗ Аввал ба каналҳо обуна шав")
            return
        sql.execute("INSERT INTO users VALUES (?)", (uid,))
        db.commit()

    bot.send_message(uid, "🌟 Хуш омадед!\nФармоиш интихоб кунед 👇", reply_markup=user_menu())

# ========= ФАРМОИШ =========
@bot.callback_query_handler(func=lambda c: c.data in ["music", "photo", "file"])
def orders(c):
    names = {
        "music": "🎵 Музыка",
        "photo": "📷 Фото",
        "file": "📁 Файл"
    }

    bot.send_message(
        ADMIN_ID,
        f"🆕 <b>ФАРМОИШ</b>\n\n"
        f"{names[c.data]}\n"
        f"👤 @{c.from_user.username}\n"
        f"🆔 {c.from_user.id}"
    )

    bot.answer_callback_query(c.id, "✅ Фармоиш қабул шуд")

    ad = get_ad()
    if ad:
        bot.send_message(c.from_user.id, f"📢 <b>Реклама</b>\n\n{ad}")

# ========= РЕКЛАМА =========
@bot.callback_query_handler(func=lambda c: c.data == "set_ad")
def set_ad(c):
    msg = bot.send_message(ADMIN_ID, "Матни реклама:")
    bot.register_next_step_handler(msg, get_ad_text)

def get_ad_text(m):
    text = m.text
    msg = bot.send_message(ADMIN_ID, "Вақт (дақиқа):")
    bot.register_next_step_handler(msg, lambda x: save_ad(text, x))

def save_ad(text, m):
    end = int(time.time()) + int(m.text) * 60
    sql.execute("DELETE FROM ads")
    sql.execute("INSERT INTO ads VALUES (?,?)", (text, end))
    db.commit()
    bot.send_message(ADMIN_ID, "✅ Реклама фаъол шуд", reply_markup=admin_menu())

# ========= КАНАЛ =========
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
    bot.send_message(ADMIN_ID, "Удалить канал:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rm_"))
def rm(c):
    ch = c.data[3:]
    sql.execute("DELETE FROM channels WHERE username=?", (ch,))
    db.commit()
    bot.edit_message_text("🗑 Удалён", c.message.chat.id, c.message.message_id)

# ========= СТАТ =========
@bot.callback_query_handler(func=lambda c: c.data == "stats")
def stats(c):
    count = sql.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    bot.send_message(ADMIN_ID, f"👥 Корбарон: {count}")

# ========= RUN =========
print("Bot started")
bot.infinity_polling()
