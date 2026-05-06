# AGGIUNGI QUESTO DENTRO async def button(...)

    elif query.data == "manage_featured":

        if len(featured_servers) == 0:
            await query.edit_message_text(
                "⭐ Nessun server consigliato aggiunto."
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

        keyboard.append([
            InlineKeyboardButton(
                "⬅️ Torna admin",
                callback_data="admin_panel"
            )
        ])

        await query.edit_message_text(
            "⭐ Gestisci server consigliati\n\n"
            "Seleziona un server da rimuovere:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    elif query.data.startswith("remove_featured_"):

        featured_key = query.data.replace("remove_featured_", "")

        if featured_key not in featured_servers:
            await query.edit_message_text(
                "❌ Server non trovato."
            )
            return

        server_name = featured_servers[featured_key]["nome"]

        del featured_servers[featured_key]

        save_featured_servers(featured_servers)

        await query.edit_message_text(
            f"❌ Server rimosso dai consigliati\n\n"
            f"🏜 {server_name}"
        )
