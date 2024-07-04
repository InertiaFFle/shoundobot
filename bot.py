import json
import os
import sys
import time
import asyncio
import random
import platform
import glob

import discord
from discord.ext import commands
from discord.ext.pages import Paginator, Page, PaginatorButton
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import psutil
import pytube
from pytube.innertube import _default_clients

load_dotenv()
TOKEN = os.getenv('TOKEN')
ADMIN_IDS = json.loads(os.getenv('ADMIN_IDS'))
STORAGE_PATH = "storage"

start_time = time.time()

_default_clients["ANDROID_MUSIC"] = _default_clients["ANDROID_CREATOR"]

bot = commands.Bot(command_prefix='.', intents=discord.Intents.all())
bot.voice_channel = None

bot.queue_box = []
bot.queue_box_index = 0
bot.queue_loop = False

bot.custom_buttons = [
    PaginatorButton("first", label="<<", style=discord.ButtonStyle.gray),
    PaginatorButton("prev", label="<", style=discord.ButtonStyle.gray),
    PaginatorButton("page_indicator", style=discord.ButtonStyle.gray, disabled=True),
    PaginatorButton("next", label=">", style=discord.ButtonStyle.gray),
    PaginatorButton("last", label=">>", style=discord.ButtonStyle.gray),
]

if not os.path.exists(STORAGE_PATH):
    os.makedirs(STORAGE_PATH)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(aliases=["a"])
async def add(ctx, *, query):
    
    added_videos = []
    try: 
        if "https://" not in query:
            video = pytube.Search(query).results[0]
            added_videos.append(video)
        elif "watch" in query:
            video = pytube.YouTube(query)
            added_videos.append(video)
        elif "playlist" in query:
            playlist = pytube.Playlist(query)
            for video in playlist.videos:
                added_videos.append(video)
        else:
            raise
    except:
        await ctx.send("**:anger: | Invalid YouTube query!**")
        return
    
    for video in added_videos:
        bot.queue_box.append(video)
        
    content = f"**:eject: | Added `{len(added_videos)}` songs to queue box!**"
    if len(added_videos) == 1:
        content = f"**:eject: | Added to queue box:\n`{added_videos[0].title}`\nby `{added_videos[0].author}`**"
    await ctx.send(content)
    
@bot.command(aliases=["r"])
async def remove(ctx, index):
    try:
        video = bot.queue_box.pop(index)
        await ctx.send(f"**:wastebasket: | Removed from queue box `[{index:02}]`:\n`{video.title}`\nby `{video.author}`**")
    except:
        await ctx.send("**:anger: | Invalid index query!**")
    
@bot.command(aliases=["sh"])
async def shuffle(ctx):
    
    if not bot.queue_box:
        await ctx.send("**:thinking: | The queue box is empty. how about u shuffle deez nuts?**")
        return
    
    random.shuffle(bot.queue_box)
    await ctx.send("**:twisted_rightwards_arrows: | Shuffled queue box!**")
    
@bot.command(aliases=["c"])
async def clear(ctx):
    
    if not bot.queue_box:
        await ctx.send("**:thinking: | The queue box is already empty**")
        return
    
    bot.queue_box = []
    await ctx.send("**:wastebasket: | Cleared queue box!**")

@bot.command(aliases=["l"])
async def loop(ctx):
    
    bot.queue_loop = not bot.queue_loop
    
    if bot.queue_loop:
        await ctx.send("**:repeat: | Queue is now looping!**")
    else:
        await ctx.send("**:fast_forward: | Queue is no longer looping!**")

@bot.command(aliases=["q"])
async def queue(ctx):
    queue_list = []
    for index, video in enumerate(bot.queue_box):
        video.title = video.title[:27] + "..." if len(video.title) > 30 else video.title
        video.author = video.author[:27] + "..." if len(video.author) > 30 else video.author
        queue_list.append(f"**`[{index:02}]` - {video.title}\nby {video.author}**")
    
    if not queue_list:
        await ctx.send("**:o: | Queue box is empty :(**")
        return
    
    chunks = [queue_list[i:i + 10] for i in range(0, len(queue_list), 10)]
    
    pages = []
    loop_status = "looping" if bot.queue_loop else "not looping"
    index_status = f"{bot.queue_box_index}/{len(bot.queue_box)}"
    header = f"({loop_status}) `[{index_status}]`"
    for chunk in chunks:
        content = "\n".join(chunk)
        page = Page(content=f"**:notes: | Queue Box {header}**\n{content}")
        pages.append(page)
    
    await Paginator(
        pages=pages,
        custom_buttons=bot.custom_buttons,
        show_indicator=True,
        use_default_buttons=False
        ).send(ctx)
    
@bot.command(aliases=["np"])
async def now_playing(ctx):
    
    if not bot.voice_channel:
        await ctx.send("**:anger: | I'm not even connected to a voice channel!**")
        return
    
    if not bot.voice_channel.is_playing():
        await ctx.send("**:anger: | I'm not playing anything!**")
        return
    
    current_video = bot.queue_box[bot.queue_box_index]
    index_status = f"`[{bot.queue_box_index}/{len(bot.queue_box)}]`"
    await ctx.send(f"**:musical_note: | Currently playing {index_status}:\n{current_video.title}\nby `{current_video.author}`**")
    
@bot.command(aliases=["p"])
async def play(ctx):
    
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("**:anger: | You need to be in a voice channel to use this command!**")
        return
    
    if not bot.voice_channel:
        bot.voice_channel = await voice_channel.connect()
    
    if bot.voice_channel.is_playing():
        await ctx.send("**:anger: | I am already playing the queue!**")
        return
    
    if not bot.queue_box:
        await ctx.send("**:anger: | Queue box is empty!**")
        return
    
    await play_next_video(ctx)
    
@bot.command(aliases=["s"])
async def skip(ctx, index=None):
    
    if not bot.voice_channel.is_playing():
        await ctx.send("**:anger: | I'm not playing anything!**")
        return 
    
    if index:
        
        if not index.isdigit():
            await ctx.send("**:anger: | Index must be a number!**")
            return
        
        if (int(index) > len(bot.queue_box) - 1) or (int(index) < 0):
            await ctx.send("**:anger: | Index out of range!**")
            return
        
        bot.queue_box_index = index

    bot.queue_box_index += 1
    bot.voice_channel.stop()
    
@bot.command(aliases=["dc"])
async def disconnect(ctx):
    
    if not bot.voice_channel:
        await ctx.send("**:anger: | I'm not in a voice channel!**")
    
    bot.queue_box = []
    await bot.voice_channel.stop()
    await bot.voice_channel.disconnect()
    bot.voice_channel = None
    bot.queue_box_index = 0
    await ctx.send("**:ballot_box_with_check: | Disconnecting...**")

async def play_next_video(ctx):
        
    if (bot.queue_box_index + 1 > len(bot.queue_box)) and (not bot.queue_loop):
        await bot.voice_channel.disconnect()
        bot.voice_channel = None
        bot.queue_box_index = 0
        await ctx.send("**:ballot_box_with_check: | Queue finished! leaving the voice channel...**")
        return
    
    if (not bot.queue_box_index) and bot.queue_loop:
        bot.queue_loop = False
        await ctx.send("**:anger: | The queue is empty! I'm disabling the loop now**")
        return
    
    if (bot.queue_box_index > len(bot.queue_box) - 1):
        await ctx.send("**:ballot_box_with_check: | Queue finished! Looping to index 0...**")
        bot.queue_box_index = 0
    
    current_video = pytube.YouTube(bot.queue_box[bot.queue_box_index].watch_url)
    audio_stream = current_video.streams.filter(only_audio=True).order_by('abr').desc().first()
    audio_file = audio_stream.download(output_path=STORAGE_PATH)
    #bot.voice_channel.play(discord.FFmpegPCMAudio(audio_stream.url))
    bot.voice_channel.play(discord.FFmpegPCMAudio(audio_file))
    
    await ctx.send(f"**:musical_note: | Now playing:\n`{current_video.title}` by `{current_video.author}`**")
    
    while bot.voice_channel.is_playing():
        await asyncio.sleep(1)
    
    os.remove(audio_file)
    bot.queue_box_index += 1
    await play_next_video(ctx)
    
async def check_if_admin(ctx):
    if ctx.author.id not in ADMIN_IDS:
        return False
    return True

@bot.command(aliases=["rr"])
async def restart_bot(self, ctx):
    if not await check_if_admin(ctx):
        await ctx.send("missing perms")
        return
    print("bot restarting")
    await ctx.send("bot restarting")
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.command(name='stats', aliases=['ss'])
async def stats(ctx):
    if not await check_if_admin(ctx):
        await ctx.send("missing perms")
        return
    uname = platform.uname()
    uptime = time.time() - start_time
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    cpu_info = f"Physical cores: {psutil.cpu_count(logical=False)}, Total cores: {psutil.cpu_count(logical=True)}, Max Frequency: {psutil.cpu_freq().max:.2f}Mhz"
    
    stats_message = (
        f"**System Information**\n"
        f"**OS**: {uname.system} {uname.release} ({uname.version})\n"
        f"**Node**: {uname.node}\n"
        f"**Machine**: {uname.machine}\n"
        f"**Processor**: {uname.processor}\n"
        f"**CPU**: {cpu_info}\n"
        f"**Uptime**: {uptime_str}\n"
        f"**Memory**: {mem.total / (1024 ** 3):.2f} GB\n"
        f"**Memory Used**: {mem.used / (1024 ** 3):.2f} GB ({mem.percent}%)\n"
        f"**Disk**: {disk.total / (1024 ** 3):.2f} GB\n"
        f"**Disk Used**: {disk.used / (1024 ** 3):.2f} GB ({disk.percent}%)"
    )
    
    await ctx.send(stats_message, delete_after=30)

@bot.command(aliases=["ls"])
async def list_files(ctx):
    files = glob.glob(os.path.join(STORAGE_PATH, '*'))
    await ctx.send(f"Files in storage:\n```\n{', '.join(files)}\n```")

@bot.command(aliases=["lsd"])
async def delete_files(ctx):
    files = glob.glob(os.path.join(STORAGE_PATH, '*'))
    for file_path in files:
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            await ctx.send(f"Failed to delete '{file_path}': {str(e)}")
    
    await ctx.send(f"All files in directory '{STORAGE_PATH}' have been deleted.")

app = Flask('')

@app.route('/')
def home():
    return "<b> <center> Shoundobot </center> </b>"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
    
keep_alive()
bot.run(TOKEN)
bot.run("")
