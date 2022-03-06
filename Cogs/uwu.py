import uwuify
from discord.ext import commands

class uwu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="UwUifies your message.")
    async def uwu(self, ctx, say: str):
        flags = uwuify.SMILEY | uwuify.YU
        conv = uwuify.uwu(f"{say}", flags=flags)
        await ctx.respond(conv)

def setup(bot):
    bot.add_cog(uwu(bot))