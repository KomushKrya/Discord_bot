import os

import discord
from discord.ext import commands
import logging
import asyncio
import youtube_dl

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
server, server_id, channel_name = None, None, None
domains = ['https://www.youtube.com', 'http://www.youtube.com', 'https://youtu.be', 'http://youtu.be']


async def check_domains(link):
    for x in domains:
        if link.startswith('x'):
            return True
        return False


class RandomThings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='play')
    async def play(self, ctx, command=None):
        global server, server_id, channel_name
        source = None
        author = ctx.author
        if command is None:
            server = ctx.guild
            channel_name = author.voice.channel.name
            voice_channel = discord.utils.get(server.voice_channels, name=channel_name)
        params = command.split(' ')
        if len(params) == 1:
            source = params[0]
            server = ctx.guild
            channel_name = author.voice.channel.name
            voice_channel = discord.utils.get(server.voice_channels, name=channel_name)
        elif len(params) == 3:
            server_id, voice_id, file_name = tuple(params)
            try:
                server_id = int(server_id)
                voice_id = int(voice_id)
            except ValueError:
                await ctx.channel.send('Не робит')
                return
            server = bot.get_guild(server_id)
            voice_channel = discord.utils.get(server.voice_channels, id=voice_id)
        else:
            await ctx.channel.send(f'Не робит, но 2')
            return
        print(1)
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice is None:
            await voice_channel.connect()
            voice = discord.utils.get(bot.voice_clients, guild=server)
        if source is None:
            pass
        elif source.startswith('http'):
            if not check_domains(source):
                await ctx.channel.send('Не робит, но 3')
                return
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192'
                    }
                ]
            }
            mp3 = True
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                print(111, source)
                ydl.download([source])
                print(222)
            for file in os.listdir('./'):
                if file.endswith('.mp3'):
                    os.rename(file, 'song.mp3')
                if file.endswith('.webm'):
                    os.rename(file, 'song.webm')
                    mp3 = False
            print(12345)
            if mp3:
                voice.play(discord.FFmpegPCMAudio('song.mp3'))
            else:
                voice.play(discord.FFmpegPCMAudio('song.webm'))
        else:
            voice.play(discord.FFmpegPCMAudio(f'music/{source}'))


bot = commands.Bot(command_prefix='!', intents=intents)
bot.add_cog(RandomThings(bot))
TOKEN = "OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.i8OGWo5bKIeSRoTA-JvHwLFKlxI"
bot.run(TOKEN)

#OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.i8OGWo5bKIeSRoTA-JvHwLFKlxI