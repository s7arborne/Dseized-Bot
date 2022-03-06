import discord
from discord.ext import commands
from discord.ext.commands import check
import time
from mal import *

class misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description="Sends an invite link for the bot.")
    async def invite(self, ctx):
        await ctx.respond(f'https://discord.com/api/oauth2/authorize?client_id=893777032423571457&permissions=0&scope=bot')

    @commands.slash_command(description="Measures the Discord WebSocket protocol latency.")
    async def ping(self, ctx):
        await ctx.respond(f'My ping is {round(self.bot.latency*1000, 2)} ms!')

    @commands.slash_command(description="Deletes a number of messages.")
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount)
        if amount>1:
            await ctx.respond(f"{amount} messages were deleted.", delete_after=1)
        else:
            await ctx.respond(f"{amount} message was deleted.", delete_after=1)

    #validates the existence of ctx.author.voice.channel
    def in_voice_channel():
        def predicate(ctx):
            return ctx.author.voice and ctx.author.voice.channel
        return check(predicate)

    @in_voice_channel()
    @commands.slash_command(description="Moves connected members to a different voice channel.")
    async def move(self, ctx, *, channel : discord.VoiceChannel):
        for members in ctx.author.voice.channel.members:
            await members.move_to(channel)

    @commands.slash_command(description="Displays information about a member.")
    async def userinfo(self, ctx, member: discord.Member):
        member = ctx.author if not member else member
        roles = [role for role in member.roles]
        embed = discord.Embed(colour=member.colour)
        embed.set_author(name=f"User Info - {member}")
        embed.set_thumbnail(url=member.avatar)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.add_field(name="ID:", value=member.id)
        embed.add_field(name="Nickname:", value=member.display_name, inline="False")
        embed.add_field(name="Created On:", value=member.created_at.strftime("%a, %d, %B, %Y, %I:%M %p UTC"), inline="False")
        embed.add_field(name="Joined On:", value=member.joined_at.strftime("%a, %d, %B, %Y, %I:%M %p UTC"), inline="False")
        embed.add_field(name=f"Roles ({len(roles)})", value=" ".join([role.mention for role in roles]), inline="False")
        embed.add_field(name="Highest Role:", value=member.top_role.mention, inline="False")
        embed.add_field(name="Bot:", value=member.bot, inline="False")
        await ctx.respond(embed=embed)

    @discord.slash_command(description="Fetches Anime Search results from MyAnimeList.net")
    async def animesearch(self, ctx, *, an: str, ):
        start = time.time()
        search = AnimeSearch(f"{an}") #search for "cowboy bebop"
        id_ = search.results[0].mal_id
        url_ = search.results[0].url
        img_url = search.results[0].image_url
        ti = search.results[0].title
        sy = search.results[0].synopsis
        ty = search.results[0].type
        ep = search.results[0].episodes
        sc = search.results[0].score
        anime = Anime(id_)
        st = anime.status
        ai = anime.aired
        ra = anime.rank
        embed = discord.Embed(colour=ctx.author.colour)
        embed.set_thumbnail(url=img_url)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.add_field(name="Anime Name:", value=ti, inline="False")
        embed.add_field(name="Synopsis:", value=sy, inline="False")
        embed.add_field(name="Contd:", value=url_, inline="False")
        embed.add_field(name="Type", value=ty, inline="False")
        embed.add_field(name="Episodes:", value=ep, inline="False")
        embed.add_field(name="Score:", value=sc, inline="False")
        embed.add_field(name="Status:", value=st, inline="False")
        embed.add_field(name="MAL_ID:", value=id_, inline="False")
        embed.add_field(name="Aired:", value=ai, inline="False")
        embed.add_field(name="Rank:", value=ra, inline="False")
        await ctx.respond(embed=embed)

    @discord.slash_command(description="Fetches Manga Search results from MyAnimeList.net")
    async def mangasearch(self, ctx, *, an: str, ):
        start = time.time()
        search = MangaSearch(f"{an}") #search for "cowboy bebop"
        id_ = search.results[0].mal_id
        url_ = search.results[0].url
        img_url = search.results[0].image_url
        ti = search.results[0].title
        sy = search.results[0].synopsis
        ty = search.results[0].type
        vol = search.results[0].volumes
        sc = search.results[0].score
        manga = Manga(id_)
        st = manga.status
        ra = manga.rank
        ch = manga.chapters
        vol = manga.volumes
        embed = discord.Embed(colour=ctx.author.colour)
        embed.set_thumbnail(url=img_url)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.add_field(name="Manga Name:", value=ti, inline="False")
        embed.add_field(name="Synopsis:", value=sy, inline="False")
        embed.add_field(name="Contd:", value=url_, inline="False")
        embed.add_field(name="Type", value=ty, inline="False")
        embed.add_field(name="Episodes:", value=vol, inline="False")
        embed.add_field(name="Score:", value=sc, inline="False")
        embed.add_field(name="Status:", value=st, inline="False")
        embed.add_field(name="MAL_ID:", value=id_, inline="False")
        embed.add_field(name="Chapters:", value=ch, inline="False")
        embed.add_field(name="Volumes:", value=vol, inline="False")
        embed.add_field(name="Rank:", value=ra, inline="False")
        await ctx.respond(embed=embed)
    
    '''
    @commands.slash_command()
    async def rumble(self, ctx):
        #guild = ctx.guild
        #voice_client: discord.VoiceClient = discord.utils.get(commands.voice_clients, guild=guild)
        #audio_source = discord.FFmpegPCMAudio('rumbling.mp3')
        vc = await ctx.author.channel.connect()
        #if not voice_client.is_playing():
            #voice_client.play(audio_source, after=None)
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source="rumbling.mp3"))
    '''

    '''
    @commands.slash_command()
    async def jadisconnectho(self, ctx : discord.Context, user : discord.Member = None):
        if user==None:
            user=ctx.author
        member = ctx.author if not user else user
        if user.voice is None:
            await ctx.response("Andha saala")
        elif ctx.author.voice is None:
            await ctx.respond("Tor baap ke emon kyalabo na shuor er bachha")
        else:
            roles = [role for role in member.roles]
            embed = discord.Embed(colour=member.colour, timestamp=ctx.message.created_at)
            embed.set_author(name=f"Gracefully Disconnected : {member}")
            embed.set_thumbnail(url=member.avatar_url)
            embed.set_footer(text=f"Deemed Undeserving By {ctx.author}", icon_url=ctx.author.avatar_url)
            embed.add_field(name="Undeserving Idiot :", value=member.display_name, inline="False")
            embed.add_field(name="Disgracing the Role :", value=member.top_role.mention, inline="False")
            embed.add_field(name="Unimportant user:", value=member, inline="False")
            await ctx.respond(embed=embed)
            await user.move_to(None)
    '''

def setup(bot):
    bot.add_cog(misc(bot))