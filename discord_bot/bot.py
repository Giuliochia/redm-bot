import os
import io
import asyncio
import traceback
import discord

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

GUILD_OBJECT = discord.Object(id=GUILD_ID)

BRAND_NAME = "RedM Italia Community"
BRAND_COLOR = 0x8B0000
SUCCESS_COLOR = 0x2ECC71
INFO_COLOR = 0x3498DB
DANGER_COLOR = 0xE74C3C
WARNING_COLOR = 0xF1C40F

ROLE_VERIFIED_KEYWORD = "verified"
ROLE_NEW_KEYWORD = "nuovo arrivato"

CHANNEL_LOG_KEYWORD = "admin-logs"
CHANNEL_WELCOME_KEYWORD = "benvenuti"

TICKET_CATEGORY_NAME = "🎫 | TICKET"
TICKET_CATEGORY_KEYWORD = "ticket"

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

BANNER_VERIFICA = os.path.join(ASSETS_DIR, "banner_verifica.png")
BANNER_RUOLI = os.path.join(ASSETS_DIR, "banner_ruoli.png")
BANNER_DISCORD = os.path.join(ASSETS_DIR, "banner_discord.png")

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


def asset_exists(path):
    return os.path.exists(path)


def make_file(path, filename):
    if not asset_exists(path):
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


async def send_welcome_message(member):
    guild = member.guild
    channel = find_channel(guild, CHANNEL_WELCOME_KEYWORD)

    if not channel:
        print("⚠️ Canale benvenuti non trovato.")
        return

    member_count = guild.member_count or len(guild.members)

    embed = discord.Embed(
        title="🌅 Benvenuto nella RedM Italia Community",
        description=(
            f"Benvenuto {member.mention}.\n\n"
            "Sei appena entrato nella community italiana dedicata a **RedM**.\n"
            "Completa la verifica per accedere a tutte le sezioni del server.\n\n"
            "📌 **Primi passi consigliati**\n"
            "• Leggi il regolamento\n"
            "• Completa la verifica\n"
            "• Scegli il tuo ruolo\n"
            "• Partecipa alla community"
        ),
        color=BRAND_COLOR
    )

    embed.add_field(
        name="👥 Membri community",
        value=f"Sei il membro numero **{member_count}**.",
        inline=True
    )

    embed.add_field(
        name="✅ Accesso",
        value="Vai nel canale verifica e premi **Verificami**.",
        inline=True
    )

    embed.set_author(
        name=str(member),
        icon_url=member.display_avatar.url
    )

    apply_brand(embed, guild)

    file = make_file(BANNER_DISCORD, "banner_discord.png")

    if file:
        embed.set_image(url="attachment://banner_discord.png")

        await channel.send(
            content=f"👋 Benvenuto {member.mention}",
            file=file,
            embed=embed
        )
    else:
        await channel.send(
            content=f"👋 Benvenuto {member.mention}",
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

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=BRAND_NAME
        )
    )

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
    try:
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

    file = make_file(BANNER_DISCORD, "banner_discord.png")

    if file:
        embed.set_image(url="attachment://banner_discord.png")

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


bot.run(DISCORD_TOKEN)