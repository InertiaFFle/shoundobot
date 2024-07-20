import asyncio
import json
import os
import platform
import random
import subprocess
import sys
from glob import glob
from threading import Thread
from time import gmtime, strftime, time

import discord
import psutil
import pytubefix
from discord import ActivityType, ButtonStyle, Status
from discord.ext import commands
from discord.ext.pages import Page, Paginator, PaginatorButton
from dotenv import load_dotenv
from flask import Flask
from pytubefix.innertube import _default_clients

_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS"))
PREFIX = os.getenv("PREFIX")
PRESENCE = os.getenv("PRESENCE")
PORT = os.getenv("PORT")
STORAGE_PATH = "storage"

class Shoundobot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.musicbox_list = []
        self.musicbox_index = 0
        self.musicbox_looping = False
        self.voice_channel = None
        self.next_song = asyncio.Event()
        self.playing_lock = asyncio.Lock()
        self.navigator_buttons = [
            PaginatorButton("first", label="<<", style=ButtonStyle.gray),
            PaginatorButton("prev", label="<", style=ButtonStyle.gray),
            PaginatorButton("page_indicator", style=ButtonStyle.gray, disabled=True),
            PaginatorButton("next", label=">", style=ButtonStyle.gray),
            PaginatorButton("last", label=">>", style=ButtonStyle.gray),
        ]
        self.start_time = time()
        self.version = self._get_version()
        self.advertisement = False
        
    def _get_version(self):
        try:
            result = subprocess.run(['git', 'describe', '--tags'], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"
        
    async def on_ready(self):
        activity = discord.Activity(type=discord.ActivityType.listening, name=PRESENCE)
        await self.change_presence(status=discord.Status.dnd, activity=activity)
        print(f"{self.user} is ready")
        
    async def show_ads(self, ctx):
        ads_list = [
            "want a break from the ads? if you tap now to watch a short video, youll receive 30 minutes of ad free music",
            "this video is sponsored by nerdvpn. staying safe online is an ever growing difficulty and you could be exploited by hackers. nerdvpn allows you to change your ip address, making you harder to track, securing your privacy. check out the link in the description to get 20% off for the first two months and thank you to nerdvpn for sponsoring this video",
            "grobhub perks give you deals on the food you love\nthe kind of deals that make you boogie.\n[music]\npurple guy: *bites borger and dances*\nsushi guys: *appear and eat the sushi*\nsalad girl: *eats salad and stands up*\nmilkshake girl: *does the splits and slurps milkshake*\neveryone: *dances all at once*",
            "finish your mid-fade without pausing. try shoundobot premium on us. and style, uninterrupted",
            "whopper whopper :hamburger: whopper whopper :hamburger: junior :boy: double :woman_facepalming: triple :man_facepalming: whopper :hamburger: flame grill :fire: taste with perfect toppers :heart_eyes: i rule :crown: this day :sunglasses: lettuce :leafy_green: mayo pickle :tomato: ketchup :tomato: its okay if i don’t want that :no_entry: impossible :exploding_head: bow wow bacon :bacon: whopper :hamburger: any whopper :hamburger: my way :kissing_heart: you rule :eyes: your season today :maple_leaf: at bk :prince: have it your way :pleading_face: you rule :fire:",
            "plz vote my bot!!11!! in top.gg for premuim perkss11!!1 like lik3 uhhhhjj !feet command wwhattt?:=]-p[!:!",
            "playing the next video will charge you 5$, hurry up and subscribe to shoundobot premium for unlimited streaming!"
        ]
        if random.choice([True, False]):
            await ctx.send(f"**:hamburger: | advertisement time!**\n>>> {random.choice(ads_list)}", delete_after=60)
        
class MusicboxCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        
        if not self.bot.musicbox_list:
            await ctx.send("**:o: | music box is empty :(**")
            return
        
        async with ctx.typing():
            loop_status = "looping" if self.bot.musicbox_looping else "not looping"
            index_status = f"{self.bot.musicbox_index}/{len(self.bot.musicbox_list)-1}"
            header = f"({loop_status}) `[{index_status}]`"
            
            queue_list = []
            for index, video in enumerate(self.bot.musicbox_list):
                queue_list.append(f"**`[{index:02}]` | {video[0]}**")
            chunks = [queue_list[i:i + 10] for i in range(0, len(queue_list), 10)]
            
            pages = []
            for chunk in chunks:
                content = "\n".join(chunk)
                page = Page(content=f"**:notes: | music box {header}**\n\n{content}")
                pages.append(page)
            
        await Paginator(
            pages=pages,
            custom_buttons=self.bot.navigator_buttons,
            show_indicator=True,
            use_default_buttons=False
            ).send(ctx)
            
    @commands.command(aliases=["cq"])
    async def clear_queue(self, ctx):
        
        if not self.bot.musicbox_list:
            await ctx.send(f"**:anger: | the music box is empty!!**")
            return
        
        self.bot.musicbox_list = []
        self.bot.musicbox_index = 0
        await ctx.send(f"**:o: | music box cleared >:D**")
        
    @commands.command(aliases=["sh"])
    async def shuffle_queue(self, ctx):
        
        if not self.bot.musicbox_list:
            await ctx.send("**:anger: | the music box is emptyy... how bout u shuffle deeznuts?**")
            return
        
        if len(self.bot.musicbox_list) == 1:
            await ctx.send("**:anger: | shuffwing 1 song for youuu :D**")
            return
        
        random.shuffle(self.bot.musicbox_list)
        await ctx.send("**:twisted_rightwards_arrows: | i shuffwled the music box :DD**")
        
    @commands.command(aliases=["l"])
    async def loop_queue(self, ctx):
        self.bot.musicbox_looping = not self.bot.musicbox_looping
        
        if self.bot.musicbox_looping:
            await ctx.send("**:repeat: | the music box is now looping ;)**")
        else:
            await ctx.send("**:fast_forward: | the music box is no longer looping ;(**")

    @commands.command(aliases=["a"])
    async def add(self, ctx, *, query=None):
        
        if not query:
            await ctx.send("**:anger: | please provide a url or search!**")
            return
        
        async with ctx.typing():
            try:
                if "https://" not in query:
                    videos = pytubefix.Search(query).videos[:1]
                elif "watch" in query:
                    videos = [pytubefix.YouTube(query)]
                elif "playlist" in query:
                    playlist = pytubefix.Playlist(query)
                    videos = playlist.videos
                else:
                    raise
            except Exception:
                await ctx.send("**:anger: | no, no! that's an invalid youtube queryy!**")
                return
        
            for video in videos:
                self.bot.musicbox_list.append([video.title, video.author, video.watch_url])
            
        if len(videos) == 1:
            await ctx.send(f"**:arrow_up: | queued:\n`{videos[0].title}`\nby `{videos[0].author}`**")
        else:
            await ctx.send(f"**:arrow_double_up: | added `{len(videos)}` songs to the music box :D**")
    
    @commands.command(aliases=["r"])
    async def remove(self, ctx, index=None):
        
        if not index:
            index = 0
        
        if not self.bot.musicbox_list:
            await ctx.send(f"**:anger: | nuhhh, the music box is empty, tsk tsk...**")
            return
            
        try:
            if int(index) < 0:
                raise ValueError("negative numbers")
            video = self.bot.musicbox_list.pop(int(index))
            await ctx.send(f"**:arrow_down: | removed `{video[0]}` from the music box D:**")
        except (TypeError, ValueError, IndexError):
            max_index = len(self.bot.musicbox_list) - 1
            await ctx.send(f"**:anger: | you must put a valid index!! (0 to {max_index} only!)**")
        except Exception as error:
            await ctx.send(f"**:bangbang: | unexpected error occurred!\n```\n{error}\n```")

    @commands.command(aliases=["np"])
    async def now_playing(self, ctx):
        
        if not self.bot.musicbox_list:
            await ctx.send(f"**:anger: | but nobody came**")
            return
        
        if not self.bot.musicbox_list:
            await ctx.send(f"**:anger: | but nobody came**")
            return
        
        await ctx.send(f"**:musical_note: | now playing:\n`{current_video.title}`\n(`{current_video.author}`)**")
        
class MusicplayerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def _reset_musicbox(self, destroy_box=False):
        if destroy_box:
            self.bot.musicbox_list = []
        if self.bot.voice_channel:
            await self.bot.voice_channel.disconnect()
        self.bot.voice_channel = None
        self.bot.musicbox_index = 0

    async def _musicbox_player(self, ctx):
        async with self.bot.playing_lock:
            while True:
                try:
                    if (
                        not self.bot.voice_channel or
                        not self.bot.voice_channel.is_connected() or
                        not self.bot.musicbox_list
                    ):
                        await self._reset_musicbox()
                        return
                    
                    if self.bot.musicbox_index > len(self.bot.musicbox_list) - 1 :
                        if self.bot.musicbox_looping:
                            self.bot.musicbox_index = 0
                            await ctx.send(f"**:arrows_counterclockwise: | looping back to `[00]` :D**", delete_after=30)
                        else:
                            await self._reset_musicbox()
                            await ctx.send(f"**:stop_button: | music box finishedd :(**")
                            return
                    
                    # download
                    async with ctx.typing():
                        if self.bot.advertisement:
                            await self.bot.show_ads(ctx)
                        current_video = pytubefix.YouTube(self.bot.musicbox_list[self.bot.musicbox_index][2])
                        audio_stream = current_video.streams.filter(only_audio=True).order_by("abr").desc().first()
                        audio_file = audio_stream.download(output_path=STORAGE_PATH)
                    
                    # stream
                    message = await ctx.send(f"**:musical_note: | now playing:\n`{current_video.title}`\n(`{current_video.author}`)**")
                    self.bot.voice_channel.play(discord.FFmpegPCMAudio(audio_file), after=lambda e: self.bot.loop.call_soon_threadsafe(self.bot.next_song.set))
                    self.bot.next_song.clear()
                    await self.bot.next_song.wait()
                    
                    # after stream
                    await message.delete()
                    self.bot.musicbox_index += 1
                    os.remove(audio_file)
                except Exception as error:
                    await self._reset_musicbox()
                    await ctx.send(f"**:bangbang: | oh nooo! an error occured!!**\n```\n{error}\n```")
                    return
                    
    @commands.command(aliases=["p"])
    async def play(self, ctx):
        
        if not self.bot.musicbox_list:
            await ctx.send("**:anger: | music box is empty! fill it first!!**")
            return
        
        if not ctx.author.voice:
            await ctx.send("**:anger: | nuh uh, you need to be in a voice channel first!**")
            return
        
        if not self.bot.voice_channel:
            voice_channel = await ctx.author.voice.channel.connect()
            self.bot.voice_channel = voice_channel
        
        if ctx.author.voice.channel != self.bot.voice_channel.channel or self.bot.voice_channel.is_playing():
            await ctx.send(f"**:anger: | im playing in <#{self.bot.voice_channel.channel.id}>!**")
            return
        
        if self.bot.playing_lock.locked():
            await ctx.send("**:anger: | music player is already running!**")
            return
        
        await self._musicbox_player(ctx)
    
    @commands.command(aliases=["dc"])
    async def disconnect(self, ctx):
        if not self.bot.voice_channel or not self.bot.voice_channel.is_connected():
            await ctx.send("**:anger: | im not in any voice channel?!**")
            return
        
        if self.bot.voice_channel.is_playing():
            self.bot.voice_channel.stop()
            
        await self._reset_musicbox()
        await ctx.send("**:wave: | disconnected :D**")
        
    @commands.command(aliases=["s"])
    async def skip(self, ctx, index=None):
        if not index:
            index = self.bot.musicbox_index + 1
            
        if not self.bot.voice_channel or not self.bot.voice_channel.is_connected():
            await ctx.send("**:anger: | im not in any voice channel....**")
            return
        
        if not self.bot.musicbox_list:
            await ctx.send("**:anger: | skip what?? the music box is emptyy >:(**")
            return
        
        try:
            if int(index) < 0:
                raise ValueError("negative numbers")
            self.bot.musicbox_index = int(index)
            ctx.voice_client.stop()
            await ctx.send("**:fast_forward: | skipped the current song!**")
        except (TypeError, ValueError, IndexError):
            max_index = len(self.bot.musicbox_list) - 1
            await ctx.send(f"**:anger: | you must put a valid index!! (0 to {max_index} only!)**")
        except Exception as error:
            await ctx.send(f"**:bangbang: | unexpected error occurred!\n```\n{error}\n```")

async def is_bot_admin(ctx):
    return ctx.author.id in ADMIN_IDS

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.check
    async def not_in_dm(self, ctx):
        return ctx.guild is not None
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            if not await self.not_in_dm(ctx):
                return
            elif not await self.is_bot_admin(self, ctx):
                await ctx.send("**:no_entry_sign: | youre not a bot admin :P**")
        else:
            raise error

    @commands.command(aliases=["rr"])
    @commands.check(is_bot_admin)
    async def restart_bot(self, ctx):
        await ctx.send("**:pink_heart: | restarting....**")
        os.execv(sys.executable, ["python"] + sys.argv)

    @commands.command(aliases=["ss"])
    @commands.check(is_bot_admin)
    async def stats(self, ctx):
        uptime = time() - self.bot.start_time
        uptime_str = strftime("%H:%M:%S", gmtime(uptime))
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info().rss
        ping = self.bot.latency * 1000
        
        stats_message = (
            "```\n"
            "SHOUNDOBOT\n"
            f"version:         {self.bot.version}\n"
            f"uptime:          {uptime_str}\n"
            f"ping:            {ping:.2f} ms\n"
            "\n"
            "MEMORY\n"
            f"total:           {mem.total / (1024 ** 3):.2f} GB\n"
            f"using:           {mem.used / (1024 ** 3):.2f} GB ({mem.percent}%)\n"
            f"usage:           {mem_info / (1024 * 1024):.2f} MB\n"
            "\n"
            "DISK\n"
            f"total:           {disk.total / (1024 ** 3):.2f} GB\n"
            f"used:            {disk.used / (1024 ** 3):.2f} GB ({disk.percent}%)\n"
            "```"
        )
        
        await ctx.send(stats_message)
    
    @commands.command(aliases=["sa"])
    @commands.check(is_bot_admin)
    async def show_ads_toggle(self, ctx):
        self.bot.advertisement = not self.bot.advertisement
        await ctx.send(f"**:hamburger: | advertisement: `{self.bot.advertisement}`**")

        
class WebApp:
    def __init__(self, host="0.0.0.0", port=PORT):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self._setup_routes()
    
    def _setup_routes(self):
        @self.app.route("/")
        def home():
            return "<b><center> Shoundobot :) </center></b>"

    def run(self):
        self.app.run(host=self.host, port=self.port)
        
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = Shoundobot(command_prefix=PREFIX, intents=intents)

bot.add_cog(MusicplayerCog(bot))
bot.add_cog(MusicboxCog(bot))
bot.add_cog(AdminCog(bot))

web_app = WebApp()

if __name__ == "__main__":
    
    if not os.path.exists(STORAGE_PATH):
        os.makedirs(STORAGE_PATH)
    
    for file in glob(f"{STORAGE_PATH}/*"):
        os.remove(file)
    
    thread = Thread(target=web_app.run)
    thread.start()
    bot.run(TOKEN)