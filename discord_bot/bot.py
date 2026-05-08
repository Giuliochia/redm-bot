# =========================
# REDM ITALIA BOT
# =========================

import os
import io
import time
import asyncio
import traceback
import discord

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# =========================
# CONFIG
# =========================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

ROLE_VERIFIED_KEYWORD = "verified"
ROLE_NEW_KEYWORD = "nuovo arrivato"

CHANNEL_LOG_KEYWORD = "admin-logs"

TICKET_CATEGORY_NAME = "🎫 | TICKET"
TICKET_CATEGORY_KEYWORD = "ticket"

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

GUILD_OBJECT = discord.Object(id=GUILD_ID)

# =========================
# CACHE
# =========================

ticket_claims = {}
ticket_cooldowns = {}

# =========================
# ROLE OPTIONS
# =========================

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

# =========================
# TICKET TYPES
# =========================

TICKET_TYPES = {
    "supporto_generale": {
        "label": "Supporto Generale",
        "emoji": "🎫",
        "channel_prefix": "supporto",
        "color": 0x3498db
    },

    "partnership": {
        "label": "Partnership",
        "emoji": "🤝",
        "channel_prefix": "partnership",
        "color": 0x9b59b6
    },

    "promozione_server": {
        "label": "Promozione Server",
        "emoji": "⭐",
        "channel_prefix": "server",
        "color": 0xf1c40f
    },

    "candidatura_staff": {
        "label": "Candidatura Staff",
        "emoji": "💼",
        "channel_prefix": "staff",
        "color": 0x2ecc71
    }
}

# =========================
# DISCORD INTENTS
# =========================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

# =========================
# UTILS
# =========================

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

        if role:
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

    return name[:25]


def member_is_verified(member):
    verified_role = find_role(member.guild, ROLE_VERIFIED_KEYWORD)

    if not verified_role:
        return False

    return verified_role in member.roles


def member_is_ticket_staff(member):
    staff_roles = find_roles(
        member.guild,
        TICKET_STAFF_ROLE_KEYWORDS
    )

    return any(role in member.roles for role in staff_roles)


def member_can_use_setup_commands(member):

    if member.guild_permissions.administrator:
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
        return channel.topic.split(
            "ticket_owner:"
        )[1].split(" ")[0]

    except Exception:
        return None


async def get_or_create_ticket_category(guild):

    category = find_category(
        guild,
        TICKET_CATEGORY_KEYWORD
    )

    if category:
        return category

    return await guild.create_category(
        name=TICKET_CATEGORY_NAME
    )


async def send_admin_log(
    guild,
    title,
    description,
    color=0x3498db,
    file=None
):
    channel = find_channel(
        guild,
        CHANNEL_LOG_KEYWORD
    )

    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    embed.set_footer(
        text="RedM Italia Community • Admin Logs"
    )

    await channel.send(
        embed=embed,
        file=file
    )

# =========================
# TRANSCRIPT
# =========================

async def generate_ticket_transcript(channel):

    lines = []

    lines.append(
        f"Transcript Ticket: #{channel.name}"
    )

    lines.append("=" * 50)
    lines.append("")

    messages = []

    async for message in channel.history(
        limit=None,
        oldest_first=True
    ):
        messages.append(message)

    for message in messages:

        created_at = message.created_at.strftime(
            "%d/%m/%Y %H:%M:%S"
        )

        content = message.content

        if not content:
            content = "[embed/allegato]"

        line = (
            f"[{created_at}] "
            f"{message.author} : "
            f"{content}"
        )

        lines.append(line)

    transcript_text = "\n".join(lines)

    transcript_bytes = io.BytesIO(
        transcript_text.encode("utf-8")
    )

    return discord.File(
        transcript_bytes,
        filename=f"{channel.name}-transcript.txt"
    )

# =========================
# ROLE PICKER
# =========================

class RolePickerView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(
        self,
        interaction,
        role_key
    ):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(
            member,
            discord.Member
        ):
            return

        role_data = ROLE_OPTIONS.get(role_key)

        if not role_data:
            return

        role = find_role(
            guild,
            role_data["keyword"]
        )

        if not role:
            return

        try:

            if role in member.roles:

                await member.remove_roles(role)

                await interaction.response.send_message(
                    f"❌ Ruolo rimosso: {role.name}",
                    ephemeral=True
                )

            else:

                await member.add_roles(role)

                await interaction.response.send_message(
                    f"✅ Ruolo assegnato: {role.name}",
                    ephemeral=True
                )

        except Exception:
            traceback.print_exc()

    @discord.ui.button(
        label="Player",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="role_player"
    )
    async def player_button(
        self,
        interaction,
        button
    ):
        await self.toggle_role(
            interaction,
            "player"
        )

    @discord.ui.button(
        label="Developer",
        emoji="💻",
        style=discord.ButtonStyle.primary,
        custom_id="role_developer"
    )
    async def developer_button(
        self,
        interaction,
        button
    ):
        await self.toggle_role(
            interaction,
            "developer"
        )

    @discord.ui.button(
        label="Mapper",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="role_mapper"
    )
    async def mapper_button(
        self,
        interaction,
        button
    ):
        await self.toggle_role(
            interaction,
            "mapper"
        )

    @discord.ui.button(
        label="UI Designer",
        emoji="🎨",
        style=discord.ButtonStyle.primary,
        custom_id="role_ui"
    )
    async def ui_button(
        self,
        interaction,
        button
    ):
        await self.toggle_role(
            interaction,
            "ui_designer"
        )

    @discord.ui.button(
        label="Creator",
        emoji="🎥",
        style=discord.ButtonStyle.primary,
        custom_id="role_creator"
    )
    async def creator_button(
        self,
        interaction,
        button
    ):
        await self.toggle_role(
            interaction,
            "creator"
        )

# =========================
# VERIFY
# =========================

class VerifyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Verificami",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="verify_button"
    )
    async def verify_button(
        self,
        interaction,
        button
    ):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(
            member,
            discord.Member
        ):
            return

        verified_role = find_role(
            guild,
            ROLE_VERIFIED_KEYWORD
        )

        new_role = find_role(
            guild,
            ROLE_NEW_KEYWORD
        )

        if verified_role:
            await member.add_roles(verified_role)

        if new_role and new_role in member.roles:
            await member.remove_roles(new_role)

        await interaction.response.send_message(
            "✅ Verifica completata.",
            ephemeral=True
        )

# =========================
# TICKET CONTROLS
# =========================

class TicketControlView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Prendi in carico",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="ticket_claim"
    )
    async def claim_ticket(
        self,
        interaction,
        button
    ):

        member = interaction.user
        channel = interaction.channel

        if not isinstance(
            member,
            discord.Member
        ):
            return

        if not isinstance(
            channel,
            discord.TextChannel
        ):
            return

        if not member_is_ticket_staff(member):

            await interaction.response.send_message(
                "❌ Solo lo staff può claimare ticket.",
                ephemeral=True
            )
            return

        claimed_by = ticket_claims.get(channel.id)

        if claimed_by:

            await interaction.response.send_message(
                "⚠️ Ticket già preso in carico.",
                ephemeral=True
            )
            return

        ticket_claims[channel.id] = member.id

        embed = discord.Embed(
            title="📌 Ticket preso in carico",
            description=(
                f"{member.mention} "
                f"ha preso in carico il ticket."
            ),
            color=0x3498db
        )

        await channel.send(embed=embed)

        await send_admin_log(
            member.guild,
            "📌 Ticket claimato",
            (
                f"Staff: {member.mention}\n"
                f"Canale: {channel.name}"
            )
        )

        await interaction.response.send_message(
            "✅ Ticket preso in carico.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Chiudi Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="ticket_close"
    )
    async def close_ticket(
        self,
        interaction,
        button
    ):

        guild = interaction.guild
        member = interaction.user
        channel = interaction.channel

        if not guild:
            return

        if not isinstance(
            member,
            discord.Member
        ):
            return

        if not isinstance(
            channel,
            discord.TextChannel
        ):
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

            transcript_file = await generate_ticket_transcript(
                channel
            )

            await send_admin_log(
                guild,
                "🔒 Ticket chiuso",
                (
                    f"Canale: {channel.name}\n"
                    f"Chiuso da: {member.mention}"
                ),
                color=0xe74c3c,
                file=transcript_file
            )

        except Exception:
            traceback.print_exc()

        await asyncio.sleep(5)

        try:

            ticket_claims.pop(
                channel.id,
                None
            )

            await channel.delete()

        except Exception:
            traceback.print_exc()

# =========================
# TICKET SELECT
# =========================

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
            options=options,
            custom_id="ticket_select"
        )

    async def callback(
        self,
        interaction
    ):

        try:

            guild = interaction.guild
            member = interaction.user

            if not guild or not isinstance(
                member,
                discord.Member
            ):
                return

            if not member_is_verified(member):

                await interaction.response.send_message(
                    "❌ Devi essere verificato.",
                    ephemeral=True
                )
                return

            category = await get_or_create_ticket_category(
                guild
            )

            staff_roles = find_roles(
                guild,
                TICKET_STAFF_ROLE_KEYWORDS
            )

            overwrites = {
                guild.default_role:
                    discord.PermissionOverwrite(
                        view_channel=False
                    ),

                member:
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        read_message_history=True
                    )
            }

            for role in staff_roles:

                overwrites[role] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True,
                        read_message_history=True
                    )
                )

            bot_member = guild.me

            if bot_member:

                overwrites[bot_member] = (
                    discord.PermissionOverwrite(
                        view_channel=True,
                        send_messages=True,
                        manage_channels=True,
                        read_message_history=True
                    )
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
                topic=f"ticket_owner:{member.id}"
            )

            embed = discord.Embed(
                title=f"{ticket_data['emoji']} Ticket aperto",
                description=(
                    f"{member.mention}, "
                    f"ticket creato correttamente.\n\n"
                    f"Attendi una risposta dello staff."
                ),
                color=ticket_data["color"]
            )

            await channel.send(
                content=" ".join(
                    role.mention
                    for role in staff_roles
                ),
                embed=embed,
                view=TicketControlView()
            )

            await send_admin_log(
                guild,
                "🎫 Ticket aperto",
                (
                    f"Utente: {member.mention}\n"
                    f"Tipo: {ticket_data['label']}\n"
                    f"Canale: {channel.name}"
                ),
                color=ticket_data["color"]
            )

            await interaction.response.send_message(
                f"✅ Ticket creato: {channel.mention}",
                ephemeral=True
            )

        except Exception:
            traceback.print_exc()

# =========================
# TICKET PANEL
# =========================

class TicketPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            TicketSelect()
        )

# =========================
# EVENTS
# =========================

@bot.event
async def on_ready():

    print("━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot online: {bot.user}")
    print("━━━━━━━━━━━━━━━━━━")

    bot.add_view(VerifyView())
    bot.add_view(RolePickerView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())

    synced = await bot.tree.sync(
        guild=GUILD_OBJECT
    )

    print(
        f"✅ Slash commands sincronizzati: "
        f"{len(synced)}"
    )

@bot.event
async def on_member_join(member):

    try:

        new_role = find_role(
            member.guild,
            ROLE_NEW_KEYWORD
        )

        if new_role:
            await member.add_roles(new_role)

    except Exception:
        traceback.print_exc()

# =========================
# COMMANDS
# =========================

@bot.tree.command(
    name="ping",
    description="Test bot",
    guild=GUILD_OBJECT
)
async def ping(interaction):

    await interaction.response.send_message(
        "🏓 Pong!",
        ephemeral=True
    )

@bot.tree.command(
    name="setup_verifica",
    description="Invia pannello verifica",
    guild=GUILD_OBJECT
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
            "Premi il pulsante qui sotto "
            "per verificarti."
        ),
        color=0x2ecc71
    )

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
    description="Invia pannello ruoli",
    guild=GUILD_OBJECT
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
            "Seleziona i ruoli "
            "che ti rappresentano."
        ),
        color=0x3498db
    )

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
    description="Invia pannello ticket",
    guild=GUILD_OBJECT
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
            "Seleziona dal menu "
            "il tipo di ticket."
        ),
        color=0x3498db
    )

    embed.add_field(
        name="Categorie disponibili",
        value=(
            "🎫 Supporto Generale\n"
            "🤝 Partnership\n"
            "⭐ Promozione Server\n"
            "💼 Candidatura Staff"
        ),
        inline=False
    )

    embed.set_footer(
        text="RedM Italia Community • Ticket System"
    )

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "✅ Pannello ticket pubblicato.",
        ephemeral=True
    )

# =========================
# RUN
# =========================

bot.run(DISCORD_TOKEN)
