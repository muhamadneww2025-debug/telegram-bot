import os
import sqlite3
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8588404131
BOT_USERNAME = "Sobirov_muzrobot"  # бе @

bot = telebot.TeleBot(TOKEN)
db = sqlite3.connect("bot.db", check_same_thread=False)
sql = db.cursor()

# ---------- DATABASE ----------
sql.execute("""CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT,
    file_id TEXT
)""")

sql.execute("""CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT
)""")
db.commit()

# ---------- HELPERS ----------
def is_admin(uid):
    return uid == ADMIN_ID

def get_channels():
    sql.execute("SELECT username FROM channels")
    return [x[0] for x in sql.fetchall()]

def check_sub(uid):
    for ch in get_channels():
        try:
            m = bot.get_chat_member(ch, uid)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def sub_keyboard():
    kb = types.InlineKeyboardMarkup()
    for ch in get_channels():
        kb.add(types.InlineKeyboardButton(
            f"📢 {ch}", url=f"https://t.me/{ch.replace('@','')}"
        ))
    kb.add(types.InlineKeyboardButton("✅ Санҷиш", callback_data="check_sub"))
    return kb

# ---------- START ----------
@bot.message_handler(commands=["start"])
def start(message):
    args = message.text.split()

    if not check_sub(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "❗ Барои истифода аввал ба каналҳо обуна шав",
            reply_markup=sub_keyboard()
        )
        return

    if len(args) > 1:
        file_id = args[1]
        sql.execute("SELECT type, file_id FROM files WHERE id=?", (file_id,))
        f = sql.fetchone()
        if f:
            if f[0] == "photo":
                bot.send_photo(message.chat.id, f[1])
            elif f[0] == "audio":
                bot.send_audio(message.chat.id, f[1])
            elif f[0] == "document":
                bot.send_document(message.chat.id, f[1])
        else:
            bot.send_message(message.chat.id, "❌ Файл ёфт нашуд")
    else:
        bot.send_message(message.chat.id, "Салом 👋")

# ---------- CALLBACK ----------
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    if call.data == "check_sub":
        if check_sub(call.from_user.id):
            bot.edit_message_text(
                "✅ Обуна тасдиқ шуд",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(
                call.id,
                "❌ Ҳанӯз обуна нестӣ",
                show_alert=True
            )

    if call.data == "admin":
        admin_panel(call.message)

    if call.data == "add_channel":
        bot.send_message(
            call.message.chat.id,
            "Username каналро фирист (мисол: @channel)"
        )
        bot.register_next_step_handler(call.message, save_channel)

    if call.data == "del_channel":
        chs = get_channels()
        kb = types.InlineKeyboardMarkup()
        for c in chs:
            kb.add(types.InlineKeyboardButton(
                c, callback_data=f"del_{c}"
            ))
        bot.send_message(
            call.message.chat.id,
            "Каналро интихоб кун:",
            reply_markup=kb
        )

    if call.data.startswith("del_"):
        ch = call.data.replace("del_", "")
        sql.execute(
            "DELETE FROM channels WHERE username=?",
            (ch,)
        )
        db.commit()
        bot.edit_message_text(
            "✅ Удалит шуд",
            call.message.chat.id,
            call.message.message_id
        )

# ---------- ADMIN PANEL ----------
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "➕ Иловаи канал",
        callback_data="add_channel"
    ))
    kb.add(types.InlineKeyboardButton(
        "➖ Удалит канал",
        callback_data="del_channel"
    ))
    bot.send_message(
        message.chat.id,
        "👑 Админ панел",
        reply_markup=kb
    )

@bot.message_handler(commands=["admin"])
def admin_cmd(message):
    admin_panel(message)

def save_channel(message):
    if not message.text.startswith("@"):
        bot.send_message(message.chat.id, "❌ Хато")
        return
    sql.execute(
        "INSERT INTO channels(username) VALUES(?)",
        (message.text,)
    )
    db.commit()
    bot.send_message(message.chat.id, "✅ Канал илова шуд")

# ---------- FILE HANDLERS ----------
def save_file(ftype, fid, chat_id):
    sql.execute(
        "INSERT INTO files(type, file_id) VALUES(?,?)",
        (ftype, fid)
    )
    db.commit()
    file_id = sql.lastrowid
    link = f"https://t.me/{BOT_USERNAME}?start={file_id}"
    bot.send_message(chat_id, f"🔗 Линк:\n{link}")

@bot.message_handler(content_types=["photo"])
def photo(message):
    if is_admin(message.from_user.id):
        save_file("photo", message.photo[-1].file_id, message.chat.id)

@bot.message_handler(content_types=["audio"])
def audio(message):
    if is_admin(message.from_user.id):
        save_file("audio", message.audio.file_id, message.chat.id)

@bot.message_handler(content_types=["document"])
def doc(message):
    if is_admin(message.from_user.id):
        save_file("document", message.document.file_id, message.chat.id)

# ---------- RUN ----------
print("Bot started")
bot.infinity_polling()
