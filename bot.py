import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

servers = {
    "wildlands": {
        "nome": "Wildlands Italia",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Roleplay immersivo", "Community italiana", "Sistema whitelist"],
        "discord": "https://discord.gg/wildlandsita",
        "image": "wildlands.jpg"
    },
    "streets": {
        "nome": "Streets of Saints",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano.",
        "feature": ["Roleplay", "Community attiva", "Esperienza immersiva"],
        "discord": "https://discord.gg/streetsofsaints",
        "image": "streets.png"
    },
    "madwest": {
        "nome": "Mad West",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Roleplay Far West", "Whitelist attiva", "Community italiana"],
        "discord": "https://discord.gg/E3gYt2EuTH",
        "image": "madwest.png"
    },
    "newhope": {
        "nome": "1886 New Hope",
        "whitelist": "Sì",
        "descrizione": "Server RedM italiano whitelist.",
        "feature": ["Ambientazione 1886", "Roleplay realistico", "Community attiva"],
        "discord": "https://discord.gg/ZdYQk7NCNV",
        "image": "newhope.png"
    }
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Server consigliati", callback_data="server_list")],
        [InlineKeyboardButton("📢 Pubblicizza server", callback_data="promo")],
        [InlineKeyboardButton("📜 Regole", callback_data="regole")]
    ]

    await update.message.reply_text(
        "🤠 Benvenuto su RedM Server Hub Italia\n\nScegli cosa vuoi fare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "server_list":
        keyboard = [
            [InlineKeyboardButton("🏜 Wildlands Italia", callback_data="wildlands")],
            [InlineKeyboardButton("🏜 Streets of Saints", callback_data="streets")],
            [InlineKeyboardButton("🏜 Mad West", callback_data="madwest")],
            [InlineKeyboardButton("🏜 1886 New Hope", callback_data="newhope")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "⭐ Server consigliati:\n\nSeleziona un server:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data in servers:
        server = servers[query.data]
        features = "\n".join([f"- {f}" for f in server["feature"]])

        caption = f"""🏜 {server['nome']}

🔐 Whitelist: {server['whitelist']}

📜 Descrizione:
{server['descrizione']}

⚙️ Feature:
{features}

🔗 Discord:
{server['discord']}
"""

        keyboard = [
            [InlineKeyboardButton("🔗 Entra nel Discord", url=server["discord"])],
            [InlineKeyboardButton("⬅️ Torna ai server", callback_data="server_list")]
        ]

        await query.message.reply_photo(
            photo=open(server["image"], "rb"),
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "promo":
        keyboard = [
            [InlineKeyboardButton("📢 Vai al gruppo", url="https://t.me/redmitacommunity")],
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "📢 Vuoi pubblicizzare il tuo server?\n\nEntra nella community e usa il topic:\n\n📢 PROMO SERVER\n\nSegui il formato fissato 👍",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "regole":
        keyboard = [
            [InlineKeyboardButton("⬅️ Indietro", callback_data="home")]
        ]

        await query.edit_message_text(
            "📜 REGOLE\n\n- Niente spam\n- Usa i topic corretti\n- Rispetta gli altri\n- Max 1 promo ogni 48 ore",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "home":
        keyboard = [
            [InlineKeyboardButton("⭐ Server consigliati", callback_data="server_list")],
            [InlineKeyboardButton("📢 Pubblicizza server", callback_data="promo")],
            [InlineKeyboardButton("📜 Regole", callback_data="regole")]
        ]

        await query.edit_message_text(
            "🤠 RedM Server Hub Italia\n\nScegli cosa vuoi fare:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))

print("Bot avviato...")
app.run_polling()