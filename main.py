import os

import discord
from discord.ext import commands
import logging
import asyncio
from yandex_music import Client


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intents = discord.Intents.default()
intents.members = True
server, server_id, channel_name = None, None, None
domains = ['https://music.yandex.ru', 'http://music.yandex.ru']
client = Client().init()


async def check_domains(link):
    for x in domains:
        if link.startswith(x):
            print(link.startswith(x))
            return True
        return False


class RandomThings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='play')
    async def play(self, ctx, command=None):
        global server, server_id, channel_name
        author = ctx.author
        # if command is None:
        #     server = ctx.guild
        #     channel_name = author.voice.channel.name
        #     voice_channel = discord.utils.get(server.voice_channels, name=channel_name)
        params = command.split(' ')
        if len(params) == 1:
            source = params[0]
            server = ctx.guild
            channel_name = author.voice.channel.name
        else:
            await ctx.channel.send(f'Команда имеет лишние данные')
            return
        voice_channel = discord.utils.get(server.voice_channels, name=channel_name)
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice is None:
            await voice_channel.connect()
            voice = discord.utils.get(bot.voice_clients, guild=server)
        if source is None:
            pass
        elif source.startswith('http'):
            if not await check_domains(source):
                await ctx.channel.send('Неверно указана ссылка с сервера Яндекс.Музыки')
                return
            source = source.split('/')
            print(source)
            album, track = source[4], source[6]
            print(client.tracks([f'{track}:{album}'])[0].download('song.mp3', bitrate_in_kbps=128))
            voice.play(discord.FFmpegPCMAudio('song.mp3'))
        else:
            await ctx.channel.send('Неверный протокол')
            return

    @commands.command(name='pause')
    async def pause(self, ctx):
        print(1)
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_playing():
            voice.pause()
        else:
            await ctx.channel.send('Музыка уже приостановлена')

    @commands.command(name='resume')
    async def resume(self, ctx):
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_playing():
            await ctx.channel.send('Музыка уже воспроизводится')
        else:
            voice.resume()

    @commands.command(name='stop')
    async def stop(self, ctx):
        voice = discord.utils.get(bot.voice_clients, guild=server)
        voice.stop()

    @commands.command(name='leave')
    async def leave(self, ctx):
        global server, channel_name
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_connected():
            await voice.disconnect()
        else:
            await ctx.channel.send('Бот не находится в голосовом канале')


bot = commands.Bot(command_prefix='!', intents=intents)
bot.add_cog(RandomThings(bot))
TOKEN = ""
bot.run(TOKEN)