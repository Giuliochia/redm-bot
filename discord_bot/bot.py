import os
import time
import asyncio
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

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

TICKET_COOLDOWN_SECONDS = 300

GUILD_OBJECT = discord.Object(id=GUILD_ID)

ticket_cooldowns = {}
ticket_claims = {}

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
        "color": 0x3498db,
        "title": "🎫 Supporto Generale"
    },
    "partnership": {
        "label": "Partnership",
        "emoji": "🤝",
        "channel_prefix": "partnership",
        "color": 0x9b59b6,
        "title": "🤝 Richiesta Partnership"
    },
    "promozione_server": {
        "label": "Promozione Server",
        "emoji": "⭐",
        "channel_prefix": "server",
        "color": 0xf1c40f,
        "title": "⭐ Promozione Server"
    },
    "candidatura_staff": {
        "label": "Candidatura Staff",
        "emoji": "💼",
        "channel_prefix": "staff",
        "color": 0x2ecc71,
        "title": "💼 Candidatura Staff"
    }
}

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


def find_role(guild: discord.Guild, keyword: str):
    keyword = keyword.lower()

    for role in guild.roles:
        if keyword in role.name.lower():
            return role

    return None


def find_roles(guild: discord.Guild, keywords: list[str]):
    roles = []

    for keyword in keywords:
        role = find_role(guild, keyword)

        if role and role not in roles:
            roles.append(role)

    return roles


def find_channel(guild: discord.Guild, keyword: str):
    keyword = keyword.lower()

    for channel in guild.text_channels:
        if keyword in channel.name.lower():
            return channel

    return None


def find_category(guild: discord.Guild, keyword: str):
    keyword = keyword.lower()

    for category in guild.categories:
        if keyword in category.name.lower():
            return category

    return None


def clean_channel_name(name: str):
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"

    name = name.lower()
    name = name.replace(" ", "-")
    name = "".join(char for char in name if char in allowed)

    return name[:30]


def user_has_open_ticket(guild: discord.Guild, user_id: int):
    user_id_text = str(user_id)

    for channel in guild.text_channels:
        if channel.topic and f"ticket_owner:{user_id_text}" in channel.topic:
            return channel

    return None


def is_ticket_channel(channel: discord.TextChannel):
    return bool(channel.topic and "ticket_owner:" in channel.topic)


def get_ticket_owner_id(channel: discord.TextChannel):
    if not channel.topic:
        return None

    try:
        return channel.topic.split("ticket_owner:")[1].split(" ")[0]
    except Exception:
        return None


def member_is_ticket_staff(member: discord.Member):
    staff_roles = find_roles(member.guild, TICKET_STAFF_ROLE_KEYWORDS)

    if member.guild_permissions.manage_channels:
        return True

    return any(role in member.roles for role in staff_roles)


def member_can_use_setup_commands(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    for role in member.roles:
        if any(keyword in role.name.lower() for keyword in SETUP_ALLOWED_ROLE_KEYWORDS):
            return True

    return False


def member_is_verified(member: discord.Member):
    verified_role = find_role(member.guild, ROLE_VERIFIED_KEYWORD)

    if not verified_role:
        return False

    return verified_role in member.roles


async def get_or_create_ticket_category(guild: discord.Guild):
    category = find_category(guild, TICKET_CATEGORY_KEYWORD)

    if category:
        return category

    return await guild.create_category(name=TICKET_CATEGORY_NAME)


async def send_admin_log(
    guild: discord.Guild,
    title: str,
    description: str,
    color=0x2ecc71
):
    channel = find_channel(guild, CHANNEL_LOG_KEYWORD)

    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )

    await channel.send(embed=embed)


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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user
        channel = interaction.channel

        if not isinstance(member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        if not member_is_ticket_staff(member):
            await interaction.response.send_message(
                "❌ Solo lo staff può prendere in carico i ticket.",
                ephemeral=True
            )
            return

        claimed_by = ticket_claims.get(channel.id)

        if claimed_by:
            await interaction.response.send_message(
                "⚠️ Questo ticket è già stato preso in carico.",
                ephemeral=True
            )
            return

        ticket_claims[channel.id] = member.id

        embed = discord.Embed(
            title="📌 Ticket preso in carico",
            description=f"{member.mention} ha preso in carico questo ticket.",
            color=0x3498db
        )

        await channel.send(embed=embed)

        await send_admin_log(
            member.guild,
            "📌 Ticket claimato",
            (
                f"Staff: {member.mention}\n"
                f"Canale: {channel.mention}"
            ),
            color=0x3498db
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
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        member = interaction.user
        channel = interaction.channel

        if not isinstance(member, discord.Member):
            return

        if not isinstance(channel, discord.TextChannel):
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
            "🔒 Ticket in chiusura tra 5 secondi...",
            ephemeral=False
        )

        await send_admin_log(
            member.guild,
            "🔒 Ticket chiuso",
            (
                f"Canale: {channel.name}\n"
                f"Chiuso da: {member.mention}"
            ),
            color=0xe74c3c
        )

        await asyncio.sleep(5)

        try:
            await channel.delete()

        except Exception:
            print("❌ ERRORE ELIMINAZIONE TICKET")
            traceback.print_exc()


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

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            return

        if not member_is_verified(member):
            await interaction.response.send_message(
                "❌ Devi essere verificato.",
                ephemeral=True
            )
            return

        existing_ticket = user_has_open_ticket(guild, member.id)

        if existing_ticket:
            await interaction.response.send_message(
                f"⚠️ Hai già un ticket aperto: {existing_ticket.mention}",
                ephemeral=True
            )
            return

        category = await get_or_create_ticket_category(guild)

        staff_roles = find_roles(guild, TICKET_STAFF_ROLE_KEYWORDS)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
        }

        for role in staff_roles:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )

        bot_member = guild.me

        if bot_member:
            overwrites[bot_member] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )

        ticket_type = self.values[0]
        ticket_data = TICKET_TYPES[ticket_type]

        channel_name = (
            f"ticket-{ticket_data['channel_prefix']}-"
            f"{clean_channel_name(member.name)}"
        )

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"ticket_owner:{member.id}"
        )

        embed = discord.Embed(
            title=ticket_data["title"],
            description=(
                f"{member.mention}, il ticket è stato creato correttamente.\n\n"
                "Attendi una risposta dallo staff."
            ),
            color=ticket_data["color"]
        )

        await channel.send(
            content=" ".join(role.mention for role in staff_roles),
            embed=embed,
            view=TicketControlView()
        )

        await send_admin_log(
            guild,
            "🎫 Ticket aperto",
            (
                f"Utente: {member.mention}\n"
                f"Tipo: {ticket_data['label']}\n"
                f"Canale: {channel.mention}"
            ),
            color=ticket_data["color"]
        )

        await interaction.response.send_message(
            f"✅ Ticket creato: {channel.mention}",
            ephemeral=True
        )


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


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
            return

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

    @discord.ui.button(
        label="Player",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="role_player"
    )
    async def player_button(self, interaction, button):
        await self.toggle_role(interaction, "player")

    @discord.ui.button(
        label="Developer",
        emoji="💻",
        style=discord.ButtonStyle.primary,
        custom_id="role_developer"
    )
    async def developer_button(self, interaction, button):
        await self.toggle_role(interaction, "developer")

    @discord.ui.button(
        label="Mapper",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="role_mapper"
    )
    async def mapper_button(self, interaction, button):
        await self.toggle_role(interaction, "mapper")

    @discord.ui.button(
        label="UI Designer",
        emoji="🎨",
        style=discord.ButtonStyle.primary,
        custom_id="role_ui"
    )
    async def ui_button(self, interaction, button):
        await self.toggle_role(interaction, "ui_designer")

    @discord.ui.button(
        label="Creator",
        emoji="🎥",
        style=discord.ButtonStyle.primary,
        custom_id="role_creator"
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
        custom_id="verify_button"
    )
    async def verify_button(self, interaction, button):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            return

        verified_role = find_role(guild, ROLE_VERIFIED_KEYWORD)
        new_role = find_role(guild, ROLE_NEW_KEYWORD)

        if verified_role and verified_role not in member.roles:
            await member.add_roles(verified_role)

        if new_role and new_role in member.roles:
            await member.remove_roles(new_role)

        await interaction.response.send_message(
            "✅ Verifica completata.",
            ephemeral=True
        )


@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot online: {bot.user}")
    print("━━━━━━━━━━━━━━━━━━")

    bot.add_view(VerifyView())
    bot.add_view(RolePickerView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketControlView())

    synced = await bot.tree.sync(guild=GUILD_OBJECT)

    print(f"✅ Slash commands sincronizzati: {len(synced)}")


@bot.event
async def on_member_join(member):
    new_role = find_role(member.guild, ROLE_NEW_KEYWORD)

    if new_role:
        await member.add_roles(new_role)


@bot.tree.command(
    name="setup_verifica",
    description="Invia pannello verifica",
    guild=GUILD_OBJECT
)
async def setup_verifica(interaction):
    if not member_can_use_setup_commands(interaction.user):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="✅ Verifica Community",
        description="Premi il pulsante qui sotto per verificarti.",
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
    if not member_can_use_setup_commands(interaction.user):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎭 Scegli il tuo ruolo",
        description="Seleziona i ruoli che ti rappresentano.",
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
    if not member_can_use_setup_commands(interaction.user):
        await interaction.response.send_message(
            "❌ Non hai i permessi.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 Centro Supporto RedM Italia",
        description=(
            "Benvenuto nel centro supporto ufficiale.\n\n"
            "Seleziona il tipo di ticket dal menu qui sotto."
        ),
        color=0x3498db
    )

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "✅ Pannello ticket pubblicato.",
        ephemeral=True
    )


bot.run(DISCORD_TOKEN)
