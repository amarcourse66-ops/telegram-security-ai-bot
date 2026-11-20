

import os
import sqlite3
import random
import asyncio
import logging
import tempfile
from datetime import datetime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ========== الإعدادات ==========

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7723868658
DB_NAME = "bot_data.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========== قاعدة البيانات ==========

def db():
    return sqlite3.connect(DB_NAME)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        user_id INTEGER PRIMARY KEY,
        bank TEXT,
        account_number TEXT UNIQUE,
        balance INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        amount INTEGER,
        details TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS marriages (
        user_id INTEGER PRIMARY KEY,
        partner_id INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS marriage_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        partner_id INTEGER,
        action TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS whispers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        message TEXT,
        created_at TEXT
    )
    """)

    con.commit()
    con.close()


# ========== أدوات مساعدة ==========

def save_user(user):
    con = db()
    con.execute("""
        INSERT OR REPLACE INTO users
        (user_id, username, first_name)
        VALUES (?, ?, ?)
    """, (user.id, user.username, user.first_name))
    con.commit()
    con.close()


def get_user_name(user_id):
    con = db()
    cur = con.cursor()
    cur.execute(
        "SELECT first_name FROM users WHERE user_id=?",
        (user_id,)
    )
    result = cur.fetchone()
    con.close()
    return result[0] if result else str(user_id)


def add_transaction(user_id, action, amount, details=""):
    con = db()
    con.execute("""
        INSERT INTO transactions
        (user_id, action, amount, details, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user_id, action, amount, details,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    con.commit()
    con.close()


def get_account(user_id):
    con = db()
    cur = con.cursor()
    cur.execute(
        "SELECT bank, account_number, balance FROM accounts WHERE user_id=?",
        (user_id,)
    )
    result = cur.fetchone()
    con.close()
    return result


def is_married(user_id):
    con = db()
    cur = con.cursor()
    cur.execute(
        "SELECT partner_id FROM marriages WHERE user_id=?",
        (user_id,)
    )
    result = cur.fetchone()
    con.close()
    return result[0] if result else None


BANKS = [
    "بنك شام",
    "بنك لين",
    "بنك اسكندر",
    "بنك أبو سليمان"
]

# ========== نهاية الدفعة الأولى ==========# ========== تشغيل البوت والترحيب ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    await update.message.reply_text(
        f"أهلاً وسهلاً {user.first_name} ❤️\n\n"
        "أنا بوت المجموعة، جاهز لخدمتك!\n"
        "اكتب /help لمعرفة الأوامر."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 أوامر البوت:\n\n"
        "💌 اهمس: بالرد على رسالة العضو اكتب اهمس\n"
        "🏦 /bank - إنشاء حساب بنكي\n"
        "💰 /balance - معرفة رصيدك\n"
        "💳 /deposit - إيداع\n"
        "💸 /withdraw - سحب\n"
        "📜 /statement - كشف حساب\n"
        "💍 زوجني - طلب زواج بالرد على العضو\n"
        "❤️ زوجتي أو زوجي - معرفة الشريك\n"
        "💔 طلاق - إنهاء الزواج\n"
        "🎮 /games - قائمة الألعاب"
    )


async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        save_user(member)
        await update.message.reply_text(
            f"أهلاً وسهلاً {member.first_name} 🌹\n"
            "نورت المجموعة ❤️"
        )


# ========== الحسابات البنكية ==========

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    account = get_account(user.id)

    if account:
        await update.message.reply_text(
            f"لديك حساب مسبقاً في {account[0]}."
        )
        return

    keyboard = [
        [InlineKeyboardButton(bank, callback_data=f"bank:{bank}")]
        for bank in BANKS
    ]

    await update.message.reply_text(
        "🏦 اختر البنك الذي تريد فتح حساب فيه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def bank_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("bank:"):
        return

    bank = query.data.split(":", 1)[1]
    user_id = query.from_user.id

    if bank not in BANKS:
        return

    if get_account(user_id):
        await query.edit_message_text("لديك حساب بنكي مسبقاً.")
        return

    account_number = str(random.randint(10000000, 99999999))

    con = db()
    try:
        con.execute("""
            INSERT INTO accounts
            (user_id, bank, account_number, balance)
            VALUES (?, ?, ?, 0)
        """, (user_id, bank, account_number))
        con.commit()
    except sqlite3.IntegrityError:
        await query.edit_message_text(
            "حدث خطأ، حاول فتح الحساب مرة ثانية."
        )
        return
    finally:
        con.close()

    await query.edit_message_text(
        f"🎉 تم فتح حسابك بنجاح!\n\n"
        f"🏦 البنك: {bank}\n"
        f"🔢 رقم الحساب: {account_number}\n"
        f"💰 الرصيد: 0"
    )


async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    account = get_account(update.effective_user.id)

    if not account:
        await update.message.reply_text("افتح حساباً أولاً باستخدام /bank")
        return

    await update.message.reply_text(
        f"🏦 {account[0]}\n"
        f"🔢 رقم الحساب: {account[1]}\n"
        f"💰 رصيدك: {account[2]}"
    )


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    account = get_account(user_id)

    if not account:
        await update.message.reply_text("افتح حساباً أولاً باستخدام /bank")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("اكتب هكذا:\n/deposit 100")
        return

    amount = int(context.args[0])

    if amount <= 0:
        await update.message.reply_text("المبلغ يجب أن يكون أكبر من صفر.")
        return

    con = db()
    con.execute(
        "UPDATE accounts SET balance=balance+? WHERE user_id=?",
        (amount, user_id)
    )
    con.commit()
    con.close()

    add_transaction(user_id, "إيداع", amount)

    await update.message.reply_text(
        f"✅ تم إيداع {amount} بنجاح!"
    )


async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    account = get_account(user_id)

    if not account:
        await update.message.reply_text("افتح حساباً أولاً باستخدام /bank")
        return

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("اكتب هكذا:\n/withdraw 100")
        return

    amount = int(context.args[0])

    if amount <= 0 or amount > account[2]:
        await update.message.reply_text("المبلغ غير صالح أو رصيدك غير كافٍ.")
        return

    con = db()
    con.execute(
        "UPDATE accounts SET balance=balance-? WHERE user_id=?",
        (amount, user_id)
    )
    con.commit()
    con.close()

    add_transaction(user_id, "سحب", amount)

    await update.message.reply_text(
        f"✅ تم سحب {amount} بنجاح!"
    )


async def statement_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    con = db()
    cur = con.cursor()
    cur.execute("""
        SELECT action, amount, details, created_at
        FROM transactions
        WHERE user_id=?
        ORDER BY id DESC LIMIT 10
    """, (user_id,))
    rows = cur.fetchall()
    con.close()

    if not rows:
        await update.message.reply_text("لا توجد حركات بنكية حتى الآن.")
        return

    result = "📜 آخر 10 حركات بحسابك:\n\n"

    for action, amount, details, created_at in rows:
        result += (
            f"• {action}: {amount}\n"
            f"  {details}\n"
            f"  {created_at}\n\n"
        )

    await update.message.reply_text(result)


# ========== نهاية الدفعة الثانية ==========# ========== التحويلات البنكية ==========

async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) != 2:
        await update.message.reply_text(
            "طريقة التحويل:\n/transfer رقم_المستخدم المبلغ"
        )
        return

    try:
        receiver_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("تأكد من رقم المستخدم والمبلغ.")
        return

    if receiver_id == user_id or amount <= 0:
        await update.message.reply_text("بيانات التحويل غير صالحة.")
        return

    con = db()
    cur = con.cursor()
    cur.execute("SELECT balance FROM accounts WHERE user_id=?", (user_id,))
    sender = cur.fetchone()
    cur.execute("SELECT balance FROM accounts WHERE user_id=?", (receiver_id,))
    receiver = cur.fetchone()

    if not sender or not receiver:
        con.close()
        await update.message.reply_text("يجب أن يمتلك الطرفان حساباً بنكياً.")
        return

    if sender[0] < amount:
        con.close()
        await update.message.reply_text("رصيدك لا يكفي للتحويل.")
        return

    con.execute("UPDATE accounts SET balance=balance-? WHERE user_id=?",
                (amount, user_id))
    con.execute("UPDATE accounts SET balance=balance+? WHERE user_id=?",
                (amount, receiver_id))
    con.commit()
    con.close()

    add_transaction(user_id, "تحويل صادر", amount, f"إلى {receiver_id}")
    add_transaction(receiver_id, "تحويل وارد", amount, f"من {user_id}")

    await update.message.reply_text(f"✅ تم تحويل {amount} بنجاح!")


# ========== الزواج ==========

async def marry_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    sender = update.effective_user

    if not message.reply_to_message:
        await message.reply_text("رد على رسالة الشخص واكتب زوجني 💍")
        return

    target = message.reply_to_message.from_user

    if target.is_bot or target.id == sender.id:
        await message.reply_text("ما فيك تتزوج نفسك أو بوت 😂")
        return

    if is_married(sender.id) or is_married(target.id):
        await message.reply_text("أحد الطرفين متزوج بالفعل.")
        return

    keyboard = [[
        InlineKeyboardButton("❤️ موافق", callback_data=f"marry:yes:{sender.id}:{target.id}"),
        InlineKeyboardButton("💔 رفض", callback_data=f"marry:no:{sender.id}:{target.id}")
    ]]

    await message.reply_text(
        f"💍 {target.first_name}، {sender.first_name} يطلب الزواج منك!\n"
        "هل توافق؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def marriage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split(":")

    if len(parts) != 4:
        await query.answer()
        return

    action = parts[1]
    sender_id = int(parts[2])
    target_id = int(parts[3])

    if query.from_user.id != target_id:
        await query.answer("هذا الطلب ليس موجهاً إليك!", show_alert=True)
        return

    await query.answer()

    if action == "no":
        await query.edit_message_text("💔 تم رفض طلب الزواج.")
        return

    if is_married(sender_id) or is_married(target_id):
        await query.edit_message_text("أحد الطرفين تزوج بالفعل.")
        return

    con = db()
    con.execute("INSERT INTO marriages VALUES (?, ?)", (sender_id, target_id))
    con.execute("INSERT INTO marriages VALUES (?, ?)", (target_id, sender_id))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con.execute(
        "INSERT INTO marriage_history (user_id, partner_id, action, created_at) VALUES (?, ?, ?, ?)",
        (sender_id, target_id, "زواج", now)
    )
    con.execute(
        "INSERT INTO marriage_history (user_id, partner_id, action, created_at) VALUES (?, ?, ?, ?)",
        (target_id, sender_id, "زواج", now)
    )
    con.commit()
    con.close()

    await query.edit_message_text("🎉 مبروك! تم الزواج ❤️💍")


async def partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = is_married(user_id)

    if not partner_id:
        await update.message.reply_text("أنت غير متزوج حالياً ❤️")
        return

    await update.message.reply_text(
        f"❤️ شريكك هو: {get_user_name(partner_id)}"
    )


async def divorce_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner_id = is_married(user_id)

    if not partner_id:
        await update.message.reply_text("أنت غير متزوج.")
        return

    con = db()
    con.execute("DELETE FROM marriages WHERE user_id IN (?, ?)",
                (user_id, partner_id))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    con.execute(
        "INSERT INTO marriage_history (user_id, partner_id, action, created_at) VALUES (?, ?, ?, ?)",
        (user_id, partner_id, "طلاق", now)
    )
    con.execute(
        "INSERT INTO marriage_history (user_id, partner_id, action, created_at) VALUES (?, ?, ?, ?)",
        (partner_id, user_id, "طلاق", now)
    )
    con.commit()
    con.close()

    await update.message.reply_text("💔 تم الطلاق. يمكنك الزواج مرة أخرى لاحقاً.")


async def married_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db()
    cur = con.cursor()
    cur.execute("SELECT user_id, partner_id FROM marriages WHERE user_id < partner_id")
    rows = cur.fetchall()
    con.close()

    if not rows:
        await update.message.reply_text("لا توجد زيجات حالياً.")
        return

    result = "💍 قائمة المتزوجين:\n\n"
    for first, second in rows:
        result += f"❤️ {get_user_name(first)} و {get_user_name(second)}\n"

    await update.message.reply_text(result)


# ========== نهاية الدفعة الثالثة ==========# ========== الهمسات الخاصة ==========

async def whisper_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)

    if context.args and context.args[0] == "whisper":
        target_id = context.user_data.get("whisper_target")
        if target_id:
            await update.message.reply_text(
                "💌 اكتب نص الهمسة الآن، أو /cancel للإلغاء."
            )
            return

    await update.message.reply_text(
        "أهلاً بك ❤️\nاكتب /help لمعرفة الأوامر."
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("whisper_target", None)
    await update.message.reply_text("تم إلغاء الهمسة.")


async def whisper_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        await message.reply_text("لازم ترد على رسالة الشخص وتكتب اهمس.")
        return

    target = message.reply_to_message.from_user
    sender = update.effective_user

    if target.is_bot or target.id == sender.id:
        await message.reply_text("ما فيك تهمس لنفسك أو لبوت.")
        return

    context.user_data["whisper_target"] = target.id

    try:
        await context.bot.send_message(
            sender.id,
            "💌 اكتب نص الهمسة التي تريد إرسالها."
        )
    except Exception:
        await message.reply_text(
            "افتح محادثتي واضغط Start أولاً، ثم جرّب مرة ثانية."
        )
        return

    await message.reply_text("💌 أرسلت لك بالخاص. اكتب الهمسة هناك.")


async def whisper_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    target_id = context.user_data.get("whisper_target")

    if not target_id:
        return

    message_text = update.message.text

    if not message_text or message_text.startswith("/"):
        return

    try:
        await context.bot.send_message(
            target_id,
            f"💌 وصلتك همسة خاصة:\n\n{message_text}"
        )
    except Exception:
        await update.message.reply_text(
            "ما قدرت أوصل الهمسة. لازم المستلم يفتح البوت ويضغط Start."
        )
        return

    # إشراف المالك: تُرسل نسخة للمالك كما هو معلن للمستخدمين
    try:
        await context.bot.send_message(
            OWNER_ID,
            f"📋 نسخة إشراف على همسة:\n"
            f"من: {user.id}\nإلى: {target_id}\n\n{message_text}"
        )
    except Exception:
        logging.exception("تعذر إرسال نسخة الإشراف للمالك")

    con = db()
    con.execute(
        "INSERT INTO whispers (sender_id, receiver_id, message, created_at) VALUES (?, ?, ?, ?)",
        (user.id, target_id, message_text,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    con.commit()
    con.close()

    context.user_data.pop("whisper_target", None)
    await update.message.reply_text("✅ وصلت الهمسة!")


# ========== الألعاب ==========

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎭 صراحة وجرأة", callback_data="game:truth")],
        [InlineKeyboardButton("✊ حجر ورقة مقص", callback_data="game:rps")],
        [InlineKeyboardButton("🧠 مين أنا؟", callback_data="game:who")],
        [InlineKeyboardButton("🎡 عجلة الحظ", callback_data="game:wheel")],
        [InlineKeyboardButton("❓ تحدي المعلومات", callback_data="game:quiz")],
        [InlineKeyboardButton("🕵️ لعبة المافيا", callback_data="game:mafia")]
    ]

    await update.message.reply_text(
        "🎮 اختار اللعبة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    game = query.data.split(":")[1]

    if game == "truth":
        question = random.choice([
            "ما هو أكبر سر احتفظت به؟",
            "مين آخر شخص فكرت فيه؟",
            "شو أكثر موقف محرج صار معك؟",
            "شو الشي اللي بتخاف تعترف فيه؟"
        ])
        dare = random.choice([
            "غنّي مقطع أغنية 🎤",
            "قل نكتة للمجموعة 😂",
            "اكتب مجاملة لشخص بالمجموعة ❤️",
            "غيّر اسمك لمدة عشر دقائق 😄"
        ])
        await query.edit_message_text(
            f"🎭 صراحة: {question}\n\n🔥 جرأة: {dare}"
        )

    elif game == "rps":
        keyboard = [[
            InlineKeyboardButton("✊ حجر", callback_data="rps:حجر"),
            InlineKeyboardButton("📄 ورقة", callback_data="rps:ورقة"),
            InlineKeyboardButton("✂️ مقص", callback_data="rps:مقص")
        ]]
        await query.edit_message_text(
            "اختار حركتك:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif game == "who":
        names = ["أسد", "طبيب", "طيار", "قطة", "ملك", "معلم"]
        answer = random.choice(names)
        context.user_data["who_answer"] = answer
        await query.edit_message_text(
            "🧠 مين أنا؟\n"
            "أنا أملك جناحين لكنني لست طائراً، من أنا؟\n"
            "هذه الجولة للتسلية، والجواب: طائرة."
        )

    elif game == "wheel":
        prize = random.choice([
            "ربحت 100 نقطة افتراضية 🎉",
            "حظ أوفر المرة القادمة 😅",
            "ربحت لقب محظوظ المجموعة 🍀",
            "عليك تحدي صراحة 😂"
        ])
        await query.edit_message_text(f"🎡 عجلة الحظ:\n{prize}")

    elif game == "quiz":
        context.user_data["quiz_answer"] = "باريس"
        await query.edit_message_text(
            "❓ ما عاصمة فرنسا؟\n"
            "اكتب جوابك برسالة في المجموعة."
        )

    elif game == "mafia":
        await query.edit_message_text(
            "🕵️ لعبة المافيا:\n"
            "هذه نسخة تمهيدية؛ تحتاج مجموعة من اللاعبين "
            "لتوزيع الأدوار وبدء جولة منظمة.\n"
            "لم تكتمل بعد جولات التصويت والإقصاء."
        )


async def rps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data.split(":")[1]
    bot_choice = random.choice(["حجر", "ورقة", "مقص"])

    if choice == bot_choice:
        result = "تعادل! 🤝"
    elif (choice, bot_choice) in [
        ("حجر", "مقص"),
        ("ورقة", "حجر"),
        ("مقص", "ورقة")
    ]:
        result = "فزت! 🎉"
    else:
        result = "خسرت! 😄"

    await query.edit_message_text(
        f"اختيارك: {choice}\nاختياري: {bot_choice}\n{result}"
    )


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()

    if message.chat.type == "private":
        if context.user_data.get("whisper_target"):
            await whisper_private(update, context)
        return

    if text == "اهمس":
        await whisper_group(update, context)

    elif text == "زوجني":
        await marry_command(update, context)

    elif text in ("زوجتي", "زوجي"):
        await partner_command(update, context)

    elif text == "طلاق":
        await divorce_command(update, context)

    elif text == "المتزوجين":
        await married_list(update, context)


# ========== تشغيل البوت ==========

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN غير موجود في Secrets")

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))

    app.add_handler(CommandHandler("bank", bank_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("deposit", deposit_command))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("statement", statement_command))
    app.add_handler(CommandHandler("transfer", transfer_command))

    app.add_handler(CommandHandler("games", games_command))

    app.add_handler(CallbackQueryHandler(bank_callback, pattern=r"^bank:"))
    app.add_handler(CallbackQueryHandler(marriage_callback, pattern=r"^marry:"))
    app.add_handler(CallbackQueryHandler(game_callback, pattern=r"^game:"))
    app.add_handler(CallbackQueryHandler(rps_callback, pattern=r"^rps:"))

    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome)
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_router)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
