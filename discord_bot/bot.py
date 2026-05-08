import os
import time
import asyncio
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
        "title": "🎫 Supporto Generale",
        "description": (
            "Hai aperto un ticket di **Supporto Generale**.\n\n"
            "Spiega chiaramente la tua richiesta così lo staff potrà aiutarti nel modo migliore."
        ),
        "questions": (
            "• Qual è il problema o la richiesta?\n"
            "• Da quanto succede?\n"
            "• Hai screenshot, video o prove utili?\n"
            "• Hai già contattato qualcuno dello staff?"
        )
    },
    "partnership": {
        "label": "Partnership",
        "emoji": "🤝",
        "channel_prefix": "partnership",
        "color": 0x9b59b6,
        "title": "🤝 Richiesta Partnership",
        "description": (
            "Hai aperto un ticket per una **Partnership**.\n\n"
            "Presenta la tua community, server o progetto in modo chiaro e professionale."
        ),
        "questions": (
            "• Nome server/community/progetto\n"
            "• Numero membri\n"
            "• Link Discord o riferimento ufficiale\n"
            "• Che tipo di collaborazione proponi?\n"
            "• Perché dovremmo collaborare?"
        )
    },
    "promozione_server": {
        "label": "Promozione Server",
        "emoji": "⭐",
        "channel_prefix": "server",
        "color": 0xf1c40f,
        "title": "⭐ Promozione Server",
        "description": (
            "Hai aperto un ticket per richiedere la **Promozione di un Server RedM**.\n\n"
            "Inserisci tutte le informazioni necessarie per valutare il tuo server."
        ),
        "questions": (
            "• Nome server\n"
            "• Descrizione breve\n"
            "• Link Discord\n"
            "• Stato server: aperto / in sviluppo\n"
            "• Cosa rende unico il server?\n"
            "• Hai immagini, trailer o grafiche?"
        )
    },
    "candidatura_staff": {
        "label": "Candidatura Staff",
        "emoji": "💼",
        "channel_prefix": "staff",
        "color": 0x2ecc71,
        "title": "💼 Candidatura Staff",
        "description": (
            "Hai aperto un ticket per una **Candidatura Staff**.\n\n"
            "Compila le informazioni richieste con serietà e precisione."
        ),
        "questions": (
            "• Età\n"
            "• Esperienze precedenti\n"
            "• Ruolo desiderato\n"
            "• Disponibilità settimanale\n"
            "• Perché vuoi entrare nello staff?\n"
            "• Cosa puoi portare alla community?"
        )
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

    if not name:
        name = "utente"

    return name[:35]


def user_has_open_ticket(guild: discord.Guild, user_id: int):
    user_id_text = str(user_id)

    for channel in guild.text_channels:
        if channel.topic and f"ticket_owner:{user_id_text}" in channel.topic:
            return channel

    return None


def is_ticket_channel(channel: discord.TextChannel):
    return bool(channel.topic and "ticket_owner:" in channel.topic)


def get_ticket_owner_id(channel: discord.TextChannel):
    if not channel.topic or "ticket_owner:" not in channel.topic:
        return None

    try:
        return channel.topic.split("ticket_owner:")[1].split(" ")[0]
    except Exception:
        return None


def get_ticket_type(channel: discord.TextChannel):
    if not channel.topic or "ticket_type:" not in channel.topic:
        return "sconosciuto"

    try:
        return channel.topic.split("ticket_type:")[1].split(" ")[0]
    except Exception:
        return "sconosciuto"


def member_is_ticket_staff(member: discord.Member):
    staff_roles = find_roles(member.guild, TICKET_STAFF_ROLE_KEYWORDS)

    if member.guild_permissions.manage_channels:
        return True

    return any(role in member.roles for role in staff_roles)


def member_can_use_setup_commands(member: discord.Member):
    if member.guild_permissions.administrator:
        return True

    if member.guild_permissions.manage_guild:
        return True

    for role in member.roles:
        role_name = role.name.lower()

        if any(keyword in role_name for keyword in SETUP_ALLOWED_ROLE_KEYWORDS):
            return True

    return False


def member_is_verified(member: discord.Member):
    verified_role = find_role(member.guild, ROLE_VERIFIED_KEYWORD)

    if not verified_role:
        return False

    return verified_role in member.roles


def ticket_cooldown_remaining(user_id: int):
    now = time.time()
    last_open = ticket_cooldowns.get(user_id)

    if not last_open:
        return 0

    elapsed = now - last_open
    remaining = TICKET_COOLDOWN_SECONDS - elapsed

    if remaining <= 0:
        return 0

    return int(remaining)


async def get_or_create_ticket_category(guild: discord.Guild):
    category = find_category(guild, TICKET_CATEGORY_KEYWORD)

    if category:
        return category

    category = await guild.create_category(
        name=TICKET_CATEGORY_NAME,
        reason="Categoria ticket creata automaticamente"
    )

    return category


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

    embed.set_footer(text="RedM Italia Community • Admin Logs")

    await channel.send(embed=embed)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Chiudi Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="redm_ticket_close"
    )
    async def close_ticket_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild
        channel = interaction.channel
        member = interaction.user

        if not guild or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                "❌ Errore: impossibile chiudere questo ticket.",
                ephemeral=True
            )
            return

        if not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Errore: membro non valido.",
                ephemeral=True
            )
            return

        if not is_ticket_channel(channel):
            await interaction.response.send_message(
                "❌ Questo canale non sembra essere un ticket valido.",
                ephemeral=True
            )
            return

        owner_id = get_ticket_owner_id(channel)
        ticket_type = get_ticket_type(channel)

        is_owner = owner_id == str(member.id)
        is_staff = member_is_ticket_staff(member)

        if not is_owner and not is_staff:
            await interaction.response.send_message(
                "❌ Non hai i permessi per chiudere questo ticket.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "🔒 Ticket in chiusura. Il canale verrà eliminato tra 5 secondi.",
            ephemeral=False
        )

        await send_admin_log(
            guild,
            "🔒 Ticket chiuso",
            (
                f"Canale: `{channel.name}`\n"
                f"Tipo: `{ticket_type}`\n"
                f"Chiuso da: {member.mention}\n"
                f"Owner ID: `{owner_id}`"
            ),
            color=0xe74c3c
        )

        await asyncio.sleep(5)

        try:
            await channel.delete(
                reason=f"Ticket chiuso da {member}"
            )
        except Exception as error:
            print(f"Errore chiusura ticket: {error}")


class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Supporto Generale",
                description="Problemi Discord, dubbi o richieste generiche",
                emoji="🎫",
                value="supporto_generale"
            ),
            discord.SelectOption(
                label="Partnership",
                description="Collaborazioni con server, community o creator",
                emoji="🤝",
                value="partnership"
            ),
            discord.SelectOption(
                label="Promozione Server",
                description="Richiedi la promozione del tuo server RedM",
                emoji="⭐",
                value="promozione_server"
            ),
            discord.SelectOption(
                label="Candidatura Staff",
                description="Candidati come Helper, Moderatore o staff community",
                emoji="💼",
                value="candidatura_staff"
            )
        ]

        super().__init__(
            placeholder="Seleziona il tipo di ticket...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="redm_ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Errore: impossibile aprire il ticket.",
                ephemeral=True
            )
            return

        if not member_is_verified(member):
            await interaction.response.send_message(
                "❌ Devi essere verificato per aprire un ticket.",
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

        remaining = ticket_cooldown_remaining(member.id)

        if remaining > 0:
            minutes = max(1, remaining // 60)
            await interaction.response.send_message(
                f"⏳ Devi attendere circa {minutes} minuto/i prima di aprire un altro ticket.",
                ephemeral=True
            )
            return

        ticket_type_key = self.values[0]
        ticket_data = TICKET_TYPES.get(ticket_type_key)

        if not ticket_data:
            await interaction.response.send_message(
                "❌ Tipo ticket non valido.",
                ephemeral=True
            )
            return

        try:
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

            if bot_member:
                overwrites[bot_member] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    attach_files=True,
                    embed_links=True
                )

            for role in staff_roles:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True,
                    attach_files=True,
                    embed_links=True
                )

            channel_name = (
                f"ticket-{ticket_data['channel_prefix']}-"
                f"{clean_channel_name(member.name)}"
            )

            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=f"ticket_owner:{member.id} ticket_type:{ticket_type_key}",
                overwrites=overwrites,
                reason=f"Ticket {ticket_type_key} aperto da {member}"
            )

            embed = discord.Embed(
                title=ticket_data["title"],
                description=(
                    f"{ticket_data['description']}\n\n"
                    f"Utente: {member.mention}"
                ),
                color=ticket_data["color"]
            )

            embed.add_field(
                name="Informazioni richieste",
                value=ticket_data["questions"],
                inline=False
            )

            embed.add_field(
                name="Regole del ticket",
                value=(
                    "• Scrivi in modo chiaro e ordinato\n"
                    "• Non taggare lo staff inutilmente\n"
                    "• Non aprire ticket duplicati\n"
                    "• Mantieni sempre rispetto e serietà"
                ),
                inline=False
            )

            embed.set_footer(text="RedM Italia Community • Sistema Ticket")

            staff_mentions = " ".join(role.mention for role in staff_roles)

            await ticket_channel.send(
                content=f"{member.mention} {staff_mentions}".strip(),
                embed=embed,
                view=TicketCloseView()
            )

            ticket_cooldowns[member.id] = time.time()

            await interaction.response.send_message(
                f"✅ Ticket creato correttamente: {ticket_channel.mention}",
                ephemeral=True
            )

            await send_admin_log(
                guild,
                "🎫 Ticket aperto",
                (
                    f"Utente: {member.mention}\n"
                    f"Tipo: `{ticket_data['label']}`\n"
                    f"Canale: {ticket_channel.mention}\n"
                    f"ID utente: `{member.id}`"
                ),
                color=ticket_data["color"]
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Errore permessi: il bot non può creare o gestire i canali ticket. Controlla il ruolo Bot.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                "❌ Errore imprevisto durante la creazione del ticket.",
                ephemeral=True
            )
            print(f"Errore apertura ticket: {error}")


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class RolePickerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def toggle_role(self, interaction: discord.Interaction, role_key: str):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Errore: impossibile assegnare il ruolo.",
                ephemeral=True
            )
            return

        role_data = ROLE_OPTIONS.get(role_key)

        if not role_data:
            await interaction.response.send_message(
                "❌ Errore: ruolo non configurato.",
                ephemeral=True
            )
            return

        role = find_role(guild, role_data["keyword"])

        if not role:
            await interaction.response.send_message(
                f"❌ Errore: ruolo `{role_data['label']}` non trovato. Contatta lo staff.",
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

                await send_admin_log(
                    guild,
                    "🎭 Ruolo rimosso",
                    f"Utente: {member.mention}\nRuolo: `{role.name}`\nID: `{member.id}`",
                    color=0xe74c3c
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

                await send_admin_log(
                    guild,
                    "🎭 Ruolo assegnato",
                    f"Utente: {member.mention}\nRuolo: `{role.name}`\nID: `{member.id}`"
                )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Errore permessi: il bot non può assegnare questo ruolo. Controlla l’ordine dei ruoli.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                "❌ Errore imprevisto durante l’assegnazione del ruolo.",
                ephemeral=True
            )
            print(f"Errore role picker: {error}")

    @discord.ui.button(
        label="Player",
        emoji="🎮",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_player"
    )
    async def player_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.toggle_role(interaction, "player")

    @discord.ui.button(
        label="Developer",
        emoji="💻",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_developer"
    )
    async def developer_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.toggle_role(interaction, "developer")

    @discord.ui.button(
        label="Mapper",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_mapper"
    )
    async def mapper_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.toggle_role(interaction, "mapper")

    @discord.ui.button(
        label="UI Designer",
        emoji="🎨",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_ui_designer"
    )
    async def ui_designer_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.toggle_role(interaction, "ui_designer")

    @discord.ui.button(
        label="Creator",
        emoji="🎥",
        style=discord.ButtonStyle.primary,
        custom_id="redm_role_creator"
    )
    async def creator_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
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
    async def verify_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        guild = interaction.guild
        member = interaction.user

        if not guild or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "❌ Errore: impossibile completare la verifica.",
                ephemeral=True
            )
            return

        verified_role = find_role(guild, ROLE_VERIFIED_KEYWORD)
        new_role = find_role(guild, ROLE_NEW_KEYWORD)

        if not verified_role:
            await interaction.response.send_message(
                "❌ Errore: ruolo Verified non trovato. Contatta lo staff.",
                ephemeral=True
            )
            return

        try:
            if verified_role not in member.roles:
                await member.add_roles(
                    verified_role,
                    reason="Verifica completata tramite RedM Italia Bot"
                )

            if new_role and new_role in member.roles:
                await member.remove_roles(
                    new_role,
                    reason="Utente verificato"
                )

            embed = discord.Embed(
                title="✅ Verifica completata",
                description=(
                    f"Benvenuto in **RedM Italia Community**, {member.mention}.\n\n"
                    "Ora scegli il ruolo che ti rappresenta nella community.\n"
                    "Puoi selezionare anche più ruoli se ti rispecchiano."
                ),
                color=0x2ecc71
            )

            embed.add_field(
                name="Ruoli disponibili",
                value=(
                    "🎮 Player\n"
                    "💻 Developer\n"
                    "🗺️ Mapper\n"
                    "🎨 UI Designer\n"
                    "🎥 Creator"
                ),
                inline=False
            )

            embed.set_footer(text="RedM Italia Community • Selezione ruoli")

            await interaction.response.send_message(
                embed=embed,
                view=RolePickerView(),
                ephemeral=True
            )

            await send_admin_log(
                guild,
                "✅ Utente verificato",
                f"Utente: {member.mention}\nID: `{member.id}`"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Errore permessi: il bot non può assegnare il ruolo Verified. Controlla l’ordine dei ruoli.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                "❌ Errore imprevisto durante la verifica. Contatta lo staff.",
                ephemeral=True
            )
            print(f"Errore verifica: {error}")


@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot online: {bot.user}")
    print("━━━━━━━━━━━━━━━━━━")

    bot.add_view(VerifyView())
    bot.add_view(RolePickerView())
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="RedM Italia Community"
        )
    )

    try:
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()

        synced = await bot.tree.sync(guild=GUILD_OBJECT)

        print(f"✅ Slash commands GUILD sincronizzati: {len(synced)}")

        for command in synced:
            print(f"   /{command.name}")

    except Exception as e:
        print(f"❌ Errore sync slash commands: {e}")


@bot.event
async def on_member_join(member: discord.Member):
    try:
        new_role = find_role(member.guild, ROLE_NEW_KEYWORD)

        if new_role:
            await member.add_roles(
                new_role,
                reason="Nuovo membro entrato nel server"
            )

        await send_admin_log(
            member.guild,
            "👋 Nuovo membro",
            f"Utente: {member.mention}\nID: `{member.id}`\nRuolo assegnato: `{new_role.name if new_role else 'non trovato'}`"
        )

        print(f"✅ Nuovo utente: {member}")

    except Exception as e:
        print(f"❌ Errore on_member_join: {e}")


@bot.tree.command(
    name="ping",
    description="Test bot",
    guild=GUILD_OBJECT
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🏓 Pong! Bot online.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_verifica",
    description="Invia il pannello verifica nel canale corrente",
    guild=GUILD_OBJECT
)
async def setup_verifica(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not member_can_use_setup_commands(interaction.user):
        await interaction.response.send_message(
            "❌ Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="✅ Verifica Community",
        description=(
            "Benvenuto in **RedM Italia Community**.\n\n"
            "Per accedere alla community completa premi il pulsante qui sotto.\n\n"
            "Dopo la verifica potrai:\n"
            "• accedere ai canali principali\n"
            "• scegliere il tuo ruolo\n"
            "• partecipare alla community\n\n"
            "⚠️ Rispetta il regolamento e mantieni un comportamento corretto."
        ),
        color=0x2ecc71
    )

    embed.set_footer(text="RedM Italia Community • Sistema verifica ufficiale")

    await interaction.channel.send(
        embed=embed,
        view=VerifyView()
    )

    await interaction.response.send_message(
        "✅ Pannello verifica pubblicato correttamente.",
        ephemeral=True
    )


@bot.tree.command(
    name="ruoli",
    description="Invia il pannello selezione ruoli nel canale corrente",
    guild=GUILD_OBJECT
)
async def ruoli(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not member_can_use_setup_commands(interaction.user):
        await interaction.response.send_message(
            "❌ Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎭 Scegli il tuo ruolo",
        description=(
            "Seleziona il ruolo che ti rappresenta nella community.\n\n"
            "Puoi scegliere anche più ruoli.\n"
            "Se clicchi di nuovo su un ruolo già assegnato, verrà rimosso."
        ),
        color=0x3498db
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

    embed.set_footer(text="RedM Italia Community • Role picker ufficiale")

    await interaction.channel.send(
        embed=embed,
        view=RolePickerView()
    )

    await interaction.response.send_message(
        "✅ Pannello ruoli pubblicato correttamente.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_ticket",
    description="Invia il pannello ticket nel canale corrente",
    guild=GUILD_OBJECT
)
async def setup_ticket(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not member_can_use_setup_commands(interaction.user):
        await interaction.response.send_message(
            "❌ Non hai i permessi per usare questo comando.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎫 Centro Supporto RedM Italia",
        description=(
            "Benvenuto nel centro supporto ufficiale di **RedM Italia Community**.\n\n"
            "Seleziona dal menu qui sotto il tipo di richiesta più adatto.\n"
            "Lo staff riceverà il tuo ticket in un canale privato.\n\n"
            "Apri un ticket solo se hai davvero bisogno di supporto."
        ),
        color=0x3498db
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

    embed.set_footer(text="RedM Italia Community • Sistema ticket ufficiale")

    await interaction.channel.send(
        embed=embed,
        view=TicketPanelView()
    )

    await interaction.response.send_message(
        "✅ Pannello ticket pubblicato correttamente.",
        ephemeral=True
    )


bot.run(DISCORD_TOKEN)
