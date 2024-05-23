import logging
from pprint import pprint
import sqlite3
import json
import datetime
import pytz
import time
from calendar import monthrange
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

state = {}
dict_bd_name = {}
dict_bd_rep = {}
users_list_cache = []

conn = sqlite3.connect("+rep_bot_db.sqlite")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                                    id INT PRIMARY KEY,
                                    name TEXT,
                                    reputation INT);""")

conn.commit()
conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("+rep_bot_db.sqlite")
    cursor = conn.cursor()
    user_list = cursor.execute(
        f'SELECT id FROM users WHERE id = "{update.effective_user.id}"'
    ).fetchone()
    if user_list == None:
        cursor.execute(
            f'INSERT INTO users VALUES({update.effective_user.id}, "{update.effective_user.username}", {0})'
        )
        conn.commit()
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"{update.effective_user.first_name}, вы успешно зарегистрировались в системе репутации 'Романенко Учит'!\nДобро пожаловать!",
            disable_notification=True,
        )

    conn.close()


async def write_rep(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("+rep_bot_db.sqlite")
    cursor = conn.cursor()
    text = "Репутация участников:"
    user_list = cursor.execute(
        f"SELECT * FROM users order by reputation DESC"
    ).fetchall()
    i = 0
    for person_data in user_list:
        text = f"{text}\n • {user_list[i][1]} --> {user_list[i][2]}."
        i += 1

    await context.bot.send_message(chat_id=-1001549196503, text=text)
    conn.close()


async def add_to_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(2)
    if update.effective_user.id in users_list_cache:
        return
    await delete_message(update, context)
    conn = sqlite3.connect("+rep_bot_db.sqlite")
    cursor = conn.cursor()
    user_list = cursor.execute(
        f'SELECT id FROM users WHERE id = "{update.effective_user.id}"'
    ).fetchone()
    if user_list == None:
        cursor.execute(
            f'INSERT INTO users VALUES({update.effective_user.id}, "{update.effective_user.username}", {0})'
        )
        conn.commit()
        users_list_cache.append(update.effective_user.id)

    conn.close()


async def rep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != -1001549196503:
        return

    conn = sqlite3.connect("+rep_bot_db.sqlite")
    cursor = conn.cursor()
    if update.effective_message.reply_to_message != None:
        id_rep = update.effective_message.reply_to_message.from_user.id
        rep = cursor.execute(
            f'SELECT reputation FROM users WHERE id = "{id_rep}"'
        ).fetchone()
        name = cursor.execute(
            f'SELECT name FROM users WHERE id = "{id_rep}"'
        ).fetchone()
        if rep == None or name == None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Вы не можете повысить репутацию этому человеку, т.к он не зарегистрировался",
            )
        elif id_rep == update.effective_user.id:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Вы не можете повысить репутацию самому себе",
            )
        else:
            cursor.execute(
                f"UPDATE users SET reputation = {rep[0] + 1} WHERE id = {id_rep}"
            )
            conn.commit()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Репутация {name[0]} повышена!\nТ"
                f"еперь репутация {name[0]} равна "
                f"{rep[0] + 1}",
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Вы можете использовать эту команду, если отвечаете кому-то...",
        )
    conn.close()


async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.effective_message.text
    if "вы успешно зарегистрировались" not in message_text:
        return
    elif "/start" not in message_text:
        return
    await asyncio.sleep(10)
    await update.message.delete()


if __name__ == "__main__":
    application = ApplicationBuilder().token(os.getenv("TOKEN")).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    rep_handler = CommandHandler("plus_rep", rep)
    application.add_handler(rep_handler)

    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, start)
    )

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, add_to_db))

    application.job_queue.run_daily(
        write_rep,
        time=datetime.time(hour=12, minute=00, tzinfo=pytz.timezone("Europe/Moscow")),
        chat_id=-1001549196503,
    )

    conn = sqlite3.connect("+rep_bot_db.sqlite")
    cursor = conn.cursor()

    users_list_cache = cursor.execute("SELECT id FROM users").fetchall()
    users_list_cache = [x[0] for x in users_list_cache]

    conn.close()

    application.run_polling()
