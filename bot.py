import os
import re
import json
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "391476319"))
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
PROMO_THREAD_ID = int(os.getenv("PROMO_THREAD_ID", "0"))

BOT_USERNAME = "redmhub_ita_bot"

ASK_NAME, ASK_WL, ASK_DESC, ASK_FEATURES, ASK_DISCORD = range(5)

FEATURED_FILE = "featured_servers.json"

pending_servers = {}
user_warnings = {}

BAD_WORDS = [
    "mongolo", "ritardato", "handicappato", "frocio", "negro",
    "zingaro", "server di merda", "server merda", "fai schifo",
    "killati", "ammazzati"
]

ALLOWED_LINKS = [
    "discord.gg", "discord.com", "youtube.com", "youtu.be",
    "tiktok.com", "t.me", "telegram.me"
]

servers = {
    "wildlands": {
        "nome": "Wildlands Italia",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Roleplay immersivo", "Community italiana", "Sistema whitelist"],
        "discord": "https://discord.gg/wildlandsita",
        "image": "wildlands.jpg",
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "streets": {
        "nome": "Streets of Saints",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano.",
        "feature": ["Roleplay", "Community attiva", "Esperienza immersiva"],
        "discord": "https://discord.gg/streetsofsaints",
        "image": "streets.png",
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "madwest": {
        "nome": "Mad West",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Roleplay Far West", "Whitelist attiva", "Community italiana"],
        "discord": "https://discord.gg/E3gYt2EuTH",
        "image": "madwest.png",
        "badge": "⭐ SERVER CONSIGLIATO"
    },
    "newhope": {
        "nome": "1886 New Hope",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Ambientazione 1886", "Roleplay realistico", "Community attiva"],
        "discord": "https://discord.gg/ZdYQk7NCNV",
        "image": "newhope.png",
        "badge": "⭐ SERVER CONSIGLIATO"
    }
   "westworld": {
    "nome": "West World 2.0",
    "whitelist": "Sì",
    "descrizione": "Server RedM italiano whitelist.",
    "feature": ["Roleplay immersivo", "Community italiana", "Sistema whitelist", "Eventi e interazioni tra player"],
    "discord": "https://discord.gg/8PTeBBzvk",
    "image": None,
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


def load_featured_servers():
    if not os.path.exists(FEATURED_FILE):
        return {}

    try:
        with open(FEATURED_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_featured_servers(data):
    with open(FEATURED_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


featured_servers = load_featured_servers()


def make_featured_key(name):
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
    all_servers.update(featured_servers)
    return all_servers


def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Server consigliati", callback_data="server_list")],
        [InlineKeyboardButton("🤝 Partnership", callback_data="partnership")],
        [InlineKeyboardButton("📨 Candidatura server", callback_data="candidate")],
        [InlineKeyboardButton("📢 Pubblicizza server", callback_data="promo")],
        [InlineKeyboardButton("📜 Regole", callback_data="regole")],
        [InlineKeyboardButton("🧰 Pannello admin", callback_data="admin_panel")]
    ])


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


async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE, reason):
    user = update.effective_user
    chat_id = update.effective_chat.id
    key = f"{chat_id}_{user.id}"

    user_warnings[key] = user_warnings.get(key, 0) + 1
    warns = user_warnings[key]

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

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🚨 Moderazione\n\n"
            f"Gruppo: {update.effective_chat.title}\n"
            f"Utente: @{user.username or 'senza username'}\n"
            f"ID: {user.id}\n"
            f"Motivo: {reason}\n"
            f"Warn: {warns}/3"
        )
    )

    if warns >= 3:
        until_date = datetime.now(timezone.utc) + timedelta(minutes=10)

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔇 {user.mention_html()} è stato mutato per 10 minuti.",
                parse_mode="HTML"
            )

            user_warnings[key] = 0

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
    if context.args and context.args[0] == "candidatura":
        context.user_data.clear()

        await update.message.reply_text(
            "📨 Candidatura server\n\n"
            "Scrivi il nome del server:"
        )

        return ASK_NAME

    await update.message.reply_text(
        "🤠 RedM Hub Italia\n\n"
        "La community italiana dedicata ai server RedM.\n\n"
        "Scegli una sezione:",
        reply_markup=home_keyboard()
    )


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
            reply_markup=home_keyboard()
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

        image = server.get("image")

        if image and os.path.exists(image):
            await query.message.reply_photo(
                photo=open(image, "rb"),
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.message.reply_text(
                caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=False
            )

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
        keyboard = [
            [InlineKeyboardButton("⭐ Gestisci consigliati", callback_data="manage_featured")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "🧰 Pannello Admin\n\n"
            f"📨 Candidature in attesa: {len(pending_servers)}\n"
            f"⭐ Server consigliati aggiunti: {len(featured_servers)}\n"
            f"🚨 Sistema moderazione: attivo",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "manage_featured":
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
        featured_key = query.data.replace("remove_featured_", "")

        if featured_key not in featured_servers:
            await query.edit_message_text(
                "❌ Server non trovato.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Torna admin", callback_data="admin_panel")]
                ])
            )
            return

        server_name = featured_servers[featured_key]["nome"]

        del featured_servers[featured_key]
        save_featured_servers(featured_servers)

        await query.edit_message_text(
            f"❌ Server rimosso dai consigliati\n\n🏜 {server_name}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Torna admin", callback_data="admin_panel")]
            ])
        )

    elif query.data.startswith("approve_featured_"):
        submission_id = query.data.replace("approve_featured_", "")
        server = pending_servers.get(submission_id)

        if not server:
            await query.edit_message_text("❌ Candidatura non trovata o già gestita.")
            return

        server["badge"] = "⭐ SERVER CONSIGLIATO"
        server["image"] = None

        featured_key = make_featured_key(server["nome"])
        featured_servers[featured_key] = server
        save_featured_servers(featured_servers)

        text = format_public_server_post(server)

        if GROUP_CHAT_ID:
            kwargs = {
                "chat_id": GROUP_CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            }

            if PROMO_THREAD_ID:
                kwargs["message_thread_id"] = PROMO_THREAD_ID

            await context.bot.send_message(**kwargs)

        await query.edit_message_text(
            f"⭐ Candidatura approvata e aggiunta ai consigliati\n\n🏜 {server['nome']}"
        )

        del pending_servers[submission_id]

    elif query.data.startswith("approve_"):
        submission_id = query.data.replace("approve_", "")
        server = pending_servers.get(submission_id)

        if not server:
            await query.edit_message_text("❌ Candidatura non trovata o già gestita.")
            return

        text = format_public_server_post(server)

        if GROUP_CHAT_ID:
            kwargs = {
                "chat_id": GROUP_CHAT_ID,
                "text": text,
                "disable_web_page_preview": False
            }

            if PROMO_THREAD_ID:
                kwargs["message_thread_id"] = PROMO_THREAD_ID

            await context.bot.send_message(**kwargs)

        await query.edit_message_text(
            f"✅ Candidatura approvata\n\n🏜 {server['nome']}"
        )

        del pending_servers[submission_id]

    elif query.data.startswith("reject_"):
        submission_id = query.data.replace("reject_", "")
        server = pending_servers.get(submission_id)

        if not server:
            await query.edit_message_text("❌ Candidatura non trovata o già gestita.")
            return

        await query.edit_message_text(
            f"❌ Candidatura rifiutata\n\n🏜 {server['nome']}"
        )

        del pending_servers[submission_id]


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
    discord = update.message.text.strip()

    if "discord.gg" not in discord and "discord.com" not in discord:
        await update.message.reply_text(
            "❌ Link Discord non valido.\n\n"
            "Manda un link tipo:\n"
            "https://discord.gg/xxxxx"
        )

        return ASK_DISCORD

    candidate = context.user_data["candidate"]
    candidate["discord"] = discord

    submission_id = (
        str(update.effective_user.id)
        + "_"
        + str(update.message.message_id)
    )

    pending_servers[submission_id] = candidate

    await update.message.reply_text(
        "✅ Candidatura inviata!\n\n"
        "Un admin controllerà la richiesta."
    )

    admin_text = f"""📨 NUOVA CANDIDATURA SERVER

👤 Utente: @{update.effective_user.username or 'senza username'}

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

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=False
    )

    context.user_data.clear()

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text("❌ Candidatura annullata.")

    return ConversationHandler.END


app = ApplicationBuilder().token(TOKEN).build()

candidate_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(button, pattern="^candidate$"),
        CommandHandler("start", start)
    ],
    states={
        ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_WL: [CallbackQueryHandler(ask_wl_button, pattern="^wl_")],
        ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_desc)],
        ASK_FEATURES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_features)],
        ASK_DISCORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discord)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("promo_message", promo_message))
app.add_handler(candidate_handler)
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, moderate_message))

print("Bot avviato...")
app.run_polling()
