import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "391476319"))

GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
PROMO_THREAD_ID = os.getenv("PROMO_THREAD_ID")

BOT_USERNAME = "redmhub_ita_bot"

if GROUP_CHAT_ID:
    GROUP_CHAT_ID = int(GROUP_CHAT_ID)

if PROMO_THREAD_ID:
    PROMO_THREAD_ID = int(PROMO_THREAD_ID)

ASK_NAME, ASK_WL, ASK_DESC, ASK_FEATURES, ASK_DISCORD = range(5)

pending_servers = {}

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
}

partners = {
    "server_partner": {
        "titolo": "🌟 Server Partner",
        "descrizione": "Server RedM selezionati come partner ufficiali della community.",
        "items": [
            "Wildlands Italia",
            "1886 New Hope"
        ]
    },
    "creator_partner": {
        "titolo": "🎥 Creator Partner",
        "descrizione": "Creator e streamer che supportano la community RedM italiana.",
        "items": [
            "Disponibile prossimamente"
        ]
    },
    "sponsor_partner": {
        "titolo": "📢 Sponsor",
        "descrizione": "Spazi dedicati a sponsor, collaborazioni e progetti in evidenza.",
        "items": [
            "Slot sponsor disponibile"
        ]
    }
}


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
{server.get('badge', '🏜 SERVER REDM')}
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
        keyboard = [
            [InlineKeyboardButton("🏜 Wildlands Italia", callback_data="wildlands")],
            [InlineKeyboardButton("🏜 Streets of Saints", callback_data="streets")],
            [InlineKeyboardButton("🏜 Mad West", callback_data="madwest")],
            [InlineKeyboardButton("🏜 1886 New Hope", callback_data="newhope")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "⭐ Server consigliati\n\nSeleziona un server:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data in servers:
        server = servers[query.data]
        caption = format_premium_card(server)

        keyboard = [
            [InlineKeyboardButton("🔗 Entra nel Discord", url=server["discord"])],
            [InlineKeyboardButton("⬅️ Torna ai server", callback_data="server_list")]
        ]

        await query.message.reply_photo(
            photo=open(server["image"], "rb"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
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
        await query.edit_message_text(
            "🧰 Pannello Admin\n\n"
            f"📨 Candidature in attesa: {len(pending_servers)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
            ])
        )

    elif query.data.startswith("approve_"):
        submission_id = query.data.replace("approve_", "")
        server = pending_servers.get(submission_id)

        if not server:
            await query.edit_message_text(
                "❌ Candidatura non trovata o già gestita."
            )
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
            await query.edit_message_text(
                "❌ Candidatura non trovata o già gestita."
            )
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

    await query.edit_message_text(
        "📜 Scrivi una breve descrizione del server:"
    )

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

    await update.message.reply_text(
        "🔗 Ora manda il link Discord del server:"
    )

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

    await update.message.reply_text(
        "❌ Candidatura annullata."
    )

    return ConversationHandler.END


app = ApplicationBuilder().token(TOKEN).build()

candidate_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(button, pattern="^candidate$"),
        CommandHandler("start", start)
    ],
    states={
        ASK_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)
        ],
        ASK_WL: [
            CallbackQueryHandler(ask_wl_button, pattern="^wl_")
        ],
        ASK_DESC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_desc)
        ],
        ASK_FEATURES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_features)
        ],
        ASK_DISCORD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_discord)
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel)
    ],
)

app.add_handler(CommandHandler("test", test))
app.add_handler(CommandHandler("promo_message", promo_message))
app.add_handler(candidate_handler)
app.add_handler(CallbackQueryHandler(button))

print("Bot avviato...")
app.run_polling()
