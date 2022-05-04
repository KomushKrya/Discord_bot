import discord
from discord.ext import commands
import logging
from database import DataBase
from PIL import Image
import requests
import random
from yandex_music import Client
import datetime as dt

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

db = DataBase('data/discord_bot.db')

city_game = False
channel_game = None
named_cities = []
reactions = {'👌': 'Okay',
             '👎': 'фигово'}
roles_for_buying = {'Хорошая роль': 500,
                    'Роль похуже': 200}

server, server_id, channel_name = None, None, None
domains = ['https://music.yandex.ru', 'http://music.yandex.ru']
client = Client().init()

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


async def check_count(ctx):
    """Делает проверку того, сколько раз пользователь выругнулся. Каждый третий раз - мут"""
    user_id = ctx.author.id
    sql = f'SELECT counter FROM muted_users WHERE id = {user_id}'
    result = db.select_with_fetchone(sql)
    if not result:
        db.query(f'INSERT INTO muted_users(id, counter) VALUES ({user_id}, {0})')
        result = (0,)
    result = result[0] + 1
    db.query(f'UPDATE muted_users '
             f'SET counter = {result} '
             f'WHERE id = {user_id}')
    if result % 3 == 0:
        response = 'mute', result
    else:
        response = 'delete', result
    return response


async def remove_role(member, role_name):
    """Забирает роль"""
    role = discord.utils.get(member.guild.roles, name=role_name)
    await member.remove_roles(role)


async def give_role(member, role_name):
    """Выдает роль"""
    role = discord.utils.get(member.guild.roles, name=role_name)
    await member.add_roles(role)


async def play_city(ctx):
    """Играет с пользователем в города"""
    global named_cities, city_game, channel_game
    user_city = ctx.content.lower()
    if named_cities and (named_cities[-1][-1] != user_city[0] and
                         named_cities[-1][-1] in ('ъ', 'ы', 'ь', 'й') and named_cities[-1][-2] != user_city[0]):
        await ctx.channel.send(f'Игра окончена, вы начали не с той буквы. '
                               f'За время игры было названо {len(named_cities)} городов.')
        city_game = False
        named_cities = []
        channel_game = None
    elif user_city in named_cities:
        await ctx.channel.send(f'Игра окончена, такой город уже называли. '
                               f'За время игры было названо {len(named_cities)} городов.')
        city_game = False
        named_cities = []
        channel_game = None
    else:
        with open('data/cities.txt') as cities:
            cities_remake = []
            for city in cities:
                if city.strip():
                    cities_remake.append(city.strip().lower())
            cities = cities_remake.copy()
            if user_city not in cities:
                await ctx.channel.send(f'Игра окончена, нет такого города в России '
                                       f'За время игры было названо {len(named_cities)} городов.')
                city_game = False
                named_cities = []
                channel_game = None
            else:
                good_cities = []
                for city in cities:
                    if city[0].lower() == user_city[-1] or \
                            city[0].lower() == user_city[-2] and user_city[-1] in ('ы', 'ь', 'ъ', 'й'):
                        good_cities.append(city)
                try:
                    final_city = random.choice(good_cities)
                except ValueError:
                    await ctx.channel.send(f'Этого не может быть... У меня закончились города! Вы победили! '
                                           f'За время игры было названо {len(named_cities)} городов.')
                    city_game = False
                    named_cities = []
                    channel_game = None
                named_cities.append(user_city)
                named_cities.append(final_city)
                await ctx.channel.send(final_city.capitalize())


async def check_domains(link):
    """Проверяет правильно ли указана ссылка"""
    for x in domains:
        if link.startswith(x):
            return True
        return False


class MusicCommands(commands.Cog):
    def __init__(self, ds_bot):
        self.bot = ds_bot

    @commands.command(name='play')
    async def play(self, ctx, command=None):
        """Проигрывает музыку по ссылке"""
        global server, server_id, channel_name
        author = ctx.author
        if command is None:
            server = ctx.guild
            channel_name = author.voice.channel.name
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
            album, track = source[4], source[6]
            client.tracks([f'{track}:{album}'])[0].download('data/song.mp3', bitrate_in_kbps=128)
            voice.play(discord.FFmpegPCMAudio('data/song.mp3'))
        else:
            await ctx.channel.send('Неверный протокол')
            return

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Поставить музыку на паузу"""
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_playing():
            voice.pause()
        else:
            await ctx.channel.send('Музыка уже приостановлена')

    @commands.command(name='resume')
    async def resume(self, ctx):
        """Продолжить воспроизведение музыки"""
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_playing():
            await ctx.channel.send('Музыка уже воспроизводится')
        else:
            voice.resume()

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Прекратить воспроизведение музыки"""
        voice = discord.utils.get(bot.voice_clients, guild=server)
        await voice.stop()
        await ctx.channel.send('Воспроизведение прекращено')

    @commands.command(name='leave')
    async def leave(self, ctx):
        """Заставляет бота покинуть голосовой канал"""
        global server, channel_name
        voice = discord.utils.get(bot.voice_clients, guild=server)
        if voice.is_connected():
            await voice.disconnect()
        else:
            await ctx.channel.send('Бот не находится в голосовом канале')


class GameCommands(commands.Cog):
    def __init__(self, ds_bot):
        self.bot = ds_bot

    @commands.command(name='city')
    async def city(self, ctx):
        """Запускает игру Города"""
        global city_game, channel_game, named_cities
        channel_game = ctx.channel
        city_game = True
        named_cities = []
        await channel_game.send('Игра запущена!')

    @commands.command(name='give_admin')
    @commands.has_permissions(administrator=True)
    async def give_admin(self, ctx, count, member: discord.Member = None):
        """Выдает пользователю указанную сумму средств"""
        count = int(count)
        sql = f'SELECT money FROM users_money WHERE id = {member.id}'
        result = db.select_with_fetchone(sql)
        if not result:
            db.query(f'INSERT INTO users_money(id, money, time) VALUES ({member.id}, {count}, {"1"})')
        else:
            result = result[0]
            db.query(f'UPDATE users_money SET money = {result + count} WHERE id = {member.id}')
        await ctx.channel.send('Операция завершена')

    @commands.command(name='give_money')
    async def give_money(self, ctx, count, member: discord.Member = None):
        """Пользователь передает деньги другому человеку"""
        if not str(int(count)) == count or int(count) <= 0:
            await ctx.channel.send('Неверно указано число средств для передачи')
            return
        count = int(count)
        sql_author = f'SELECT money FROM users_money WHERE id = {ctx.author.id}'
        sql_member = f'SELECT money FROM users_money WHERE id = {member.id}'
        money_a = db.select_with_fetchone(sql_author)
        money_m = db.select_with_fetchone(sql_member)
        if not money_a:
            db.query(f'INSERT INTO users_money(id, money, time) VALUES ({ctx.author.id}, {0}, {"1"})')
            money_a = (0,)
        if not money_m:
            db.query(f'INSERT INTO users_money(id, money, time) VALUES ({member.id}, {0}, {"1"})')
            money_m = (0,)
        money_a, money_m = money_a[0], money_m[0]
        if money_a > count:
            db.query(f'UPDATE users_money SET money = {money_a - count} WHERE id = {ctx.author.id}')
            db.query(f'UPDATE users_money SET money = {money_m + count} WHERE id = {member.id}')
            await ctx.channel.send('Операция завершена')
        else:
            await ctx.channel.send('У вас нет таких денег!')

    @commands.command(name='show_money')
    async def show_money(self, ctx):
        """Показывает сколько денег у пользователя"""
        sql = f'SELECT money FROM users_money WHERE id = {ctx.author.id}'
        result = db.select_with_fetchone(sql)
        if not result:
            db.query(f'INSERT INTO users_money(id, money, time) VALUES ({ctx.author.id}, {0}, {"1"})')
            result = (0,)
        await ctx.channel.send(f'Ваш баланс: {result[0]}')

    @commands.command(name='daily')
    async def daily(self, ctx):
        """Выдает ежедневную награду"""
        sql = f'SELECT time, money FROM users_money WHERE id = {ctx.author.id}'
        result = db.select_with_fetchone(sql)
        if not result:
            db.query(f'INSERT INTO users_money(id, money, time) '
                     f'VALUES ({ctx.author.id}, {10}, datetime("now"))')
            await ctx.send('Операция завершена')
            return
        time_get, money = result
        if time_get == 1 or time_get == '1':
            db.query(f'UPDATE users_money SET money = {money + 10} WHERE id = {ctx.author.id}')
            db.query(f'UPDATE users_money SET time = datetime("now") WHERE id = {ctx.author.id}')
            await ctx.channel.send('Операция завершена')
        else:
            time_get = time_get.split()
            time_get = time_get[0].split('-') + time_get[1].split(':')
            time_get = [int(x) for x in time_get]
            time = dt.datetime(time_get[0], time_get[1], time_get[2],
                               time_get[3], time_get[4], time_get[5]) + dt.timedelta(hours=7)
            if time + dt.timedelta(hours=24) > dt.datetime.now():
                await ctx.send('Сутки еще не прошли!')
            else:
                db.query(f'UPDATE users_money SET money = {money + 10} WHERE id = {ctx.author.id}')
                db.query(f'UPDATE users_money SET time = datetime("now") WHERE id = {ctx.author.id}')
                await ctx.channel.send('Операция завершена')
            pass

    @commands.command(name='show_roles')
    async def show_roles(self, ctx):
        """Показывает какие роли доступны для покупки"""
        roles = []
        for key in roles_for_buying.keys():
            roles.append(f'{key}: {roles_for_buying[key]}')
        await ctx.send('\n'.join(roles))

    @commands.command(name='buy_role')
    async def buy_role(self, ctx, *role_name):
        """Купить роль"""
        role_name = ' '.join(role_name)
        sql = f'SELECT money FROM users_money WHERE id = {ctx.author.id}'
        result = db.select_with_fetchone(sql)
        if not result:
            db.query(f'INSERT INTO users_money(id, money, time) VALUES ({ctx.author.id}, {0}, {"1"})')
            result = (0,)
        result = result[0]
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send('Вы неверно указали роль для покупки')
        elif result < roles_for_buying[role_name]:
            await ctx.send('У вас недостаточно средств!')
        else:
            await give_role(ctx.author, role_name)
            db.query(f'UPDATE users_money '
                     f'SET money = {result - roles_for_buying[role_name]} WHERE id = {ctx.author.id}')
            await ctx.send('Роль куплена!')


class ChatCommands(commands.Cog):
    def __init__(self, ds_bot):
        self.bot = ds_bot

    @commands.command(name='elect')
    async def elect(self, ctx, *, command):
        """Позволяет создавать небольшие опросы"""
        params = command.split('/')
        if len(params) == 1:
            text = command
            color = int('ff0000', 16)
            title = ''
        elif len(params) == 2 or len(params) == 3:
            if len(params) == 3:
                title = params[2]
            else:
                title = ''
            text = params[0]
            if params[1] == '':
                color = int('ff0000', 16)
            else:
                color = params[1]
                try:
                    color = int(color, 16)
                except ValueError:
                    await ctx.channel.send(f'{ctx.author.mention}, неправильно указан цвет')
                    return
        else:
            await ctx.channel.send(f'{ctx.author.mention}, неправильно указаны параметры опроса')
            return
        await ctx.message.delete()

        msg = await ctx.channel.send(embed=discord.Embed(title=title, description=text, color=color))
        await msg.add_reaction('☑')
        await msg.add_reaction('❌')

    @commands.command(name='ava')
    async def avatar(self, ctx, *, member: discord.Member = None):
        """Выдает аватарку указанного пользователя"""
        user_url = member.avatar_url
        await ctx.send(user_url)

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Блокирует указанного участника на сервере"""
        await member.ban(reason=reason)
        await ctx.channel.purge(limit=1)
        await ctx.channel.send(f'Пользователь {member} был заблокирован. Причина: {reason}')
        admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
        await admin_channel.send(f'Пользователь {member} был заблокирован. Причина: {reason}')

    @commands.command(name='unban')
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, *member):
        """Разблокирует указанного участника на сервере"""
        banned_users = await ctx.guild.bans()
        member = ' '.join(member)
        member_name, member_discriminator = member.split("#")
        for person in banned_users:
            user = person.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.channel.purge(limit=1)
                admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
                await admin_channel.send(f'Пользователь {user.name} разблокирован')

    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        """Выдает мут указанному участнику на сервере"""
        await give_role(member, 'Muted')
        await ctx.channel.purge(limit=1)
        await ctx.channel.send(f'Пользователю {member.mention} был выдан мут. Причина: {reason}')
        admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
        await admin_channel.send(f'Пользователю {member.mention} был выдан мут. Причина: {reason}')

    @commands.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        """Снимает мут указанному участнику на сервере"""
        await remove_role(member, 'Muted')
        await ctx.channel.purge(limit=1)
        await ctx.channel.send(f'С пользователя {member.mention} был снят мут.')


@bot.event
async def on_message(ctx):
    """Первичная проверка сообщения"""
    if ctx.author == bot.user:
        return
    author = ctx.author
    with open('data/ban_words.txt', encoding='utf8') as bw:
        for word in bw:
            word = word.strip()
            if word in ctx.content.lower():
                response = await check_count(ctx)
                msg, counter = response
                if msg == 'delete':
                    await ctx.delete()
                    await ctx.channel.send(f'{author.mention}, не используйте запрещенные слова!')
                else:
                    await give_role(author, 'Muted')
                    await ctx.channel.purge(limit=1)
                    await ctx.channel.send(f'Пользователю {author.mention} был выдан мут из-за использования '
                                           f'запрещенных слов!')
                admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
                embed = discord.Embed(title="Матершина!",
                                      description=f"{ctx.author.name} только что сказал ||{word}||",
                                      color=discord.Color.blurple())
                await admin_channel.send(embed=embed)
    if city_game and ctx.channel == channel_game:
        await play_city(ctx)
    await bot.process_commands(ctx)


@bot.event
async def on_member_join(member):
    """Здоровается с пользователем в соответствующем канале"""
    ava_url = member.avatar_url
    response = requests.get(ava_url).content
    user_invite = 'data/user_invite.jpg'
    with open(user_invite, 'wb') as file:
        file.write(response)
    image_user = Image.open(user_invite)
    image_user = image_user.convert('RGB')
    image_user.save(user_invite)
    image_user_small = image_user.resize((150, 150))
    image_user_small.save('data/small_user.jpg')
    invite_image = Image.open('data/invite.jpg')
    pixels_invite = invite_image.load()
    pixels_user = image_user_small.load()
    x, y = invite_image.size
    for i in range(x):
        for j in range(y):
            if 229 < i < 380 and 84 < j < 235:
                r, g, b = pixels_user[i - 230, j - 85]
                pixels_invite[i, j] = r, g, b
    invite_image.save('data/final_user_invite.jpg')
    with open('data/final_user_invite.jpg', 'rb') as file:
        picture = discord.File(file)
        channel = discord.utils.get(member.guild.text_channels, name='приветствие')
        await channel.send(f'Поприветствуйте {member.mention}!')
        msg = await channel.send(file=picture)
        await msg.add_reaction('👍')


@bot.event
async def on_raw_reaction_add(payload):
    """Добавляет пользователю роль при нажатии на соответствующую реакцию"""
    reaction = payload.emoji.name
    user = payload.member
    channel = bot.get_channel(970705900740423701)
    if channel.id != payload.channel_id:
        return
    try:
        await give_role(user, reactions[reaction])
    except KeyError:
        return


bot.add_cog(ChatCommands(bot))
bot.add_cog(GameCommands(bot))
bot.add_cog(MusicCommands(bot))
TOKEN = "OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.Cts8ZF82r0uFA8kQCBpD-lIUY5o"
bot.run(TOKEN)
