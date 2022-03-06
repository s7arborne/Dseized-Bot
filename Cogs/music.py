import discord
from discord.ext import commands
import asyncio
import itertools
import sys
import traceback
from async_timeout import timeout
from functools import partial
from youtube_dl import YoutubeDL

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ffmpegopts = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = YoutubeDL(ytdlopts)

class VoiceConnectionError(commands.CommandError):
    """Custom Exception class for connection errors."""

class InvalidVoiceChannel(VoiceConnectionError):
    """Exception for cases of invalid Voice Channels."""

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        await ctx.respond(f'```ini\n[Added {data["title"]} to the Queue.]\n```')

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)


class MusicPlayer(commands.Cog):
    """The class that is assigned to each guild using the bot for music.
    It implements a queue and loop, which allows for different guilds to listen to different playlists simultaneously.
    It's instance is destroyed when the bot disconnects from the voice."""

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    def destroy(self, guild):
        """Disconnect and cleanup the player."""
        return self.bot.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    """Music related commands."""

    __slots__ = ('bot', 'players')

    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del self.players[guild.id]
        except KeyError:
            pass

    async def __local_check(self, ctx):
        """A local check which applies to all commands in this cog."""
        if not ctx.guild:
            raise commands.NoPrivateMessage
        return True

    async def __error(self, ctx, error):
        """A local error handler for all errors arising from commands in this cog."""
        if isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.send('This command can not be used in Private Messages.')
            except discord.HTTPException:
                pass
        elif isinstance(error, InvalidVoiceChannel):
            await ctx.send('Error connecting to Voice Channel. '
                           'Please make sure you are in a valid channel or provide me with one')

        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one."""
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.slash_command(description="Joins the voice channel user is connected to.")
    async def join(self, ctx):
        try:
            channel = ctx.author.voice.channel
        except AttributeError:
            await ctx.respond("You have to be connected to a voice channel to use this command.")
            raise InvalidVoiceChannel("No channel to join.")
        vc = ctx.voice_client
        if vc:
            if vc.channel.id == channel.id:
                return
            try:
                await vc.move_to(channel)
            except asyncio.TimeoutError:
                await ctx.respond("Connection timed out.")
                raise VoiceConnectionError(f"Moving to channel: <{channel}> timed out.")
        else:
            try:
                await channel.connect()
            except asyncio.TimeoutError:
                await ctx.respond("Connection timed out.")
                raise VoiceConnectionError(f"Connecting to channel: <{channel}> timed out.")
        await ctx.respond(f'Connected to: **{channel}**')

    @commands.slash_command(description="Plays a song.")
    async def play(self, ctx, *, search: str):
        vc = ctx.voice_client
        if ctx.author.voice is None:
            await ctx.respond("You are not connected to any voice channel.")
        else:
            #await ctx.invoke(self.join)
            player = self.get_player(ctx)
            # If download is False, source will be a dict which will be used later to regather the stream.
            # If download is True, source will be a discord.FFmpegPCMAudio with a VolumeTransformer.
            source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)
            await player.queue.put(source)

    @commands.slash_command(description="Pauses the currently playing song.")
    async def pause(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.respond("I am not playing anything currently!")
        elif vc.is_paused():
            return
        vc.pause()
        await ctx.respond(f"**`{ctx.author}`**: Paused the song!")

    @commands.slash_command(description="Resumes the currently paused song.")
    async def resume(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.respond("I am not playing anything currently!")
        elif not vc.is_paused():
            return
        vc.resume()
        await ctx.respond(f"**`{ctx.author}`**: Resumed the song!")

    @commands.slash_command(description="Skips the currently playing song.")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.respond("I am not playing anything currently!")
        if vc.is_paused():
            pass
        elif not vc.is_playing():
            return
        vc.stop()
        await ctx.respond(f"**`{ctx.author}`**: Skipped the song!")

    @commands.slash_command(description="Displays the list of songs in queue.")
    async def queue(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.respond("I am not connected to voice currently!")
        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.respond("There are no more songs in queue.")

        #grab up to 5 entries from the queue
        upcoming = list(itertools.islice(player.queue._queue, 0, 5))
        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f"Upcoming - Next {len(upcoming)}", description=fmt)

        await ctx.respond(embed=embed)

    @commands.slash_command(description="Displays information about the currently playing song.")
    async def now_playing(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.respond("I am not connected to voice currently!")
        player = self.get_player(ctx)
        if not player.current:
            return await ctx.respond("I am not playing anything currently!")

        try:
            #remove our previous now_playing message.
            await player.np.delete()
        except discord.HTTPException:
            pass

        player.np = await ctx.respond(f"**Now Playing:** `{vc.source.title}` "
                                   f"requested by `{vc.source.requester}`")

    @commands.slash_command(description="Customises the player volume in the range 1 to 100.")
    async def volume(self, ctx, *, vol: float):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.respond("I am not connected to voice currently!")
        if not 0 < vol < 101:
            return await ctx.respond("Please enter a value between 1 and 100.")
        player = self.get_player(ctx)
        if vc.source:
            vc.source.volume = vol / 100
        player.volume = vol / 100
        await ctx.respond(f"**`{ctx.author}`**: Set the volume to **{vol}%**")

    @commands.slash_command(description="The bot will leave the voice channel, also deleting any queue songs and settings.")
    async def leave(self, ctx):
        channel = ctx.author.voice.channel
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.respond('I am not currently playing anything!')
        await self.cleanup(ctx.guild)
        await ctx.respond(f"Disconnected from: **{channel}**")
    
def setup(bot):
    bot.add_cog(Music(bot))