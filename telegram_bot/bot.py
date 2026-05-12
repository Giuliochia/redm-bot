import os
import sys
import logging
import re
import json
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "391476319"))
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
PROMO_THREAD_ID = int(os.getenv("PROMO_THREAD_ID", "0"))
DATABASE_URL = os.getenv("DATABASE_URL")

# Telegram logger
tg_logger = logging.getLogger("redm_telegram")
tg_logger.setLevel(logging.INFO)
tg_handler = logging.StreamHandler()
tg_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
tg_logger.addHandler(tg_handler)

if not TOKEN:
    tg_logger.critical("TOKEN Telegram non impostato. Uscita.")
    sys.exit(1)

if not DATABASE_URL:
    tg_logger.critical("DATABASE_URL non impostato. Uscita.")
    sys.exit(1)

PLAYER_THREAD_ID = 62
STAFF_THREAD_ID = 63
DEV_THREAD_ID = 64

BOT_USERNAME = "redmhub_ita_bot"

ASK_NAME, ASK_WL, ASK_DESC, ASK_FEATURES, ASK_DISCORD, ASK_BANNER, ASK_CONFIRM = range(7)
LOOK_TYPE, LOOK_SERVER, LOOK_ROLE, LOOK_DESC, LOOK_DISCORD = range(7, 12)

FEATURED_FILE = "featured_servers.json"
WARNINGS_FILE = "warnings.json"
PENDING_FILE = "pending_servers.json"

pending_verifications = {}

BAD_WORDS = [
    "mongolo", "ritardato", "handicappato", "frocio", "negro",
    "zingaro", "server di merda", "server merda", "fai schifo",
    "killati", "ammazzati"
]

ALLOWED_LINKS = [
    "discord.gg", "discord.com", "youtube.com", "youtu.be",
    "tiktok.com", "t.me", "telegram.me"
]

DISCORD_INVITE_REGEX = re.compile(
    r"^(https?://)?(www\.)?"
    r"(discord\.gg/[a-zA-Z0-9-]+|discord\.com/invite/[a-zA-Z0-9-]+|discordapp\.com/invite/[a-zA-Z0-9-]+)"
    r"/?(\?.*)?$",
    re.IGNORECASE
)

servers = {
    "wildlands": {
        "nome": "Wildlands Italia",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Roleplay immersivo", "Community italiana", "Sistema whitelist"],
        "discord": "https://discord.gg/wildlandsita",
        "image": "wildlands.jpg",
        "image_file_id": None,
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "streets": {
        "nome": "Streets of Saints",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano.",
        "feature": ["Roleplay", "Community attiva", "Esperienza immersiva"],
        "discord": "https://discord.gg/streetsofsaints",
        "image": "streets.png",
        "image_file_id": None,
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "madwest": {
        "nome": "Mad West",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Roleplay Far West", "Whitelist attiva", "Community italiana"],
        "discord": "https://discord.gg/E3gYt2EuTH",
        "image": "madwest.png",
        "image_file_id": None,
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "newhope": {
        "nome": "1886 New Hope",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Ambientazione 1886", "Roleplay realistico", "Community attiva"],
        "discord": "https://discord.gg/ZdYQk7NCNV",
        "image": "newhope.png",
        "image_file_id": None,
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "westworld": {
        "nome": "West World 2.0",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": [
            "Roleplay immersivo",
            "Community italiana",
            "Sistema whitelist",
            "Eventi e interazioni tra player"
        ],
        "discord": "https://discord.gg/8PTeBBzvk",
        "image": None,
        "image_file_id": None,
        "badge": "⭐ SERVER CONSIGLIATO"
    }
}

partners = {
    "server_partner": {
        "titolo": "🌟 Server Partner",
        "descrizione": "Server RedM selezionati come partner ufficiali della community.",
        "items": ["Disponibile prossimamente"]
    },
    "creator_partner": {
        "titolo": "🎥 Creator Partner",
        "descrizione": "Creator e streamer che supportano la community RedM italiana.",
        "items": ["Disponibile prossimamente"]
    },
    "sponsor_partner": {
        "titolo": "📢 Sponsor",
        "descrizione": "Spazi dedicati a sponsor, collaborazioni e progetti in evidenza.",
        "items": ["Slot sponsor disponibile"]
    }
}


def db_connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL non impostato nelle variabili Railway.")

    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS featured_servers (
                    server_key TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS pending_servers (
                    submission_id TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    submitted_by_id BIGINT,
                    submitted_by_username TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    warning_key TEXT PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    warns INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS admin_logs (
                    id BIGSERIAL PRIMARY KEY,
                    text TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS verified_users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    chat_id BIGINT,
                    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

        conn.commit()


def load_json_file(path, default):
    if not os.path.exists(path):
        return default

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def migrate_old_json_files():
    old_featured = load_json_file(FEATURED_FILE, {})
    old_pending = load_json_file(PENDING_FILE, {})
    old_warnings = load_json_file(WARNINGS_FILE, {})

    with db_connect() as conn:
        with conn.cursor() as cur:
            for server_key, data in old_featured.items():
                cur.execute(
                    """
                    INSERT INTO featured_servers (server_key, data)
                    VALUES (%s, %s)
                    ON CONFLICT (server_key) DO NOTHING;
                    """,
                    (server_key, Jsonb(data))
                )

            for submission_id, data in old_pending.items():
                cur.execute(
                    """
                    INSERT INTO pending_servers (
                        submission_id,
                        data,
                        submitted_by_id,
                        submitted_by_username
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (submission_id) DO NOTHING;
                    """,
                    (
                        submission_id,
                        Jsonb(data),
                        data.get("submitted_by_id"),
                        data.get("submitted_by_username")
                    )
                )

            for warning_key, warns in old_warnings.items():
                try:
                    chat_id, user_id = warning_key.split("_", 1)
                    cur.execute(
                        """
                        INSERT INTO warnings (warning_key, chat_id, user_id, warns)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (warning_key) DO NOTHING;
                        """,
                        (warning_key, int(chat_id), int(user_id), int(warns))
                    )
                except Exception:
                    pass

        conn.commit()


def get_featured_servers():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT server_key, data FROM featured_servers ORDER BY created_at ASC;")
            rows = cur.fetchall()

    return {row["server_key"]: row["data"] for row in rows}


def count_featured_servers():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM featured_servers;")
            return cur.fetchone()["total"]


def save_featured_server(server_key, data):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO featured_servers (server_key, data)
                VALUES (%s, %s)
                ON CONFLICT (server_key)
                DO UPDATE SET data = EXCLUDED.data;
                """,
                (server_key, Jsonb(data))
            )

        conn.commit()


def delete_featured_server(server_key):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM featured_servers WHERE server_key = %s;", (server_key,))
        conn.commit()


def get_pending_server(submission_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data FROM pending_servers WHERE submission_id = %s;",
                (submission_id,)
            )
            row = cur.fetchone()

    if not row:
        return None

    return row["data"]


def save_pending_server(submission_id, data, user):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pending_servers (
                    submission_id,
                    data,
                    submitted_by_id,
                    submitted_by_username
                )
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (submission_id)
                DO UPDATE SET data = EXCLUDED.data;
                """,
                (
                    submission_id,
                    Jsonb(data),
                    user.id,
                    user.username or "senza username"
                )
            )

        conn.commit()


def delete_pending_server(submission_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM pending_servers WHERE submission_id = %s;", (submission_id,))
        conn.commit()


def count_pending_servers():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM pending_servers;")
            return cur.fetchone()["total"]


def get_warning_count(chat_id, user_id):
    warning_key = f"{chat_id}_{user_id}"

    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT warns FROM warnings WHERE warning_key = %s;",
                (warning_key,)
            )
            row = cur.fetchone()

    if not row:
        return 0

    return row["warns"]


def set_warning_count(chat_id, user_id, warns):
    warning_key = f"{chat_id}_{user_id}"

    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO warnings (warning_key, chat_id, user_id, warns, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (warning_key)
                DO UPDATE SET warns = EXCLUDED.warns, updated_at = NOW();
                """,
                (warning_key, chat_id, user_id, warns)
            )

        conn.commit()


def count_warnings():
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM warnings WHERE warns > 0;")
            return cur.fetchone()["total"]


def save_admin_log_to_db(text):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO admin_logs (text) VALUES (%s);",
                (text,)
            )

        conn.commit()


def save_verified_user(user_id, username, chat_id):
    with db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO verified_users (user_id, username, chat_id, verified_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET username = EXCLUDED.username, chat_id = EXCLUDED.chat_id, verified_at = NOW();
                """,
                (user_id, username, chat_id)
            )

        conn.commit()


def make_featured_key(name):
    featured_servers = get_featured_servers()

    base = re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")
    key = f"feat_{base}"

    counter = 1
    original = key

    while key in servers or key in featured_servers:
        counter += 1
        key = f"{original}_{counter}"

    return key


def get_all_servers():
    all_servers = {}
    all_servers.update(servers)
    all_servers.update(get_featured_servers())
    return all_servers


def is_owner_user_id(user_id):
    return user_id == ADMIN_ID


async def require_owner_callback(query):
    if not is_owner_user_id(query.from_user.id):
        await query.answer("Accesso riservato agli admin.", show_alert=True)
        return False

    return True


async def admin_log(context: ContextTypes.DEFAULT_TYPE, text):
    try:
        save_admin_log_to_db(text)
    except Exception:
        pass

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🧾 LOG ADMIN\n\n{text}"
        )
    except Exception:
        pass


def home_keyboard(user_id=None):
    keyboard = [
        [InlineKeyboardButton("⭐ Server consigliati", callback_data="server_list")],
        [InlineKeyboardButton("👥 Cerca Player/Fazione", callback_data="looking_menu")],
        [InlineKeyboardButton("🤝 Partnership", callback_data="partnership")],
        [InlineKeyboardButton("📨 Candidatura server", callback_data="candidate")],
        [InlineKeyboardButton("📢 Pubblicizza server", callback_data="promo")],
        [InlineKeyboardButton("📜 Regole", callback_data="regole")]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🧰 Pannello admin", callback_data="admin_panel")])

    return InlineKeyboardMarkup(keyboard)


def full_permissions():
    return ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    )


def no_permissions():
    return ChatPermissions(can_send_messages=False)


def clean_link(text):
    return text.strip().strip("<>").rstrip(".,;!?)(")


def is_valid_discord_link(text):
    link = clean_link(text)
    return bool(DISCORD_INVITE_REGEX.match(link))


def format_premium_card(server):
    features = "\n".join([f"• {f}" for f in server["feature"]])

    return f"""━━━━━━━━━━━━━━
{server.get('badge', '⭐ SERVER CONSIGLIATO')}
━━━━━━━━━━━━━━

🏜 {server['nome']}

🎭 Tipo: Roleplay
🌍 Lingua: Italiano
🔐 Whitelist: {server['whitelist']}

📜 Descrizione:
{server['descrizione']}

⚙️ Features:
{features}

━━━━━━━━━━━━━━

🔗 Discord:
{server['discord']}

🤠 RedM Hub Italia
"""


def format_public_server_post(server):
    features = "\n".join([f"• {f}" for f in server["feature"]])

    return f"""━━━━━━━━━━━━━━
🏜 {server['nome']}
━━━━━━━━━━━━━━

🎭 Tipo: Roleplay
🌍 Lingua: Italiano
🔐 Whitelist: {server['whitelist']}

📜 Descrizione:
{server['descrizione']}

⚙️ Features:
{features}

━━━━━━━━━━━━━━

🔗 Discord:
{server['discord']}

🤠 RedM Hub Italia
"""


def format_looking_post(data):
    tipo = data["tipo"]

    titles = {
        "player": "👤 CERCO PLAYER",
        "fazione": "🤠 CERCO FAZIONE",
        "staff": "🛡 CERCO STAFF",
        "developer": "💻 CERCO DEVELOPER"
    }

    labels = {
        "player": "🔎 Cerchiamo",
        "fazione": "🔎 Cerco",
        "staff": "🎭 Ruolo",
        "developer": "💻 Figura"
    }

    return f"""━━━━━━━━━━━━━━
{titles[tipo]}
━━━━━━━━━━━━━━

🏜 Server:
{data['server']}

{labels[tipo]}:
{data['ruolo']}

📜 Descrizione:
{data['descrizione']}

🔗 Discord:
{data['discord']}

🤠 RedM Hub Italia
"""


def contains_bad_word(text):
    lower_text = text.lower()
    return any(word in lower_text for word in BAD_WORDS)


def contains_bad_link(text):
    links = re.findall(r"(https?://\S+|www\.\S+)", text.lower())

    for link in links:
        if not any(allowed in link for allowed in ALLOWED_LINKS):
            return True

    return False


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        return member.status in ["administrator", "creator"]
    except Exception:
        return False


async def verify_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    user_id = data["user_id"]

    key = f"{chat_id}_{user_id}"

    if key not in pending_verifications:
        return

    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)

        await context.bot.send_message(
            chat_id=chat_id,
            text="🚫 Utente rimosso: verifica non completata entro 60 secondi."
        )

        await admin_log(
            context,
            f"🚫 Verifica fallita\n\nChat ID: {chat_id}\nUtente ID: {user_id}\nAzione: espulso automaticamente"
        )

    except Exception:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="⚠️ Non sono riuscito a rimuovere un utente non verificato. Controlla i permessi del bot."
        )

    pending_verifications.pop(key, None)


async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_CHAT_ID:
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        user_id = member.id
        chat_id = update.effective_chat.id
        key = f"{chat_id}_{user_id}"

        pending_verifications[key] = True

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=no_permissions()
            )
        except Exception:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ Non sono riuscito a bloccare temporaneamente un nuovo utente. Controlla i permessi del bot."
            )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Verificami", callback_data=f"verify_{user_id}")]
        ])

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 Benvenuto {member.mention_html()}!\n\n"
                "Per accedere alla community premi il bottone qui sotto.\n"
                "Hai 60 secondi per verificarti."
            ),
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        if context.job_queue:
            context.job_queue.run_once(
                verify_timeout_job,
                when=60,
                data={"chat_id": chat_id, "user_id": user_id},
                name=f"verify_{chat_id}_{user_id}"
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=(
                    "⚠️ JobQueue non disponibile.\n\n"
                    "Installa python-telegram-bot con:\n"
                    "python-telegram-bot[job-queue]"
                )
            )

        await admin_log(
            context,
            f"🛡 Nuovo utente in verifica\n\nUtente: @{member.username or 'senza username'}\nID: {user_id}\nTempo: 60 secondi"
        )


async def verify_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.replace("verify_", ""))
    clicker_id = query.from_user.id
    chat_id = query.message.chat_id
    key = f"{chat_id}_{user_id}"

    if clicker_id != user_id:
        await query.answer("Questo bottone non è per te.", show_alert=True)
        return

    if key not in pending_verifications:
        await query.answer("Verifica già completata o scaduta.", show_alert=True)
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=full_permissions()
        )
    except Exception:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text="⚠️ Non sono riuscito a sbloccare un utente verificato. Controlla i permessi del bot."
        )
        return

    pending_verifications.pop(key, None)
    save_verified_user(user_id, query.from_user.username or "senza username", chat_id)

    await query.edit_message_text(
        "✅ Verifica completata!\n\n"
        "Benvenuto in RedM Hub Italia 🤠"
    )

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "📌 Guida rapida community\n\n"
            "⭐ Server consigliati → trovi i server RedM selezionati\n"
            "📢 Promo Server → usa il bot per candidare il tuo server\n"
            "👥 Cerco Player/Fazione → trova player o gruppi RP\n"
            "🛡 Cerco Staff → cerca o offri supporto staff\n"
            "💻 Cerco Developer → cerca dev RedM / Lua / mapping\n\n"
            "❌ No spam, no flame, rispetto per tutti."
        )
    )

    await admin_log(
        context,
        f"✅ Verifica completata\n\nUtente: @{query.from_user.username or 'senza username'}\nID: {user_id}"
    )


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE, reason):
    user = update.effective_user
    chat_id = update.effective_chat.id

    warns = get_warning_count(chat_id, user.id) + 1
    set_warning_count(chat_id, user.id, warns)

    try:
        await update.message.delete()
    except Exception:
        pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"⚠️ Messaggio rimosso\n\n"
            f"👤 Utente: {user.mention_html()}\n"
            f"📌 Motivo: {reason}\n"
            f"🚨 Warn: {warns}/3"
        ),
        parse_mode="HTML"
    )

    await admin_log(
        context,
        f"🚨 Moderazione\n\n"
        f"Gruppo: {update.effective_chat.title}\n"
        f"Utente: @{user.username or 'senza username'}\n"
        f"ID: {user.id}\n"
        f"Motivo: {reason}\n"
        f"Warn: {warns}/3"
    )

    if warns >= 3:
        until_date = datetime.now(timezone.utc) + timedelta(minutes=10)

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=no_permissions(),
                until_date=until_date
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 {user.mention_html()} è stato mutato per 10 minuti.",
                parse_mode="HTML"
            )

            set_warning_count(chat_id, user.id, 0)

            await admin_log(
                context,
                f"🔇 Mute automatico\n\nUtente: @{user.username or 'senza username'}\nID: {user.id}\nDurata: 10 minuti"
            )

        except Exception:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text="⚠️ Non sono riuscito a mutare l’utente. Controlla i permessi admin del bot."
            )


async def moderate_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    if update.effective_chat.id != GROUP_CHAT_ID:
        return

    if await is_admin(update, context):
        return

    text = update.message.text

    if contains_bad_word(text):
        await warn_user(update, context, "linguaggio offensivo / flame")
        return

    if contains_bad_link(text):
        await warn_user(update, context, "link non consentito")
        return


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤠 RedM Hub Italia\n\n"
        "La community italiana dedicata ai server RedM.\n\n"
        "Scegli una sezione:",
        reply_markup=home_keyboard(update.effective_user.id)
    )


async def start_candidate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "📨 Candidatura server\n\n"
        "Scrivi il nome del server:"
    )

    return ASK_NAME


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message

    await update.message.reply_text(
        f"CHAT ID:\n{chat.id}\n\nTHREAD ID:\n{message.message_thread_id}"
    )


async def promo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_CHAT_ID:
        return

    link = f"https://t.me/{BOT_USERNAME}?start=candidatura"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Promuovi il tuo server", url=link)]
    ])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        message_thread_id=update.effective_message.message_thread_id,
        text=(
            "📨 Vuoi pubblicizzare il tuo server RedM?\n\n"
            "Premi il bottone qui sotto per inviare la candidatura.\n\n"
            "Un admin controllerà la richiesta e, se approvata, verrà pubblicata nella community."
        ),
        reply_markup=keyboard
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "home":
        await query.edit_message_text(
            "🤠 RedM Hub Italia\n\nScegli una sezione:",
            reply_markup=home_keyboard(query.from_user.id)
        )

    elif query.data == "server_list":
        all_servers = get_all_servers()
        keyboard = []

        for key, server in all_servers.items():
            keyboard.append([
                InlineKeyboardButton(f"🏜 {server['nome']}", callback_data=key)
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Indietro", callback_data="home")])

        await query.edit_message_text(
            "⭐ Server consigliati\n\nSeleziona un server:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data in get_all_servers():
        all_servers = get_all_servers()
        server = all_servers[query.data]
        caption = format_premium_card(server)

        keyboard = [
            [InlineKeyboardButton("🔗 Entra nel Discord", url=server["discord"])],
            [InlineKeyboardButton("⬅️ Torna ai server", callback_data="server_list")]
        ]

        image_file_id = server.get("image_file_id")
        image = server.get("image")

        if image_file_id:
            await query.message.reply_photo(
                photo=image_file_id,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif image and os.path.exists(image):
            with open(image, "rb") as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            await query.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=False
            )

    elif query.data == "looking_menu":
        keyboard = [
            [InlineKeyboardButton("👤 Cerco Player", callback_data="look_player")],
            [InlineKeyboardButton("🤠 Cerco Fazione", callback_data="look_fazione")],
            [InlineKeyboardButton("🛡 Cerco Staff", callback_data="look_staff")],
            [InlineKeyboardButton("💻 Cerco Developer", callback_data="look_developer")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "👥 Ricerca Player / Fazioni / Staff\n\n"
            "Scegli cosa vuoi pubblicare nella community:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("look_"):
        tipo = query.data.replace("look_", "")
        context.user_data.clear()
        context.user_data["looking"] = {"tipo": tipo}

        await query.message.reply_text(
            "🏜 Scrivi il nome del server:"
        )

        return LOOK_SERVER

    elif query.data == "partnership":
        keyboard = [
            [InlineKeyboardButton("🌟 Server Partner", callback_data="server_partner")],
            [InlineKeyboardButton("🎥 Creator Partner", callback_data="creator_partner")],
            [InlineKeyboardButton("📢 Sponsor", callback_data="sponsor_partner")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "🤝 Partnership\n\n"
            "Scopri i partner ufficiali della community RedM Hub Italia.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data in partners:
        partner = partners[query.data]
        items = "\n".join([f"• {item}" for item in partner["items"]])

        text = f"""━━━━━━━━━━━━━━
{partner['titolo']}
━━━━━━━━━━━━━━

{partner['descrizione']}

📌 Lista:
{items}

━━━━━━━━━━━━━━

🤝 Vuoi diventare partner?
Contatta un admin della community.
"""

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Torna alle partnership", callback_data="partnership")]
            ])
        )

    elif query.data == "candidate":
        context.user_data.clear()

        await query.message.reply_text(
            "📨 Candidatura server\n\n"
            "Scrivi il nome del server:"
        )

        return ASK_NAME

    elif query.data == "promo":
        link = f"https://t.me/{BOT_USERNAME}?start=candidatura"

        keyboard = [
            [InlineKeyboardButton("📨 Promuovi il tuo server", url=link)],
            [InlineKeyboardButton("📢 Vai al gruppo", url="https://t.me/redmitacommunity")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "📢 Vuoi pubblicizzare il tuo server?\n\n"
            "Premi il bottone qui sotto e completa la candidatura nel bot.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "regole":
        await query.edit_message_text(
            "📜 REGOLE\n\n"
            "• Niente spam\n"
            "• Usa i topic corretti\n"
            "• Rispetta gli altri\n"
            "• Max 1 promo ogni 48 ore\n"
            "• Le candidature vengono approvate manualmente",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
            ])
        )

    elif query.data == "admin_panel":
        if not await require_owner_callback(query):
            return

        keyboard = [
            [InlineKeyboardButton("⭐ Gestisci consigliati", callback_data="manage_featured")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "🧰 Pannello Admin\n\n"
            f"📨 Candidature in attesa: {count_pending_servers()}\n"
            f"⭐ Server consigliati aggiunti: {count_featured_servers()}\n"
            f"🚨 Warn attivi: {count_warnings()}\n"
            f"🛡 Verifiche in corso: {len(pending_verifications)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "manage_featured":
        if not await require_owner_callback(query):
            return

        featured_servers = get_featured_servers()

        if len(featured_servers) == 0:
            await query.edit_message_text(
                "⭐ Nessun server consigliato aggiunto.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Torna admin", callback_data="admin_panel")]
                ])
            )
            return

        keyboard = []

        for key, server in featured_servers.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {server['nome']}",
                    callback_data=f"remove_featured_{key}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅️ Torna admin", callback_data="admin_panel")])

        await query.edit_message_text(
            "⭐ Gestisci server consigliati\n\n"
            "Seleziona un server da rimuovere:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("remove_featured_"):
        if not await require_owner_callback(query):
            return

        featured_key = query.data.replace("remove_featured_", "")
        featured_servers = get_featured_servers()

        if featured_key not in featured_servers:
            await query.edit_message_text(
                "❌ Server non trovato.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Torna admin", callback_data="admin_panel")]
                ])
            )
            return

        server_name = featured_servers[featured_key]["nome"]

        delete_featured_server(featured_key)

        await query.edit_message_text(
            f"❌ Server rimosso dai consigliati\n\n🏜 {server_name}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Torna admin", callback_data="admin_panel")]
            ])
        )

        await admin_log(
            context,
            f"⭐ Server rimosso dai consigliati\n\nServer: {server_name}\nAdmin: @{query.from_user.username or 'senza username'}"
        )

    elif query.data.startswith("approve_featured_"):
        if not await require_owner_callback(query):
            return

        submission_id = query.data.replace("approve_featured_", "")
        server = get_pending_server(submission_id)

        if not server:
            await query.edit_message_text("❌ Candidatura non trovata o già gestita.")
            return

        server["badge"] = "⭐ SERVER CONSIGLIATO"
        server["image"] = None

        featured_key = make_featured_key(server["nome"])
        save_featured_server(featured_key, server)

        await publish_server(context, server)

        await query.edit_message_text(
            f"⭐ Candidatura approvata e aggiunta ai consigliati\n\n🏜 {server['nome']}"
        )

        delete_pending_server(submission_id)

        await admin_log(
            context,
            f"⭐ Candidatura approvata + consigliati\n\nServer: {server['nome']}\nAdmin: @{query.from_user.username or 'senza username'}"
        )

    elif query.data.startswith("approve_"):
        if not await require_owner_callback(query):
            return

        submission_id = query.data.replace("approve_", "")
        server = get_pending_server(submission_id)

        if not server:
            await query.edit_message_text("❌ Candidatura non trovata o già gestita.")
            return

        await publish_server(context, server)

        await query.edit_message_text(
            f"✅ Candidatura approvata\n\n🏜 {server['nome']}"
        )

        delete_pending_server(submission_id)

        await admin_log(
            context,
            f"✅ Candidatura approvata\n\nServer: {server['nome']}\nAdmin: @{query.from_user.username or 'senza username'}"
        )

    elif query.data.startswith("reject_"):
        if not await require_owner_callback(query):
            return

        submission_id = query.data.replace("reject_", "")
        server = get_pending_server(submission_id)

        if not server:
            await query.edit_message_text("❌ Candidatura non trovata o già gestita.")
            return

        await query.edit_message_text(
            f"❌ Candidatura rifiutata\n\n🏜 {server['nome']}"
        )

        delete_pending_server(submission_id)

        await admin_log(
            context,
            f"❌ Candidatura rifiutata\n\nServer: {server['nome']}\nAdmin: @{query.from_user.username or 'senza username'}"
        )


async def publish_server(context: ContextTypes.DEFAULT_TYPE, server):
    text = format_public_server_post(server)

    if not GROUP_CHAT_ID:
        return

    if server.get("image_file_id"):
        await context.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=PROMO_THREAD_ID if PROMO_THREAD_ID else None,
            photo=server["image_file_id"],
            caption=text,
            reply_markup=None
        )
    else:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=PROMO_THREAD_ID if PROMO_THREAD_ID else None,
            text=text,
            disable_web_page_preview=False
        )


async def look_server(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["looking"]["server"] = update.message.text.strip()

    tipo = context.user_data["looking"]["tipo"]

    if tipo == "player":
        question = "👤 Che tipo di player cerchi?"
    elif tipo == "fazione":
        question = "🤠 Che fazione stai cercando?"
    elif tipo == "staff":
        question = "🛡 Che ruolo staff cerchi?"
    else:
        question = "💻 Che tipo di developer cerchi?"

    await update.message.reply_text(question)

    return LOOK_ROLE


async def look_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["looking"]["ruolo"] = update.message.text.strip()

    await update.message.reply_text(
        "📜 Scrivi una breve descrizione / requisiti:"
    )

    return LOOK_DESC


async def look_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["looking"]["descrizione"] = update.message.text.strip()

    await update.message.reply_text(
        "🔗 Ora manda il link Discord di contatto:"
    )

    return LOOK_DISCORD


async def look_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    discord = clean_link(update.message.text)

    if not is_valid_discord_link(discord):
        await update.message.reply_text(
            "❌ Link Discord non valido.\n\n"
            "Sono accettati solo link invito Discord validi, per esempio:\n"
            "https://discord.gg/xxxxx\n"
            "https://discord.com/invite/xxxxx"
        )

        return LOOK_DISCORD

    context.user_data["looking"]["discord"] = discord
    data = context.user_data["looking"]

    text = format_looking_post(data)

    thread_id = PLAYER_THREAD_ID

    if data["tipo"] == "staff":
        thread_id = STAFF_THREAD_ID
    elif data["tipo"] == "developer":
        thread_id = DEV_THREAD_ID
    elif data["tipo"] in ["player", "fazione"]:
        thread_id = PLAYER_THREAD_ID

    if GROUP_CHAT_ID:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            message_thread_id=thread_id,
            text=text,
            disable_web_page_preview=False
        )

    await update.message.reply_text(
        "✅ Annuncio pubblicato nella community!"
    )

    await admin_log(
        context,
        f"👥 Nuovo annuncio pubblicato\n\nTipo: {data['tipo']}\nServer: {data['server']}\nUtente: @{update.effective_user.username or 'senza username'}"
    )

    context.user_data.clear()

    return ConversationHandler.END


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["candidate"] = {
        "nome": update.message.text.strip()
    }

    keyboard = [
        [InlineKeyboardButton("Sì", callback_data="wl_si")],
        [InlineKeyboardButton("No", callback_data="wl_no")]
    ]

    await update.message.reply_text(
        "🔐 Il server è whitelist?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return ASK_WL


async def ask_wl_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "wl_si":
        context.user_data["candidate"]["whitelist"] = "Sì"
    else:
        context.user_data["candidate"]["whitelist"] = "No"

    await query.edit_message_text("📜 Scrivi una breve descrizione del server:")

    return ASK_DESC


async def ask_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["candidate"]["descrizione"] = update.message.text.strip()

    await update.message.reply_text(
        "⚙️ Scrivi le feature principali.\n\n"
        "Esempio:\n"
        "Economia realistica, lavori, fazioni, eventi settimanali"
    )

    return ASK_FEATURES


async def ask_features(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_features = update.message.text.strip()

    features = [
        feature.strip()
        for feature in raw_features.replace("\n", ",").split(",")
        if feature.strip()
    ]

    context.user_data["candidate"]["feature"] = features

    await update.message.reply_text("🔗 Ora manda il link Discord del server:")

    return ASK_DISCORD


async def ask_discord(update: Update, context: ContextTypes.DEFAULT_TYPE):
    discord = clean_link(update.message.text)

    if not is_valid_discord_link(discord):
        await update.message.reply_text(
            "❌ Link Discord non valido.\n\n"
            "Sono accettati solo link invito Discord validi, per esempio:\n"
            "https://discord.gg/xxxxx\n"
            "https://discord.com/invite/xxxxx"
        )

        return ASK_DISCORD

    context.user_data["candidate"]["discord"] = discord

    await update.message.reply_text(
        "🖼 Vuoi aggiungere un banner al server?\n\n"
        "Formato richiesto:\n"
        "1200x400 px\n\n"
        "Invia l'immagine adesso oppure scrivi /skip per continuare senza banner."
    )

    return ASK_BANNER


async def send_candidate_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    candidate = context.user_data["candidate"]
    preview_text = f"""📨 Preview candidatura

Controlla i dati prima di inviare:

{format_public_server_post(candidate)}

Vuoi inviare questa candidatura agli admin?
"""

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Invia candidatura", callback_data="confirm_candidate"),
            InlineKeyboardButton("❌ Annulla", callback_data="cancel_candidate")
        ]
    ])

    if update.message:
        await update.message.reply_text(
            preview_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
    else:
        await update.callback_query.message.reply_text(
            preview_text,
            reply_markup=keyboard,
            disable_web_page_preview=False
        )

    return ASK_CONFIRM


async def ask_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text(
            "❌ Devi inviare un'immagine oppure scrivere /skip."
        )
        return ASK_BANNER

    photo = update.message.photo[-1]

    if photo.width != 1200 or photo.height != 400:
        await update.message.reply_text(
            "❌ Banner non valido.\n\n"
            "Formato richiesto:\n"
            "1200x400 px\n\n"
            "Invia un'altra immagine oppure scrivi /skip per continuare senza banner."
        )
        return ASK_BANNER

    context.user_data["candidate"]["image_file_id"] = photo.file_id

    return await send_candidate_preview(update, context)


async def skip_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["candidate"]["image_file_id"] = None

    return await send_candidate_preview(update, context)


async def confirm_candidate_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_candidate":
        context.user_data.clear()

        await query.edit_message_text(
            "❌ Candidatura annullata.\n\n"
            "Puoi ricominciare quando vuoi dal menu principale."
        )

        return ConversationHandler.END

    if query.data == "confirm_candidate":
        return await finalize_candidate(update, context)

    return ASK_CONFIRM


async def finalize_candidate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    candidate = context.user_data["candidate"]
    user = update.effective_user

    submission_id = (
        str(user.id)
        + "_"
        + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    )

    candidate["submitted_by_id"] = user.id
    candidate["submitted_by_username"] = user.username or "senza username"
    candidate["submitted_at"] = datetime.now(timezone.utc).isoformat()

    save_pending_server(submission_id, candidate, user)

    await query.edit_message_text(
        "✅ Candidatura inviata!\n\n"
        "Un admin controllerà la richiesta."
    )

    admin_text = f"""📨 NUOVA CANDIDATURA SERVER

👤 Utente: @{user.username or 'senza username'}
🆔 ID: {user.id}
🕒 Inviata il: {datetime.now().strftime('%d/%m/%Y %H:%M')}

{format_public_server_post(candidate)}
"""

    keyboard = [
        [
            InlineKeyboardButton("✅ Approva", callback_data=f"approve_{submission_id}"),
            InlineKeyboardButton("⭐ Approva + Consigliati", callback_data=f"approve_featured_{submission_id}")
        ],
        [
            InlineKeyboardButton("❌ Rifiuta", callback_data=f"reject_{submission_id}")
        ]
    ]

    if candidate.get("image_file_id"):
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=candidate["image_file_id"],
            caption=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=False
        )

    await admin_log(
        context,
        f"📨 Nuova candidatura ricevuta\n\nServer: {candidate['nome']}\nUtente: @{user.username or 'senza username'}\nID candidatura: {submission_id}"
    )

    context.user_data.clear()

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text("❌ Operazione annullata.")

    return ConversationHandler.END


init_db()
migrate_old_json_files()

app = ApplicationBuilder().token(TOKEN).build()

candidate_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(button, pattern="^candidate$"),
        CommandHandler(
            "start",
            start_candidate,
            filters=filters.Regex(r"^/start\\s+candidatura(?:\\s|$)")
        )
    ],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_WL: [CallbackQueryHandler(ask_wl_button, pattern="^wl_")],
        ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_desc)],
        ASK_FEATURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_features)],
        ASK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discord)],
        ASK_BANNER: [
            MessageHandler(filters.PHOTO, ask_banner),
            CommandHandler("skip", skip_banner)
        ],
        ASK_CONFIRM: [
            CallbackQueryHandler(confirm_candidate_button, pattern="^(confirm_candidate|cancel_candidate)$")
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

looking_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(button, pattern="^look_")
    ],
    states={
        LOOK_SERVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, look_server)],
        LOOK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, look_role)],
        LOOK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, look_desc)],
        LOOK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, look_discord)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("promo_message", promo_message))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
app.add_handler(CallbackQueryHandler(verify_button, pattern="^verify_"))

app.add_handler(candidate_handler)
app.add_handler(looking_handler)

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, moderate_message))

logger_message = "Bot avviato con PostgreSQL..."
try:
    print(logger_message)
except Exception:
    pass

app.run_polling()
