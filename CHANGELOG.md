# Changelog

All notable changes to this project will be documented in this file.

## [v1.0-prelaunch] - 2026-05-12
### Added
- Centralized logging (console + rotating file handler)
- Explicit environment validation and exit on missing critical vars (`DISCORD_TOKEN`, `GUILD_ID`, `TOKEN`, `DATABASE_URL`)
- Twitch checker disabled automatically if Twitch credentials are missing
- Converted inconsistent `print()` calls to structured logging

### Misc
- Tag `v1.0-prelaunch` created and pushed
