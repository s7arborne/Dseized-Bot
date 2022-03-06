import os
import discord
from discord.ext import commands

#creates an instance of Bot to interact with discord webSocket and api
TokenFile = open("./data/Token.txt", "r") #works only when the directory is set to bot's folder
TOKEN = TokenFile.read()
OWNERID = 931968569976189008
bot=commands.Bot()

#registers an event that is called when the bot has finished logging in
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="with the homies"))
    print("Logged in as", bot.user)

#an error handler
@bot.event
async def on_command_error(ctx,error):
    embed = discord.Embed(
    title='',
    color=discord.Color.red())
    if isinstance(error, commands.MissingPermissions):
        embed.add_field(
            name="Invalid Permissions",
            value=f"You dont have {error.missing_perms} permissions.",
        )
        await ctx.send(embed=embed)
    else:
        embed.add_field(name=":x: Terminal Error", value = f"```{error}```")
        await ctx.send(embed = embed)
        raise error

#loads all the .py files in the Cogs folder automatically
for filename in os.listdir("./Cogs"):
    if filename.endswith(".py"):
        try:
            bot.load_extension("Cogs."+filename[:-3]) #load_extension takes Cogs.uwu as argument for Cogs/uwu.py
        except Exception:
            raise Exception

#commands to load, unload and reload extensions individually
@bot.slash_command(description="Loads extension to the bot.")
async def load(ctx, extension):
    #limits use of the command to bot's owner
    if ctx.author.id == OWNERID:
        bot.load_extension(f"Cogs.{extension}")
        await ctx.respond("Enabled " + extension + "!")
    else:
        await ctx.respond("You don't have the permission to run this command.")

@bot.slash_command(description="Unloads extension from the bot.")
async def unload(ctx, extension):
    if ctx.author.id == OWNERID:
        bot.unload_extension(f"Cogs.{extension}")
        await ctx.respond("Disabled " + extension + "!")
    else:
        await ctx.respond("You don't have the permission to run this command.")

@bot.slash_command(description="Reloads extension to the bot.")
async def reload(ctx, extension):
    if ctx.author.id == OWNERID:
        bot.reload_extension(f"Cogs.{extension}")
        await ctx.respond("Reloaded " + extension + "!")
    else:
        await ctx.respond("You don't have the permission to run this command.")

#running the bot with login token
bot.run(TOKEN)