import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

ROLE_VERIFIED_KEYWORD = "verified"
ROLE_NEW_KEYWORD = "nuovo arrivato"
CHANNEL_LOG_KEYWORD = "admin-logs"

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
    },
    "staff_server": {
        "label": "Staff Server",
        "emoji": "🛡️",
        "keyword": "staff server"
    },
    "owner": {
        "label": "Owner",
        "emoji": "🏜️",
        "keyword": "owner"
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


def find_channel(guild: discord.Guild, keyword: str):
    keyword = keyword.lower()

    for channel in guild.text_channels:
        if keyword in channel.name.lower():
            return channel

    return None


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

    @discord.ui.button(
        label="Staff Server",
        emoji="🛡️",
        style=discord.ButtonStyle.secondary,
        custom_id="redm_role_staff_server"
    )
    async def staff_server_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.toggle_role(interaction, "staff_server")

    @discord.ui.button(
        label="Owner",
        emoji="🏜️",
        style=discord.ButtonStyle.secondary,
        custom_id="redm_role_owner"
    )
    async def owner_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.toggle_role(interaction, "owner")


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
                    "🎥 Creator\n"
                    "🛡️ Staff Server\n"
                    "🏜️ Owner"
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

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="RedM Italia Community"
        )
    )

    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands sincronizzati: {len(synced)}")
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
    description="Test bot"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🏓 Pong! Bot online.",
        ephemeral=True
    )


@bot.tree.command(
    name="setup_verifica",
    description="Invia il pannello verifica nel canale corrente"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def setup_verifica(interaction: discord.Interaction):
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


@setup_verifica.error
async def setup_verifica_error(
    interaction: discord.Interaction,
    error
):
    await interaction.response.send_message(
        "❌ Non hai i permessi per usare questo comando.",
        ephemeral=True
    )


@bot.tree.command(
    name="ruoli",
    description="Invia il pannello selezione ruoli nel canale corrente"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def ruoli(interaction: discord.Interaction):
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
            "🎥 **Creator** — crei contenuti, clip o live\n"
            "🛡️ **Staff Server** — fai parte dello staff di un server\n"
            "🏜️ **Owner** — gestisci o rappresenti un server"
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


@ruoli.error
async def ruoli_error(
    interaction: discord.Interaction,
    error
):
    await interaction.response.send_message(
        "❌ Non hai i permessi per usare questo comando.",
        ephemeral=True
    )


bot.run(DISCORD_TOKEN)
