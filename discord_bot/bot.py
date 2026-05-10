import os
import io
import asyncio
import traceback
import aiohttp
import discord
import re

from collections import defaultdict, deque
from datetime import timedelta
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

GUILD_OBJECT = discord.Object(id=GUILD_ID)

BRAND_NAME = "RedM Italia Community"
BRAND_COLOR = 0x8B0000
SUCCESS_COLOR = 0x2ECC71
INFO_COLOR = 0x3498DB
DANGER_COLOR = 0xE74C3C
WARNING_COLOR = 0xF1C40F

ROLE_VERIFIED_KEYWORD = "verified"
ROLE_NEW_KEYWORD = "nuovo arrivato"
ROLE_CREATOR_KEYWORD = "creator"
ROLE_PARTNER_KEYWORD = "partner"

CHANNEL_LOG_KEYWORD = "admin-logs"
CHANNEL_WELCOME_KEYWORD = "benvenuti"
CHANNEL_LIVE_STREAMS_KEYWORD = "live-streams"
CHANNEL_PROMO_SERVER_KEYWORD = "promozione-server"

TICKET_CATEGORY_NAME = "🎫 | TICKET"
TICKET_CATEGORY_KEYWORD = "ticket"

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

BANNER_VERIFICA = os.path.join(ASSETS_DIR, "banner_verifica.png")
BANNER_RUOLI = os.path.join(ASSETS_DIR, "banner_ruoli.png")
BANNER_DISCORD = os.path.join(ASSETS_DIR, "banner_discord.png")
BANNER_REGOLE = os.path.join(ASSETS_DIR, "banner_regole.png")
BANNER_CREATOR_PROGRAM = os.path.join(ASSETS_DIR, "banner_creator_program.png")
BANNER_CREATOR_GUIDELINES = os.path.join(ASSETS_DIR, "banner_creator_guidelines.png")
BANNER_INVITO = os.path.join(ASSETS_DIR, "banner_invito.png")
WELCOME_BANNER = os.path.join(ASSETS_DIR, "welcome_banner.png")
LOGO_IMAGE = os.path.join(ASSETS_DIR, "logo.png")

TWITCH_STREAMERS = [
    {
        "twitch_name": "tuma_tv",
        "discord_id": 633041890111127562
    }
]

REDM_KEYWORDS = [
    "redm",
    "red dead roleplay",
    "red dead rp",
    "rdr2 rp",
    "wild west rp"
]

TICKET_STAFF_ROLE_KEYWORDS = [
    "founder",
    "admin",
    "moderatore",
    "helper"
]

SETUP_ALLOWED_ROLE_KEYWORDS = [
    "founder",
    "admin",
    "moderatore",
    "helper"
]

ticket_claims = {}
twitch_access_token = None
announced_live_streams = set()

automod_message_cache = defaultdict(lambda: deque(maxlen=10))
recent_join_times = deque(maxlen=50)
last_join_spike_log = 0

AUTOMOD_IGNORED_CHANNEL_KEYWORDS = [
    "admin-logs",
    "ticket",
    "regolamento",
    "verifica",
    "live-streams",
    "linee-guida",
    "benvenuti"
]

AUTOMOD_BLOCKED_DOMAINS = [
    "free-nitro",
    "discordnitro",
    "steamcommunit",
    "steamgift",
    "bit.ly",
    "tinyurl.com",
    "grabify",
    "iplogger",
    "linkvertise",
    "adf.ly"
]

AUTOMOD_SCAM_KEYWORDS = [
    "free nitro",
    "nitro gratis",
    "steam gift",
    "gift nitro",
    "claim nitro",
    "airdrop",
    "token grabber"
]

AUTOMOD_DUPLICATE_LIMIT = 4
AUTOMOD_DUPLICATE_WINDOW = 20

AUTOMOD_MENTION_LIMIT = 6

RAID_JOIN_LIMIT = 8
RAID_JOIN_WINDOW = 20
RAID_LOG_COOLDOWN = 120

ROLE_OPTIONS = {
    "player": {
        "label": "Player",
        "emoji": "🎮",
        "keyword": "player"
    },
    "developer": {
        "label": "Developer",
        "emoji": "💻",
        "keyword": "developer"
    },
    "mapper": {
        "label": "Mapper",
        "emoji": "🗺️",
        "keyword": "mapper"
    },
    "ui_designer": {
        "label": "UI Designer",
        "emoji": "🎨",
        "keyword": "ui designer"
    },
    "creator": {
        "label": "Creator",
        "emoji": "🎥",
        "keyword": "creator"
    }
}

TICKET_TYPES = {
    "supporto_generale": {
        "label": "Supporto Generale",
        "emoji": "🎫",
        "channel_prefix": "supporto",
        "color": INFO_COLOR
    },
    "partnership": {
        "label": "Partnership",
        "emoji": "🤝",
        "channel_prefix": "partnership",
        "color": 0x9B59B6
    },
    "promozione_server": {
        "label": "Promozione Server",
        "emoji": "⭐",
        "channel_prefix": "server",
        "color": WARNING_COLOR
    },
        "candidatura_creator": {
        "label": "Candidatura Creator",
        "emoji": "🎥",
        "channel_prefix": "creator",
        "color": BRAND_COLOR
    },
    "candidatura_staff": {
        "label": "Candidatura Staff",
        "emoji": "💼",
        "channel_prefix": "staff",
        "color": SUCCESS_COLOR
    }
}

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


def make_file(path, filename):
    if not os.path.exists(path):
        print(f"⚠️ Asset non trovato: {path}")
        return None

    return discord.File(path, filename=filename)


def apply_brand(embed, guild=None):
    embed.set_footer(text=f"{BRAND_NAME} • Sistema ufficiale")

    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    return embed


def find_role(guild, keyword):
    keyword = keyword.lower()

    for role in guild.roles:
        if keyword in role.name.lower():
            return role

    return None


def find_roles(guild, keywords):
    roles = []

    for keyword in keywords:
        role = find_role(guild, keyword)

        if role and role not in roles:
            roles.append(role)

    return roles


def find_channel(guild, keyword):
    keyword = keyword.lower()

    for channel in guild.text_channels:
        if keyword in channel.name.lower():
            return channel

    return None


def find_category(guild, keyword):
    keyword = keyword.lower()

    for category in guild.categories:
        if keyword in category.name.lower():
            return category

    return None


def clean_channel_name(name):
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"

    name = name.lower().replace(" ", "-")
    name = "".join(c for c in name if c in allowed)

    if not name:
        name = "utente"

    return name[:25]


def member_is_verified(member):
    verified_role = find_role(member.guild, ROLE_VERIFIED_KEYWORD)

    if not verified_role:
        return False

    return verified_role in member.roles


def member_is_ticket_staff(member):
    staff_roles = find_roles(member.guild, TICKET_STAFF_ROLE_KEYWORDS)

    if member.guild_permissions.manage_channels:
        return True

    return any(role in member.roles for role in staff_roles)


def member_can_use_setup_commands(member):
    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_guild:
        return True

    for role in member.roles:
        role_name = role.name.lower()

        for keyword in SETUP_ALLOWED_ROLE_KEYWORDS:
            if keyword in role_name:
                return True

    return False


def is_ticket_channel(channel):
    if not channel.topic:
        return False

    return "ticket_owner:" in channel.topic


def get_ticket_owner_id(channel):
    if not channel.topic:
        return None

    try:
        return channel.topic.split("ticket_owner:")[1].split(" ")[0]
    except Exception:
        return None
def extract_form_value(content, field_name):
    lines = content.splitlines()

    for line in lines:
        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        if key.strip().lower() == field_name.lower():
            return value.strip()

    return ""


def parse_server_promotion_form(content):
    return {
        "nome_server": extract_form_value(content, "Nome server"),
        "link_discord": extract_form_value(content, "Link Discord"),
        "descrizione": extract_form_value(content, "Descrizione"),
        "stile_server": extract_form_value(content, "Stile server"),
        "accesso": extract_form_value(content, "Accesso"),
        "lingua": extract_form_value(content, "Lingua"),
        "logo": extract_form_value(content, "Logo")
    }


def is_valid_discord_invite(link):
    link = link.strip().lower()

    return (
        link.startswith("https://discord.gg/")
        or link.startswith("https://discord.com/invite/")
    )


class ServerPromotionLinkView(discord.ui.View):
    def __init__(self, discord_link):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Entra nel Discord",
                emoji="🔗",
                style=discord.ButtonStyle.link,
                url=discord_link
            )
        )    
async def get_server_promotion_logo_file(form_message, channel, owner):
    image_attachment = None

    for attachment in form_message.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            image_attachment = attachment
            break

    if not image_attachment:
        async for message in channel.history(limit=30, oldest_first=False):
            if message.author.id != owner.id:
                continue

            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    image_attachment = attachment
                    break

            if image_attachment:
                break

    if not image_attachment:
        return None

    try:
        image_bytes = await image_attachment.read()

        return discord.File(
            io.BytesIO(image_bytes),
            filename="server_logo.png"
        )

    except Exception:
        print("❌ ERRORE LETTURA LOGO SERVER")
        traceback.print_exc()
        return None

def is_redm_stream(stream_data):
    title = stream_data.get("title", "").lower()
    game_name = stream_data.get("game_name", "").lower()
    tags = " ".join(stream_data.get("tags", [])).lower()

    combined_text = f"{title} {game_name} {tags}"

    for keyword in REDM_KEYWORDS:
        if keyword in combined_text:
            return True

    return False


async def get_or_create_ticket_category(guild):
    category = find_category(guild, TICKET_CATEGORY_KEYWORD)

    if category:
        return category

    return await guild.create_category(
        name=TICKET_CATEGORY_NAME,
        reason="Categoria ticket creata automaticamente"
    )


async def send_admin_log(
    guild,
    title,
    description,
    color=INFO_COLOR,
    file=None
):
    channel = find_channel(guild, CHANNEL_LOG_KEYWORD)

    if not channel:
        print("⚠️ Canale admin-logs non trovato.")
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    apply_brand(embed, guild)

    await channel.send(
        embed=embed,
        file=file
    )
def automod_channel_is_ignored(channel):
    if not channel:
        return True

    channel_name = channel.name.lower()

    return any(
        keyword in channel_name
        for keyword in AUTOMOD_IGNORED_CHANNEL_KEYWORDS
    )


def automod_member_is_staff(member):
    if not isinstance(member, discord.Member):
        return False

    if member.guild_permissions.manage_messages:
        return True

    if member.guild_permissions.administrator:
        return True

    return member_is_ticket_staff(member)


def extract_domains_from_message(content):
    pattern = r"(https?://[^\s]+|discord\.gg/[^\s]+)"
    matches = re.findall(pattern, content.lower())

    domains = []

    for url in matches:
        clean_url = url.replace("https://", "").replace("http://", "")
        domain = clean_url.split("/")[0]
        domains.append(domain)

    return domains


def message_contains_blocked_domain(content):
    content_lower = content.lower()
    domains = extract_domains_from_message(content_lower)

    for blocked_domain in AUTOMOD_BLOCKED_DOMAINS:
        if blocked_domain in content_lower:
            return True

        for domain in domains:
            if blocked_domain in domain:
                return True

    return False


def message_contains_scam_keyword(content):
    content_lower = content.lower()

    return any(
        keyword in content_lower
        for keyword in AUTOMOD_SCAM_KEYWORDS
    )


def normalize_message_content(content):
    return " ".join(content.lower().strip().split())


async def automod_log(guild, title, description, color=WARNING_COLOR):
    await send_admin_log(
        guild,
        title,
        description,
        color=color
    )


async def automod_timeout(member, seconds, reason):
    try:
        await member.timeout(
            timedelta(seconds=seconds),
            reason=reason
        )

        return True

    except discord.Forbidden:
        print("⚠️ AutoMod non può mettere timeout: permessi insufficienti.")
        return False

    except Exception:
        print("❌ ERRORE AUTOMOD TIMEOUT")
        traceback.print_exc()
        return False


async def automod_delete_message(message):
    try:
        await message.delete()
        return True

    except discord.Forbidden:
        print("⚠️ AutoMod non può eliminare messaggi: permessi insufficienti.")
        return False

    except Exception:
        print("❌ ERRORE AUTOMOD DELETE")
        traceback.print_exc()
        return False

async def generate_ticket_transcript(channel):
    lines = []

    lines.append(f"Transcript Ticket: #{channel.name}")
    lines.append("=" * 60)
    lines.append("")

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):
        created_at = message.created_at.strftime("%d/%m/%Y %H:%M:%S")
        content = message.content if message.content else "[embed/allegato]"

        lines.append(
            f"[{created_at}] {message.author}: {content}"
        )

    transcript_text = "\n".join(lines)

    transcript_bytes = io.BytesIO(
        transcript_text.encode("utf-8")
    )

    return discord.File(
        transcript_bytes,
        filename=f"{channel.name}-transcript.txt"
    )


async def get_twitch_access_token():
    global twitch_access_token

    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        print("⚠️ Variabili Twitch non configurate.")
        return None

    url = "https://id.twitch.tv/oauth2/token"

    params = {
        "client_id": TWITCH_CLIENT_ID,
        "client_secret": TWITCH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    print(f"❌ Errore Twitch token: {response.status} {text}")
                    return None

                data = await response.json()
                twitch_access_token = data.get("access_token")
                return twitch_access_token

    except Exception:
        print("❌ ERRORE GET TWITCH TOKEN")
        traceback.print_exc()
        return None


class LiveStreamView(discord.ui.View):
    def __init__(self, stream_url):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Guarda Live",
                emoji="🔴",
                style=discord.ButtonStyle.link,
                url=stream_url
            )
        )


async def fetch_twitch_streams():
    global twitch_access_token

    if not TWITCH_STREAMERS:
        return []

    if not twitch_access_token:
        twitch_access_token = await get_twitch_access_token()

    if not twitch_access_token:
        return []

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {twitch_access_token}"
    }

    params = []

    for streamer_data in TWITCH_STREAMERS:
        params.append(
            (
                "user_login",
                streamer_data["twitch_name"]
            )
        )

    url = "https://api.twitch.tv/helix/streams"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                params=params
            ) as response:

                if response.status == 401:
                    print("⚠️ Twitch token scaduto, rigenero token.")

                    twitch_access_token = await get_twitch_access_token()

                    if not twitch_access_token:
                        return []

                    headers["Authorization"] = (
                        f"Bearer {twitch_access_token}"
                    )

                    async with session.get(
                        url,
                        headers=headers,
                        params=params
                    ) as retry_response:

                        if retry_response.status != 200:
                            text = await retry_response.text()

                            print(
                                f"❌ Errore Twitch streams retry: "
                                f"{retry_response.status} {text}"
                            )

                            return []

                        retry_data = await retry_response.json()

                        return retry_data.get("data", [])

                if response.status != 200:
                    text = await response.text()

                    print(
                        f"❌ Errore Twitch streams: "
                        f"{response.status} {text}"
                    )

                    return []

                data = await response.json()

                return data.get("data", [])

    except Exception:
        print("❌ ERRORE FETCH TWITCH STREAMS")
        traceback.print_exc()

        return []

def member_has_role(member, keyword):
    return any(
        keyword.lower() in role.name.lower()
        for role in member.roles
    )


@tasks.loop(minutes=2)
async def twitch_live_checker():
    try:
        guild = bot.get_guild(GUILD_ID)

        if not guild:
            print("⚠️ Guild non trovata per Twitch checker.")
            return

        live_channel = find_channel(
            guild,
            CHANNEL_LIVE_STREAMS_KEYWORD
        )

        if not live_channel:
            print("⚠️ Canale live-streams non trovato.")
            return

        verified_role = find_role(
            guild,
            ROLE_VERIFIED_KEYWORD
        )

        streams = await fetch_twitch_streams()

        currently_live_redm = set()

        for stream in streams:
            streamer_login = stream.get(
                "user_login",
                ""
            ).lower()

            streamer_name = stream.get(
                "user_name",
                streamer_login
            )

            stream_title = stream.get(
                "title",
                "Live RedM Italia"
            )

            game_name = stream.get(
                "game_name",
                "RedM"
            )

            viewer_count = stream.get(
                "viewer_count",
                0
            )

            thumbnail_url = stream.get(
                "thumbnail_url",
                ""
            )

            if thumbnail_url:
                thumbnail_url = (
                    thumbnail_url
                    .replace("{width}", "1280")
                    .replace("{height}", "720")
                )

            stream_url = (
                f"https://www.twitch.tv/{streamer_login}"
            )

            streamer_config = next(
                (
                    item for item in TWITCH_STREAMERS
                    if item["twitch_name"].lower() == streamer_login
                ),
                None
            )

            creator_mention = ""

            if streamer_config:
                creator_mention = (
                    f"<@{streamer_config['discord_id']}>"
                )

            if not streamer_login:
                continue

            if not streamer_config:
                continue

            discord_member = guild.get_member(
                streamer_config["discord_id"]
            )

            if not discord_member:
                continue

            is_creator = member_has_role(
                discord_member,
                ROLE_CREATOR_KEYWORD
            )

            is_partner = member_has_role(
                discord_member,
                ROLE_PARTNER_KEYWORD
            )

            allow_live = False

            if is_partner:
                allow_live = True

            elif is_creator and is_redm_stream(stream):
                allow_live = True

            if not allow_live:

                if streamer_login in announced_live_streams:
                    announced_live_streams.discard(
                        streamer_login
                    )

                continue

            currently_live_redm.add(streamer_login)

            if streamer_login in announced_live_streams:
                continue

            role_mention = (
                verified_role.mention
                if verified_role
                else ""
            )

            embed = discord.Embed(
                title=f"🔴 {streamer_name} è ora LIVE su RedM",
                description=(
                    f"{creator_mention}\n\n"
                    "Un creator della **RedM Italia Community** "
                    "è in diretta adesso.\n\n"
                    "Clicca il pulsante qui sotto per entrare nella live."
                ),
                color=DANGER_COLOR,
                url=stream_url
            )

            embed.add_field(
                name="📌 Titolo",
                value=stream_title[:1024],
                inline=False
            )

            embed.add_field(
                name="🎮 Categoria",
                value=game_name,
                inline=True
            )

            embed.add_field(
                name="👥 Spettatori",
                value=str(viewer_count),
                inline=True
            )

            embed.add_field(
                name="🎥 Creator",
                value=creator_mention if creator_mention else streamer_name,
                inline=True
            )

            if thumbnail_url:
                embed.set_image(url=thumbnail_url)

            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            embed.set_footer(
                text=f"{BRAND_NAME} • Live System"
            )

            await live_channel.send(
                content=role_mention,
                embed=embed,
                view=LiveStreamView(stream_url),
                allowed_mentions=discord.AllowedMentions(
                    roles=True,
                    everyone=False,
                    users=True
                )
            )

            announced_live_streams.add(
                streamer_login
            )

            await send_admin_log(
                guild,
                "🔴 Live RedM pubblicata",
                (
                    f"Streamer: **{streamer_name}**\n"
                    f"Creator Discord: {creator_mention or '`Non collegato`'}\n"
                    f"Categoria: `{game_name}`\n"
                    f"Spettatori: `{viewer_count}`\n"
                    f"Titolo: `{stream_title}`\n"
                    f"Link: {stream_url}"
                ),
                color=DANGER_COLOR
            )

        offline_streamers = (
            announced_live_streams
            - currently_live_redm
        )

        for streamer_login in list(offline_streamers):
            announced_live_streams.discard(
                streamer_login
            )

    except Exception:
        print("❌ ERRORE TWITCH LIVE CHECKER")
        traceback.print_exc()


@twitch_live_checker.before_loop
async def before_twitch_live_checker():
    await bot.wait_until_ready()


def get_font(size):
    possible_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "arial.ttf"
    ]

    for path in possible_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue

    return ImageFont.load_default()


async def download_avatar_bytes(member):
    avatar_url = member.display_avatar.replace(size=256).url

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            if response.status != 200:
                return None

            return await response.read()


def make_circle_avatar(avatar_image, size):
    avatar_image = avatar_image.convert("RGBA")
    avatar_image = avatar_image.resize((size, size))

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(avatar_image, (0, 0), mask)

    return output


async def generate_welcome_card(member):
    if not os.path.exists(WELCOME_BANNER):
        print("⚠️ welcome_banner.png non trovato.")
        return None

    background = Image.open(WELCOME_BANNER).convert("RGBA")
    background = background.resize((1100, 450))

    draw = ImageDraw.Draw(background)

    avatar_bytes = await download_avatar_bytes(member)

    avatar_size = 145

    avatar_center_x = 220
    avatar_center_y = 158

    avatar_x = avatar_center_x - avatar_size // 2
    avatar_y = avatar_center_y - avatar_size // 2

    if avatar_bytes:
        avatar_image = Image.open(io.BytesIO(avatar_bytes))
        avatar = make_circle_avatar(avatar_image, avatar_size)

        glow_size = avatar_size + 34
        glow = Image.new("RGBA", (glow_size, glow_size), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)

        glow_draw.ellipse(
            (10, 10, glow_size - 10, glow_size - 10),
            fill=(180, 0, 0, 120)
        )

        glow = glow.filter(ImageFilter.GaussianBlur(10))

        background.paste(
            glow,
            (
                avatar_center_x - glow_size // 2,
                avatar_center_y - glow_size // 2
            ),
            glow
        )

        border_size = avatar_size + 10
        border = Image.new("RGBA", (border_size, border_size), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border)

        border_draw.ellipse(
            (0, 0, border_size - 1, border_size - 1),
            outline=(200, 0, 0, 255),
            width=5
        )

        border_draw.ellipse(
            (7, 7, border_size - 8, border_size - 8),
            outline=(255, 255, 255, 210),
            width=2
        )

        background.paste(
            border,
            (
                avatar_center_x - border_size // 2,
                avatar_center_y - border_size // 2
            ),
            border
        )

        background.paste(
            avatar,
            (avatar_x, avatar_y),
            avatar
        )


    output = io.BytesIO()
    background.save(output, format="PNG")
    output.seek(0)

    return discord.File(
        output,
        filename="welcome_card.png"
    )


async def send_welcome_message(member):
    guild = member.guild
    channel = find_channel(guild, CHANNEL_WELCOME_KEYWORD)

    if not channel:
        print("⚠️ Canale benvenuti non trovato.")
        return

    embed = discord.Embed(
        title="🌅 Nuovo membro nella community",
        description=(
            f"Benvenuto {member.mention} in **{BRAND_NAME}**.\n\n"
            "Completa la verifica per accedere a tutte le sezioni del server."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="📌 Primi passi",
        value=(
            "• Leggi il regolamento\n"
            "• Completa la verifica\n"
            "• Scegli il tuo ruolo\n"
            "• Partecipa alla community"
        ),
        inline=False
    )

    apply_brand(embed, guild)

    welcome_card = await generate_welcome_card(member)

    if welcome_card:
        embed.set_image(url="attachment://welcome_card.png")

        await channel.send(
            content=f"🤠 Benvenuto {member.mention}!",
            file=welcome_card,
            embed=embed
        )
    else:
        file = make_file(BANNER_DISCORD, "banner_discord.png")

        if file:
            embed.set_image(url="attachment://banner_discord.png")

            await channel.send(
                content=f"🤠 Benvenuto {member.mention}!",
                file=file,
                embed=embed
            )
        else:
            await channel.send(
                content=f"🤠 Benvenuto {member.mention}!",
                embed=embed
            )


class RolePickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(self, interaction, role_key):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            return

        role_data = ROLE_OPTIONS.get(role_key)

        if not role_data:
            return

        role = find_role(guild, role_data["keyword"])

        if not role:
            await interaction.response.send_message(
                f"❌ Ruolo `{role_data['label']}` non trovato.",
                ephemeral=True
            )
            return

        try:
            if role in member.roles:
                await member.remove_roles(
                    role,
                    reason="Ruolo rimosso tramite role picker"
                )

                await interaction.response.send_message(
                    f"❌ Ruolo rimosso: {role_data['emoji']} **{role.name}**",
                    ephemeral=True
                )

            else:
                await member.add_roles(
                    role,
                    reason="Ruolo assegnato tramite role picker"
                )

                await interaction.response.send_message(
                    f"✅ Ruolo assegnato: {role_data['emoji']} **{role.name}**",
                    ephemeral=True
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Errore permessi: il bot non può assegnare questo ruolo.",
                ephemeral=True
            )

        except Exception:
            print("❌ ERRORE ROLE PICKER")
            traceback.print_exc()

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Errore imprevisto durante l’assegnazione del ruolo.",
                    ephemeral=True
                )

    @discord.ui.button(
        label="Player",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_player"
    )
    async def player_button(self, interaction, button):
        await self.toggle_role(interaction, "player")

    @discord.ui.button(
        label="Developer",
        emoji="💻",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_developer"
    )
    async def developer_button(self, interaction, button):
        await self.toggle_role(interaction, "developer")

    @discord.ui.button(
        label="Mapper",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_mapper"
    )
    async def mapper_button(self, interaction, button):
        await self.toggle_role(interaction, "mapper")

    @discord.ui.button(
        label="UI Designer",
        emoji="🎨",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_ui_designer"
    )
    async def ui_designer_button(self, interaction, button):
        await self.toggle_role(interaction, "ui_designer")

    @discord.ui.button(
        label="Creator",
        emoji="🎥",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_creator"
    )
    async def creator_button(self, interaction, button):
        await self.toggle_role(interaction, "creator")


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verificami",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="redm_verify_button"
    )
    async def verify_button(self, interaction, button):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            return

        verified_role = find_role(guild, ROLE_VERIFIED_KEYWORD)
        new_role = find_role(guild, ROLE_NEW_KEYWORD)

        if not verified_role:
            await interaction.response.send_message(
                "❌ Ruolo Verified non trovato.",
                ephemeral=True
            )
            return

        try:
            if verified_role not in member.roles:
                await member.add_roles(
                    verified_role,
                    reason="Verifica completata"
                )

            if new_role and new_role in member.roles:
                await member.remove_roles(
                    new_role,
                    reason="Utente verificato"
                )

            embed = discord.Embed(
                title="✅ Verifica completata",
                description=(
                    f"Benvenuto in **{BRAND_NAME}**, {member.mention}.\n\n"
                    "Ora hai accesso alla community.\n"
                    "Puoi scegliere il ruolo che ti rappresenta usando il pannello ruoli."
                ),
                color=SUCCESS_COLOR
            )

            apply_brand(embed, guild)

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            await send_admin_log(
                guild,
                "✅ Utente verificato",
                f"Utente: {member.mention}\nID: `{member.id}`",
                color=SUCCESS_COLOR
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Errore permessi: il bot non può assegnare il ruolo Verified.",
                ephemeral=True
            )

        except Exception:
            print("❌ ERRORE VERIFICA")
            traceback.print_exc()

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Errore imprevisto durante la verifica.",
                    ephemeral=True
                )


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Prendi in carico",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="redm_ticket_claim"
    )
    async def claim_ticket(self, interaction, button):
        guild = interaction.guild
        member = interaction.user
        channel = interaction.channel

        if not guild or not isinstance(member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not is_ticket_channel(channel):
            await interaction.response.send_message(
                "❌ Questo canale non sembra essere un ticket valido.",
                ephemeral=True
            )
            return

        if not member_is_ticket_staff(member):
            await interaction.response.send_message(
                "❌ Solo lo staff può prendere in carico i ticket.",
                ephemeral=True
            )
            return

        claimed_by = ticket_claims.get(channel.id)

        if claimed_by:
            claimed_member = guild.get_member(claimed_by)
            claimed_text = claimed_member.mention if claimed_member else f"`{claimed_by}`"

            await interaction.response.send_message(
                f"⚠️ Questo ticket è già stato preso in carico da {claimed_text}.",
                ephemeral=True
            )
            return

        ticket_claims[channel.id] = member.id

        embed = discord.Embed(
            title="📌 Ticket preso in carico",
            description=f"{member.mention} ha preso in carico questo ticket.",
            color=INFO_COLOR
        )

        apply_brand(embed, guild)

        await channel.send(embed=embed)

        await send_admin_log(
            guild,
            "📌 Ticket preso in carico",
            f"Staff: {member.mention}\nCanale: `{channel.name}`",
            color=INFO_COLOR
        )

        await interaction.response.send_message(
            "✅ Ticket preso in carico.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Chiudi Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="redm_ticket_close"
    )
    async def close_ticket(self, interaction, button):
        guild = interaction.guild
        member = interaction.user
        channel = interaction.channel

        if not guild or not isinstance(member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not is_ticket_channel(channel):
            await interaction.response.send_message(
                "❌ Questo canale non sembra essere un ticket valido.",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(channel)

        is_owner = owner_id == str(member.id)
        is_staff = member_is_ticket_staff(member)

        if not is_owner and not is_staff:
            await interaction.response.send_message(
                "❌ Non puoi chiudere questo ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Chiusura ticket tra 5 secondi...",
            ephemeral=False
        )

        try:
            transcript_file = await generate_ticket_transcript(channel)

            await send_admin_log(
                guild,
                "🔒 Ticket chiuso",
                (
                    f"Canale: `{channel.name}`\n"
                    f"Chiuso da: {member.mention}\n"
                    f"Owner ID: `{owner_id}`"
                ),
                color=DANGER_COLOR,
                file=transcript_file
            )

        except Exception:
            print("⚠️ ERRORE TRANSCRIPT/LOG CHIUSURA")
            traceback.print_exc()

        await asyncio.sleep(5)

        try:
            ticket_claims.pop(channel.id, None)

            await channel.delete(
                reason=f"Ticket chiuso da {member}"
            )

        except Exception:
            print("❌ ERRORE ELIMINAZIONE TICKET")
            traceback.print_exc()



class CreatorApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Approva Creator",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="redm_creator_approve"
    )
    async def approve_creator(self, interaction, button):
        guild = interaction.guild
        staff_member = interaction.user
        channel = interaction.channel

        if not guild or not isinstance(staff_member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not member_is_ticket_staff(staff_member):
            await interaction.response.send_message(
                "❌ Solo lo staff può approvare i creator.",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(channel)

        if not owner_id:
            await interaction.response.send_message(
                "❌ Proprietario ticket non trovato.",
                ephemeral=True
            )
            return

        target_member = guild.get_member(int(owner_id))

        if not target_member:
            await interaction.response.send_message(
                "❌ Utente non trovato nel server.",
                ephemeral=True
            )
            return

        creator_role = find_role(guild, "creator")

        if not creator_role:
            await interaction.response.send_message(
                "❌ Ruolo Creator non trovato.",
                ephemeral=True
            )
            return

        try:
            if creator_role not in target_member.roles:
                await target_member.add_roles(
                    creator_role,
                    reason=f"Creator approvato da {staff_member}"
                )

            embed = discord.Embed(
                title="✅ Creator approvato",
                description=(
                    f"{target_member.mention} è stato approvato "
                    f"nel **Creator Program** di **{BRAND_NAME}**.\n\n"
                    "Ora può accedere alle sezioni dedicate ai creator."
                ),
                color=SUCCESS_COLOR
            )

            apply_brand(embed, guild)

            await channel.send(embed=embed)

            await send_admin_log(
                guild,
                "✅ Creator approvato",
                (
                    f"Utente: {target_member.mention}\n"
                    f"Staff: {staff_member.mention}\n"
                    f"Ticket: {channel.mention}"
                ),
                color=SUCCESS_COLOR
            )

            await interaction.response.send_message(
                "✅ Creator approvato e ruolo assegnato.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Non posso assegnare il ruolo Creator. "
                "Controlla che il ruolo del bot sia sopra al ruolo Creator.",
                ephemeral=True
            )

        except Exception:
            print("❌ ERRORE APPROVAZIONE CREATOR")
            traceback.print_exc()

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Errore durante l’approvazione creator.",
                    ephemeral=True
                )

    @discord.ui.button(
        label="Rifiuta Creator",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="redm_creator_reject"
    )
    async def reject_creator(self, interaction, button):
        guild = interaction.guild
        staff_member = interaction.user
        channel = interaction.channel

        if not guild or not isinstance(staff_member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not member_is_ticket_staff(staff_member):
            await interaction.response.send_message(
                "❌ Solo lo staff può rifiutare i creator.",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(channel)

        target_text = "Utente non trovato"

        if owner_id:
            target_member = guild.get_member(int(owner_id))

            if target_member:
                target_text = target_member.mention
            else:
                target_text = f"`{owner_id}`"

        embed = discord.Embed(
            title="❌ Candidatura creator rifiutata",
            description=(
                f"La candidatura creator di {target_text} "
                "non è stata approvata.\n\n"
                "Lo staff può lasciare una motivazione nel ticket "
                "prima della chiusura."
            ),
            color=DANGER_COLOR
        )

        apply_brand(embed, guild)

        await channel.send(embed=embed)

        await send_admin_log(
            guild,
            "❌ Creator rifiutato",
            (
                f"Utente: {target_text}\n"
                f"Staff: {staff_member.mention}\n"
                f"Ticket: {channel.mention}"
            ),
            color=DANGER_COLOR
        )

        await interaction.response.send_message(
            "❌ Candidatura creator rifiutata.",
            ephemeral=True
        )
class ServerPromotionApplicationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Approva Server",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="redm_server_promotion_approve"
    )
    async def approve_server(self, interaction, button):
        guild = interaction.guild
        staff_member = interaction.user
        channel = interaction.channel

        if not guild or not isinstance(staff_member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not member_is_ticket_staff(staff_member):
            await interaction.response.send_message(
                "❌ Solo lo staff può approvare una promozione server.",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(channel)

        if not owner_id:
            await interaction.response.send_message(
                "❌ Proprietario ticket non trovato.",
                ephemeral=True
            )
            return

        owner = guild.get_member(int(owner_id))

        if not owner:
            await interaction.response.send_message(
                "❌ Utente proprietario del ticket non trovato.",
                ephemeral=True
            )
            return

        form_message = None

        async for message in channel.history(limit=50, oldest_first=False):
            if message.author.id == owner.id and "Nome server:" in message.content:
                form_message = message
                break

        if not form_message:
            await interaction.response.send_message(
                "❌ Modulo promozione server non trovato. "
                "L'utente deve compilare il form nel ticket.",
                ephemeral=True
            )
            return

        form_data = parse_server_promotion_form(form_message.content)

        nome_server = form_data["nome_server"]
        link_discord = form_data["link_discord"]
        descrizione = form_data["descrizione"]
        stile_server = form_data["stile_server"]
        accesso = form_data["accesso"]
        lingua = form_data["lingua"]

        if not nome_server or not link_discord or not descrizione:
            await interaction.response.send_message(
                "❌ Il form è incompleto. Devono esserci almeno Nome server, Link Discord e Descrizione.",
                ephemeral=True
            )
            return

        if not is_valid_discord_invite(link_discord):
            await interaction.response.send_message(
                "❌ Link Discord non valido. Deve essere `https://discord.gg/...` oppure `https://discord.com/invite/...`.",
                ephemeral=True
            )
            return

        promo_channel = find_channel(
            guild,
            CHANNEL_PROMO_SERVER_KEYWORD
        )

        if not promo_channel:
            await interaction.response.send_message(
                "❌ Canale promozione-server non trovato.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🌐 {nome_server}",
            description=descrizione,
            color=BRAND_COLOR,
            url=link_discord
        )

        embed.add_field(
            name="🎮 Stile server",
            value=stile_server if stile_server else "Non specificato",
            inline=True
        )

        embed.add_field(
            name="🔐 Accesso",
            value=accesso if accesso else "Non specificato",
            inline=True
        )

        embed.add_field(
            name="🌍 Lingua",
            value=lingua if lingua else "Non specificata",
            inline=True
        )

        embed.add_field(
            name="🤝 Proposto da",
            value=owner.mention,
            inline=False
        )

        embed.add_field(
            name="📌 Come entrare",
            value="Clicca il bottone qui sotto per entrare nel Discord del server.",
            inline=False
        )

        logo_file = await get_server_promotion_logo_file(
        form_message,
        channel,
        owner
)

        if logo_file:
            embed.set_thumbnail(url="attachment://server_logo.png")

        embed.set_footer(
            text=f"{BRAND_NAME} • Server Promotion System"
        )

        if logo_file:
            await promo_channel.send(
                embed=embed,
                file=logo_file,
                view=ServerPromotionLinkView(link_discord)
            )
        else:
            await promo_channel.send(
                embed=embed,
                view=ServerPromotionLinkView(link_discord)
            )

        approved_embed = discord.Embed(
            title="✅ Server approvato",
            description=(
                f"Il server **{nome_server}** è stato pubblicato in {promo_channel.mention}."
            ),
            color=SUCCESS_COLOR
        )

        apply_brand(approved_embed, guild)

        await channel.send(embed=approved_embed)

        await send_admin_log(
            guild,
            "✅ Server promosso",
            (
                f"Server: **{nome_server}**\n"
                f"Proposto da: {owner.mention}\n"
                f"Approvato da: {staff_member.mention}\n"
                f"Canale: {promo_channel.mention}\n"
                f"Link: {link_discord}"
            ),
            color=SUCCESS_COLOR
        )

        await interaction.response.send_message(
            "✅ Server approvato e pubblicato.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Rifiuta Server",
        emoji="❌",
        style=discord.ButtonStyle.danger,
        custom_id="redm_server_promotion_reject"
    )
    async def reject_server(self, interaction, button):
        guild = interaction.guild
        staff_member = interaction.user
        channel = interaction.channel

        if not guild or not isinstance(staff_member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not member_is_ticket_staff(staff_member):
            await interaction.response.send_message(
                "❌ Solo lo staff può rifiutare una promozione server.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="❌ Promozione server rifiutata",
            description=(
                "La richiesta di promozione server non è stata approvata.\n\n"
                "Lo staff può lasciare una motivazione nel ticket prima della chiusura."
            ),
            color=DANGER_COLOR
        )

        apply_brand(embed, guild)

        await channel.send(embed=embed)

        await send_admin_log(
            guild,
            "❌ Promozione server rifiutata",
            (
                f"Staff: {staff_member.mention}\n"
                f"Ticket: {channel.mention}"
            ),
            color=DANGER_COLOR
        )

        await interaction.response.send_message(
            "❌ Promozione server rifiutata.",
            ephemeral=True
        )
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = []

        for key, data in TICKET_TYPES.items():
            options.append(
                discord.SelectOption(
                    label=data["label"],
                    emoji=data["emoji"],
                    value=key
                )
            )

        super().__init__(
            placeholder="Seleziona il tipo di ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="redm_ticket_select"
        )

    async def callback(self, interaction):
        try:
            guild = interaction.guild
            member = interaction.user

            if not guild or not isinstance(member, discord.Member):
                return

            if not member_is_verified(member):
                await interaction.response.send_message(
                    "❌ Devi essere verificato per aprire un ticket.",
                    ephemeral=True
                )
                return

            for channel in guild.text_channels:
                if channel.topic and f"ticket_owner:{member.id}" in channel.topic:
                    await interaction.response.send_message(
                        f"⚠️ Hai già un ticket aperto: {channel.mention}",
                        ephemeral=True
                    )
                    return

            category = await get_or_create_ticket_category(guild)
            staff_roles = find_roles(guild, TICKET_STAFF_ROLE_KEYWORDS)
            bot_member = guild.me

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(
                    view_channel=False
                ),
                member: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )
            }

            for role in staff_roles:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

            if bot_member:
                overwrites[bot_member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    manage_channels=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True
                )

            ticket_type = self.values[0]
            ticket_data = TICKET_TYPES[ticket_type]

            channel_name = (
                f"ticket-"
                f"{ticket_data['channel_prefix']}-"
                f"{clean_channel_name(member.name)}"
            )

            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"ticket_owner:{member.id} ticket_type:{ticket_type}",
                reason=f"Ticket aperto da {member}"
            )

            embed = discord.Embed(
                title=f"{ticket_data['emoji']} Ticket aperto",
                description=(
                    f"{member.mention}, il ticket è stato creato correttamente.\n\n"
                    "Descrivi la tua richiesta in modo chiaro.\n"
                    "Lo staff ti risponderà appena possibile."
                ),
                color=ticket_data["color"]
            )

            embed.add_field(
                name="Strumenti staff",
                value=(
                    "📌 **Prendi in carico** — assegna il ticket a uno staffer\n"
                    "🔒 **Chiudi Ticket** — chiude il ticket e genera il transcript"
                ),
                inline=False
            )

            apply_brand(embed, guild)

            staff_mentions = " ".join(role.mention for role in staff_roles)

            await channel.send(
                content=f"{member.mention} {staff_mentions}".strip(),
                embed=embed,
                view=TicketControlView()
            )

            if ticket_type == "candidatura_creator":
                creator_embed = discord.Embed(
                    title="🎥 Candidatura Creator",
                    description=(
                        "Compila il modulo qui sotto.\n\n"
                        "• Nome creator:\n"
                        "• Piattaforma:\n"
                        "• Link canale:\n"
                        "• Tipo contenuti:\n"
                        "• Da quanto crei contenuti:\n"
                        "• Perché vuoi entrare nel Creator Program:"
                    ),
                    color=BRAND_COLOR
                )

                apply_brand(
                    creator_embed,
                    interaction.guild
                )

                await channel.send(
                    content=interaction.user.mention,
                    embed=creator_embed,
                    view=CreatorApplicationView()
                )

            if ticket_type == "promozione_server":
                server_promo_embed = discord.Embed(
                    title="🌐 Promozione Server",
                    description=(
                        "Compila il modulo qui sotto copiandolo e rispondendo in questo ticket.\n\n"
                        "```text\n"
                        "Nome server:\n"
                        "Link Discord:\n"
                        "Descrizione:\n"
                        "Stile server:\n"
                        "Accesso:\n"
                        "Lingua:\n"
                        "```\n"
                        "**Suggerimenti:**\n"
                        "• Nome server: Es. WildWest RP\n"
                        "• Link Discord: https://discord.gg/tuoserver\n"
                        "• Descrizione: breve descrizione del server\n"
                        "• Stile server: roleplay realistico, western classico, roleplay immersivo\n"
                        "• Accesso: Whitelist / No Whitelist\n"
                        "• Lingua: Italiano\n"
                        "• Logo: allega l'immagine del logo insieme al modulo"
                    ),
                    color=BRAND_COLOR
                )

                apply_brand(
                    server_promo_embed,
                    interaction.guild
                )

                await channel.send(
                    content=interaction.user.mention,
                    embed=server_promo_embed,
                    view=ServerPromotionApplicationView()
                )

            await send_admin_log(
                guild,
                "🎫 Ticket aperto",
                (
                    f"Utente: {member.mention}\n"
                    f"Tipo: `{ticket_data['label']}`\n"
                    f"Canale: {channel.mention}"
                ),
                color=ticket_data["color"]
            )

            await interaction.response.send_message(
                f"✅ Ticket creato: {channel.mention}",
                ephemeral=True
            )

        except Exception:
            print("❌ ERRORE APERTURA TICKET")
            traceback.print_exc()

            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Errore durante la creazione del ticket.",
                    ephemeral=True
                )


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot online: {bot.user}")
    print("━━━━━━━━━━━━━━━━━━")

    bot.add_view(VerifyView())
    bot.add_view(RolePickerView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())
    bot.add_view(CreatorApplicationView())
    bot.add_view(ServerPromotionApplicationView())

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=BRAND_NAME
        )
    )

    if not twitch_live_checker.is_running():
        twitch_live_checker.start()
        print("✅ Twitch Live Checker avviato.")

    try:
        print("📌 Comandi locali registrati:")

        for command in bot.tree.get_commands():
            print(f"   /{command.name}")

        bot.tree.copy_global_to(guild=GUILD_OBJECT)

        synced = await bot.tree.sync(guild=GUILD_OBJECT)

        print(f"✅ Slash commands sincronizzati: {len(synced)}")

        for command in synced:
            print(f"   /{command.name}")

    except Exception:
        print("❌ ERRORE SYNC SLASH COMMANDS")
        traceback.print_exc()


@bot.event
async def on_member_join(member):
    global last_join_spike_log

    try:
        now = discord.utils.utcnow().timestamp()
        recent_join_times.append(now)

        recent_joins = [
            join_time for join_time in recent_join_times
            if now - join_time <= RAID_JOIN_WINDOW
        ]

        if len(recent_joins) >= RAID_JOIN_LIMIT:
            if now - last_join_spike_log >= RAID_LOG_COOLDOWN:
                last_join_spike_log = now

                await send_admin_log(
                    member.guild,
                    "🚨 Possibile join spike rilevato",
                    (
                        f"Sono entrati **{len(recent_joins)} utenti** "
                        f"negli ultimi **{RAID_JOIN_WINDOW} secondi**.\n\n"
                        "Nessuna azione automatica eseguita.\n"
                        "Il server è in monitoraggio."
                    ),
                    color=WARNING_COLOR
                )

        new_role = find_role(member.guild, ROLE_NEW_KEYWORD)

        if new_role:
            await member.add_roles(
                new_role,
                reason="Nuovo membro entrato"
            )

        await send_welcome_message(member)

        await send_admin_log(
            member.guild,
            "👋 Nuovo membro",
            (
                f"Utente: {member.mention}\n"
                f"ID: `{member.id}`"
            ),
            color=INFO_COLOR
        )

    except Exception:
        print("❌ ERRORE MEMBER JOIN")
        traceback.print_exc()

@bot.event
async def on_message(message):
    try:
        if message.author.bot:
            return

        if not message.guild:
            return

        if not isinstance(message.author, discord.Member):
            return

        member = message.author
        channel = message.channel

        if automod_channel_is_ignored(channel):
            await bot.process_commands(message)
            return

        if automod_member_is_staff(member):
            await bot.process_commands(message)
            return

        content = message.content or ""

        if not content.strip():
            await bot.process_commands(message)
            return

        total_mentions = (
            len(message.mentions)
            + len(message.role_mentions)
        )

        if message.mention_everyone or total_mentions >= AUTOMOD_MENTION_LIMIT:
            await automod_delete_message(message)

            await automod_timeout(
                member,
                300,
                "AutoMod: mention spam"
            )

            await automod_log(
                message.guild,
                "🚨 AutoMod: mention spam",
                (
                    f"Utente: {member.mention}\n"
                    f"Canale: {channel.mention}\n"
                    f"Mentions: `{total_mentions}`\n"
                    f"Messaggio eliminato."
                ),
                color=DANGER_COLOR
            )

            return

        if (
            message_contains_blocked_domain(content)
            or message_contains_scam_keyword(content)
        ):
            await automod_delete_message(message)

            await automod_timeout(
                member,
                600,
                "AutoMod: link o contenuto sospetto"
            )

            await automod_log(
                message.guild,
                "🚨 AutoMod: contenuto sospetto",
                (
                    f"Utente: {member.mention}\n"
                    f"Canale: {channel.mention}\n"
                    f"Contenuto:\n```{content[:900]}```"
                ),
                color=DANGER_COLOR
            )

            return

        normalized_content = normalize_message_content(content)

        if normalized_content:
            now = discord.utils.utcnow().timestamp()

            automod_message_cache[member.id].append(
                {
                    "content": normalized_content,
                    "timestamp": now,
                    "channel_id": channel.id
                }
            )

            recent_same_messages = [
                item for item in automod_message_cache[member.id]
                if (
                    item["content"] == normalized_content
                    and now - item["timestamp"] <= AUTOMOD_DUPLICATE_WINDOW
                )
            ]

            if len(recent_same_messages) >= AUTOMOD_DUPLICATE_LIMIT:
                await automod_delete_message(message)

                await automod_timeout(
                    member,
                    60,
                    "AutoMod: messaggi duplicati ripetuti"
                )

                await automod_log(
                    message.guild,
                    "⚠️ AutoMod: flood duplicato",
                    (
                        f"Utente: {member.mention}\n"
                        f"Canale: {channel.mention}\n"
                        f"Ripetizioni: `{len(recent_same_messages)}`\n"
                        f"Messaggio:\n```{content[:900]}```"
                    ),
                    color=WARNING_COLOR
                )

                return

        await bot.process_commands(message)

    except Exception:
        print("❌ ERRORE AUTOMOD ON_MESSAGE")
        traceback.print_exc()

        try:
            await bot.process_commands(message)
        except Exception:
            pass


@bot.tree.command(
    name="ping",
    description="Test bot"
)
async def ping(interaction):
    await interaction.response.send_message(
        "🏓 Pong! Bot online.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_verifica",
    description="Invia pannello verifica"
)
async def setup_verifica(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="✅ Verifica Community",
        description=(
            f"Benvenuto in **{BRAND_NAME}**.\n\n"
            "Per accedere a tutte le sezioni del server premi il pulsante qui sotto.\n\n"
            "Dopo la verifica potrai:\n"
            "• accedere ai canali principali\n"
            "• scegliere il tuo ruolo\n"
            "• partecipare alla community\n\n"
            "⚠️ Rispetta il regolamento e mantieni un comportamento corretto."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="Accesso community",
        value="Premi **✅ Verificami** per completare l’accesso.",
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(BANNER_VERIFICA, "banner_verifica.png")

    if file:
        embed.set_image(url="attachment://banner_verifica.png")

        await interaction.channel.send(
            file=file,
            embed=embed,
            view=VerifyView()
        )
    else:
        await interaction.channel.send(
            embed=embed,
            view=VerifyView()
        )

    await interaction.response.send_message(
        "✅ Pannello verifica pubblicato.",
        ephemeral=True
    )


@bot.tree.command(
    name="ruoli",
    description="Invia pannello ruoli"
)
async def ruoli(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎭 Scegli il tuo ruolo",
        description=(
            "Personalizza la tua esperienza nella community.\n\n"
            "Puoi selezionare anche più ruoli.\n"
            "Se clicchi di nuovo su un ruolo già assegnato, verrà rimosso."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="Ruoli disponibili",
        value=(
            "🎮 **Player** — giochi sui server RedM\n"
            "💻 **Developer** — sviluppi script, sistemi o framework\n"
            "🗺️ **Mapper** — crei mappe, MLO o ambientazioni\n"
            "🎨 **UI Designer** — lavori su UI, grafiche o UX\n"
            "🎥 **Creator** — crei contenuti, clip o live"
        ),
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(BANNER_RUOLI, "banner_ruoli.png")

    if file:
        embed.set_image(url="attachment://banner_ruoli.png")

        await interaction.channel.send(
            file=file,
            embed=embed,
            view=RolePickerView()
        )
    else:
        await interaction.channel.send(
            embed=embed,
            view=RolePickerView()
        )

    await interaction.response.send_message(
        "✅ Pannello ruoli pubblicato.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_ticket",
    description="Invia pannello ticket"
)
async def setup_ticket(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 Centro Supporto RedM Italia",
        description=(
            f"Benvenuto nel centro supporto ufficiale di **{BRAND_NAME}**.\n\n"
            "Seleziona dal menu qui sotto il tipo di richiesta più adatto.\n"
            "Lo staff riceverà il tuo ticket in un canale privato."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="Categorie disponibili",
        value=(
            "🎫 **Supporto Generale** — dubbi, problemi Discord o richieste generiche\n"
            "🤝 **Partnership** — collaborazioni con server, community o creator\n"
            "⭐ **Promozione Server** — richiesta promozione server RedM\n"
            "💼 **Candidatura Staff** — richiesta per entrare nello staff"
        ),
        inline=False
    )

    embed.add_field(
        name="Regole",
        value=(
            "• Non aprire ticket inutili\n"
            "• Non aprire ticket duplicati\n"
            "• Scrivi in modo chiaro e rispettoso\n"
            "• Attendi risposta dallo staff senza spam"
        ),
        inline=False
    )

    apply_brand(embed, interaction.guild)

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "✅ Pannello ticket pubblicato.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_welcome",
    description="Invia pannello welcome"
)
async def setup_welcome(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🌅 Benvenuto nella RedM Italia Community",
        description=(
            "Questa è la community italiana dedicata a **RedM**.\n\n"
            "Qui puoi trovare player, developer, mapper, UI designer e creator.\n"
            "Completa la verifica, scegli il tuo ruolo e inizia a partecipare."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="📌 Come iniziare",
        value=(
            "1. Leggi il regolamento\n"
            "2. Completa la verifica\n"
            "3. Scegli il tuo ruolo\n"
            "4. Partecipa alla community"
        ),
        inline=False
    )

    embed.add_field(
        name="🤠 Spirito community",
        value="Rispetto, passione e collaborazione.",
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(WELCOME_BANNER, "welcome_banner.png")

    if file:
        embed.set_image(url="attachment://welcome_banner.png")

        await interaction.channel.send(
            file=file,
            embed=embed
        )
    else:
        await interaction.channel.send(
            embed=embed
        )

    await interaction.response.send_message(
        "✅ Pannello welcome pubblicato.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_regole",
    description="Invia pannello regolamento"
)
async def setup_regole(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🤠 Regole della Community",
        description=(
            f"Benvenuto nel regolamento ufficiale di **{BRAND_NAME}**.\n\n"
            "Per mantenere una community sana, rispettosa e professionale,\n"
            "tutti i membri devono seguire queste regole."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="1️⃣ Rispetto Community",
        value=(
            "• Rispetta tutti i membri\n"
            "• No flame o tossicità\n"
            "• Mantieni un clima civile"
        ),
        inline=False
    )

    embed.add_field(
        name="2️⃣ Spam & Promo",
        value=(
            "• Vietato spam o flood\n"
            "• Promo solo nei canali dedicati\n"
            "• Evita contenuti inutili"
        ),
        inline=False
    )

    embed.add_field(
        name="3️⃣ Voice & RP",
        value=(
            "• Mantieni comportamento corretto\n"
            "• Evita troll e disturbatori\n"
            "• Rispetta creator e staff"
        ),
        inline=False
    )

    embed.add_field(
        name="4️⃣ Staff & Sicurezza",
        value=(
            "• Lo staff può intervenire\n"
            "• Segui le indicazioni della moderazione\n"
            "• Evita comportamenti dannosi"
        ),
        inline=False
    )

    embed.add_field(
        name="🌅 Filosofia Community",
        value=(
            "Rispetto • Passione • Community\n\n"
            "Insieme costruiamo la migliore community RedM italiana."
        ),
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(BANNER_REGOLE, "banner_regole.png")

    if file:
        embed.set_image(url="attachment://banner_regole.png")

        await interaction.channel.send(
            file=file,
            embed=embed
        )
    else:
        await interaction.channel.send(
            embed=embed
        )

    await interaction.response.send_message(
        "✅ Pannello regolamento pubblicato.",
        ephemeral=True
    )
    
@bot.tree.command(
    name="setup_creator",
    description="Invia pannello creator program"
)
async def setup_creator(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎥 Programma Creator RedM Italia",
        description=(
            "Sei uno streamer o creator RedM?\n\n"
            "La RedM Italia Community supporta creator italiani "
            "attraverso visibilità, live alerts e partnership community.\n\n"
            "Apri un ticket per candidarti al programma creator ufficiale."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="✅ Benefici Creator",
        value=(
            "• Accesso Creator Hub\n"
            "• Promozione live automatiche\n"
            "• Partnership creator\n"
            "• Showcase clip e highlights\n"
            "• Accesso eventi community"
        ),
        inline=False
    )

    embed.add_field(
        name="📋 Requisiti",
        value=(
            "• Contenuti RedM\n"
            "• Community friendly\n"
            "• Nessun contenuto tossico\n"
            "• Attività costante\n"
            "• Rispetto regolamento"
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ Importante",
        value=(
            "Il ruolo 🎥 Creator NON viene assegnato automaticamente.\n\n"
            "Ogni candidatura viene controllata manualmente "
            "dallo staff."
        ),
        inline=False
    )

    embed.add_field(
        name="🎫 Come candidarsi",
        value=(
            "Apri un ticket Creator "
            "nel pannello supporto."
        ),
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(
        BANNER_CREATOR_PROGRAM,
        "banner_creator_program.png"
    )

    if file:
        embed.set_image(
            url="attachment://banner_creator_program.png"
        )

        await interaction.channel.send(
            file=file,
            embed=embed
        )
    else:
        await interaction.channel.send(
            embed=embed
        )

    await interaction.response.send_message(
        "✅ Pannello creator pubblicato.",
        ephemeral=True
    )
@bot.tree.command(
    name="setup_invito",
    description="Invia pannello invito community"
)
async def setup_invito(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    invite_url = "https://discord.gg/hXZ8fv52zz"

    embed = discord.Embed(
        title="🌅 Invito RedM Italia Community",
        description=(
            "Condividi la community italiana dedicata al mondo **RedM**.\n\n"
            "Qui trovi player, developer, mapper, creator e server owner "
            "uniti dalla stessa passione.\n\n"
            f"🔗 **Invito ufficiale:**\n{invite_url}"
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="🤠 Community",
        value=(
            "• Player RedM\n"
            "• Developer\n"
            "• Mapper\n"
            "• Creator\n"
            "• Server Owner"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Condividi il server",
        value=(
            "Invita amici, creator e community interessate al mondo RedM.\n\n"
            "**Rispetto • Passione • Community**"
        ),
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(
        BANNER_INVITO,
        "banner_invito.png"
    )

    if file:
        embed.set_image(
            url="attachment://banner_invito.png"
        )

        await interaction.channel.send(
            file=file,
            embed=embed
        )
    else:
        await interaction.channel.send(
            embed=embed
        )

    await interaction.response.send_message(
        "✅ Pannello invito pubblicato.",
        ephemeral=True
    )

@bot.tree.command(
    name="setup_creator_guidelines",
    description="Invia linee guida creator"
)
async def setup_creator_guidelines(interaction):
    member = interaction.user

    if not isinstance(member, discord.Member):
        return

    if not member_can_use_setup_commands(member):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📜 Linee Guida Creator",
        description=(
            "Benvenuto nel **Creator Program ufficiale** "
            "della RedM Italia Community.\n\n"

            "Queste linee guida definiscono "
            "comportamento, qualità e responsabilità "
            "dei creator presenti nella community."
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="✅ Requisiti",
        value=(
            "• Contenuti legati a RedM\n"
            "• Attività costante\n"
            "• Community friendly\n"
            "• Rispetto regolamento server\n"
            "• Nessun comportamento tossico"
        ),
        inline=False
    )

    embed.add_field(
        name="🚫 Contenuti vietati",
        value=(
            "• Cheat / mod menu\n"
            "• Hate speech\n"
            "• Leak o drama tossico\n"
            "• NSFW estremo\n"
            "• Promozioni scam"
        ),
        inline=False
    )

    embed.add_field(
        name="🤝 Partnership Creator",
        value=(
            "Le partnership vengono valutate "
            "manualmente dallo staff.\n\n"

            "Attività, qualità contenuti e "
            "impatto nella community influenzano "
            "la valutazione."
        ),
        inline=False
    )

    embed.add_field(
        name="⚠️ Revoca ruolo Creator",
        value=(
            "Il ruolo Creator può essere rimosso "
            "in caso di:\n"
            "• inattività\n"
            "• tossicità\n"
            "• violazioni regolamento\n"
            "• comportamento dannoso"
        ),
        inline=False
    )

    embed.add_field(
        name="🎥 Visibilità Creator",
        value=(
            "I creator approvati possono ottenere:\n"
            "• live automatiche\n"
            "• showcase community\n"
            "• clip highlights\n"
            "• partnership ufficiali"
        ),
        inline=False
    )

    apply_brand(embed, interaction.guild)

    file = make_file(
        BANNER_CREATOR_GUIDELINES,
        "banner_creator_guidelines.png"
    )

    if file:
        embed.set_image(
            url="attachment://banner_creator_guidelines.png"
        )

        await interaction.channel.send(
            file=file,
            embed=embed
        )

    else:
        await interaction.channel.send(
            embed=embed
        )

    await interaction.response.send_message(
        "✅ Linee guida creator pubblicate.",
        ephemeral=True
    )

bot.run(DISCORD_TOKEN)