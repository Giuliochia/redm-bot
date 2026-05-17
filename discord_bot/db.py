import logging

import asyncpg

logger = logging.getLogger("redm_bot")

pool: asyncpg.Pool | None = None


async def init(dsn: str):
    global pool
    pool = await asyncpg.create_pool(dsn)
    await _create_tables()
    logger.info("Database connesso e tabelle verificate.")


async def close():
    global pool
    if pool:
        await pool.close()
        pool = None


async def _create_tables():
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ticket_claims (
                channel_id  BIGINT PRIMARY KEY,
                staff_id    BIGINT NOT NULL,
                claimed_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS announced_streams (
                streamer_login  TEXT PRIMARY KEY,
                announced_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                id          SERIAL PRIMARY KEY,
                user_id     BIGINT NOT NULL,
                guild_id    BIGINT NOT NULL,
                reason      TEXT NOT NULL,
                staff_id    BIGINT NOT NULL,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS twitch_streamers (
                twitch_name TEXT PRIMARY KEY,
                discord_id  BIGINT NOT NULL
            )
        """)


# ── Ticket Claims ──────────────────────────────────────────────────────────────

async def get_ticket_claim(channel_id: int) -> int | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT staff_id FROM ticket_claims WHERE channel_id = $1",
            channel_id
        )
        return row["staff_id"] if row else None


async def set_ticket_claim(channel_id: int, staff_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ticket_claims (channel_id, staff_id)
            VALUES ($1, $2)
            ON CONFLICT (channel_id) DO UPDATE SET staff_id = $2
            """,
            channel_id, staff_id
        )


async def delete_ticket_claim(channel_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM ticket_claims WHERE channel_id = $1",
            channel_id
        )


# ── Announced Streams ──────────────────────────────────────────────────────────

async def get_announced_streams() -> set[str]:
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT streamer_login FROM announced_streams")
        return {row["streamer_login"] for row in rows}


async def add_announced_stream(streamer_login: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO announced_streams (streamer_login) VALUES ($1) ON CONFLICT DO NOTHING",
            streamer_login
        )


async def remove_announced_stream(streamer_login: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM announced_streams WHERE streamer_login = $1",
            streamer_login
        )


# ── Warns ──────────────────────────────────────────────────────────────────────

async def add_warn(user_id: int, guild_id: int, reason: str, staff_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO warns (user_id, guild_id, reason, staff_id)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, guild_id, reason, staff_id
        )


async def get_warns(user_id: int, guild_id: int) -> list:
    async with pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT id, reason, staff_id, created_at
            FROM warns
            WHERE user_id = $1 AND guild_id = $2
            ORDER BY created_at
            """,
            user_id, guild_id
        )


async def count_warns(user_id: int, guild_id: int) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM warns WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id
        )


async def clear_warns(user_id: int, guild_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM warns WHERE user_id = $1 AND guild_id = $2",
            user_id, guild_id
        )


# ── Twitch Streamers ───────────────────────────────────────────────────────────

async def get_twitch_streamers() -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT twitch_name, discord_id FROM twitch_streamers"
        )
        return [
            {"twitch_name": row["twitch_name"], "discord_id": row["discord_id"]}
            for row in rows
        ]


async def add_twitch_streamer(twitch_name: str, discord_id: int):
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO twitch_streamers (twitch_name, discord_id)
            VALUES ($1, $2)
            ON CONFLICT (twitch_name) DO UPDATE SET discord_id = $2
            """,
            twitch_name, discord_id
        )


async def remove_twitch_streamer(twitch_name: str) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM twitch_streamers WHERE twitch_name = $1",
            twitch_name
        )
        return result == "DELETE 1"


async def streamer_exists(twitch_name: str) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM twitch_streamers WHERE twitch_name = $1",
            twitch_name
        )
        return row is not None
