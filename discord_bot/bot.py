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

CHANNEL_VERIFY_KEYWORD = "verifica"
CHANNEL_LOG_KEYWORD = "admin-logs"

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


async def send_admin_log(guild: discord.Guild, title: str, description: str):
    channel = find_channel(guild, CHANNEL_LOG_KEYWORD)

    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=0x2ecc71
    )

    await channel.send(embed=embed)


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
                "Errore: impossibile completare la verifica.",
                ephemeral=True
            )
            return

        verified_role = find_role(guild, ROLE_VERIFIED_KEYWORD)
        new_role = find_role(guild, ROLE_NEW_KEYWORD)

        if not verified_role:
            await interaction.response.send_message(
                "Errore: ruolo Verified non trovato. Contatta lo staff.",
                ephemeral=True
            )
            return

        try:
            await member.add_roles(
                verified_role,
                reason="Verifica completata tramite RedM Italia Bot"
            )

            if new_role and new_role in member.roles:
                await member.remove_roles(
                    new_role,
                    reason="Utente verificato"
                )

            await interaction.response.send_message(
                "✅ Verifica completata!\n\nBenvenuto in RedM Italia Community.",
                ephemeral=True
            )

            await send_admin_log(
                guild,
                "✅ Utente verificato",
                f"Utente: {member.mention}\nID: `{member.id}`"
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "Errore permessi: il bot non può assegnare il ruolo Verified. Controlla l’ordine dei ruoli.",
                ephemeral=True
            )

        except Exception as error:
            await interaction.response.send_message(
                "Errore imprevisto durante la verifica. Contatta lo staff.",
                ephemeral=True
            )
            print(f"Errore verifica: {error}")


@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot online: {bot.user}")
    print("━━━━━━━━━━━━━━━━━━")

    bot.add_view(VerifyView())

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


bot.run(DISCORD_TOKEN)
