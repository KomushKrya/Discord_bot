import discord
from discord.ext import commands
import logging
from yandex_music import Client


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


intents = discord.Intents.default()
intents.members = True
domains = ['https://music.yandex.ru', 'http://music.yandex.ru']
client = Client().init()
server, server_id, channel_name = None, None, None
queue = []
start_playing = False
bot = commands.Bot(command_prefix='!', intents=intents)


async def check_domains(link):
    for x in domains:
        if link.startswith(x):
            return True
        return False


async def add_queue(source):
    if len(source) == 7:
        album, track = source[4], source[6]
        return [f'{track}:{album}']
    elif len(source) == 5:
        tracks = []
        album = source[4]
        album_song = client.albums_with_tracks(album)
        for i, volume in enumerate(album_song.volumes):
            for j in range(len(volume)):
                tracks.append(f'{volume[j]["id"]}:{album}')
        return tracks


class MusicCommands(commands.Cog):
    def __init__(self, ds_bot):
        self.bot = ds_bot

    @commands.command(name='play')
    async def play(self, ctx, command=None):
        global server, server_id, channel_name, queue, start_playing
        author = ctx.author
        command = command.split(' ')
        if len(command) != 1:
            await ctx.channel.send(f'Команда имеет лишние данные')
            return
        else:
            source = command[0]
            server = ctx.guild
            channel_name = author.voice.channel.name
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
            queue += await add_queue(source)
            print(queue, 123)
            if not start_playing:
                start_playing = True
                while True:
                    if queue and not voice.is_playing():
                        print(2)
                        song = [queue.pop(0)]
                        print(song, 321)
                        client.tracks(song)[0].download('song.mp3', bitrate_in_kbps=128)
                        voice.play(discord.FFmpegPCMAudio('song.mp3'))
                    if not queue and not voice.is_playing():
                        start_playing = False
        else:
            await ctx.channel.send('Неверный протокол')
            return

    @commands.command(name='pause')
    async def pause(self, ctx):
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
    async def stop(self):
        global queue, start_playing
        queue, start_playing = [], False
        voice = discord.utils.get(bot.voice_clients, guild=server)
        voice.stop()

    @commands.command(name='leave')
    async def leave(self, ctx):
        global server, channel_name, queue, start_playing
        queue, start_playing = [], False
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_connected():
            queue, start_playing = [], False
            await voice.disconnect()
        else:
            await ctx.channel.send('Бот не находится в голосовом канале')

    @commands.command(name='skip')
    async def leave(self, ctx):
        global server, channel_name, queue, start_playing
        queue.pop()
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_connected():
            queue, start_playing = [], False
            await voice.disconnect()
        else:
            await ctx.channel.send('Бот не находится в голосовом канале')


bot.add_cog(MusicCommands(bot))
TOKEN = "OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.uhwFKqUvMunyou7w8jYKo2lkrdg"
bot.run(TOKEN)
# OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.uhwFKqUvMunyou7w8jYKo2lkrdg
