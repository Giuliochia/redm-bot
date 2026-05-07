import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    print("━━━━━━━━━━━━━━━━━━")
    print(f"✅ Bot online: {bot.user}")
    print("━━━━━━━━━━━━━━━━━━")

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
async def on_member_join(member):
    try:
        role = discord.utils.get(
            member.guild.roles,
            name="Nuovo Arrivato"
        )

        if role:
            await member.add_roles(role)

        channel = discord.utils.get(
            member.guild.text_channels,
            name="annunci"
        )

        if channel:
            embed = discord.Embed(
                title="👋 Nuovo utente",
                description=f"{member.mention} è entrato nel server!",
                color=0x2ecc71
            )

            embed.set_thumbnail(url=member.display_avatar.url)

            await channel.send(embed=embed)

        print(f"✅ Nuovo utente: {member}")

    except Exception as e:
        print(f"❌ Errore join member: {e}")


@bot.tree.command(
    name="ping",
    description="Test bot"
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🏓 Pong! Bot online.",
        ephemeral=True
    )


bot.run(DISCORD_TOKEN)
