# RedM Bot

Bot per la community "RedM Italia" — include integrazioni Discord e Telegram per ticketing, welcome, automod, e pubblicazione server.

## Release v1.0-prelaunch

- Tag: `v1.0-prelaunch`
- Data: 2026-05-12
- Note:
  - Centralizzato il logging (console + file rotante)
  - Validazione esplicita delle variabili d'ambiente critiche all'avvio
  - Migliorata la gestione Twitch (disabilitazione del checker se credenziali mancanti)
  - Eliminati `print()` inconsistenti e sostituiti con logger
  - Aggiunto `CHANGELOG.md` con dettagli di rilascio

## Eseguire

Imposta le variabili d'ambiente richieste e poi avvia i bot:

Discord:

```bash
export DISCORD_TOKEN=...
export GUILD_ID=...
python -m discord_bot.bot
```

Telegram:

```bash
export TOKEN=...
export DATABASE_URL=...
python -m telegram_bot.bot
```
