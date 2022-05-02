import discord
from discord.ext import commands
import logging
from database import DataBase
from PIL import Image
import requests

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

db = DataBase('discord_bot.db')
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)


async def check_count(ctx):
    global db
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
    role = discord.utils.get(member.guild.roles, name=role_name)
    await member.remove_roles(role)


async def give_role(member, role_name):
    role = discord.utils.get(member.guild.roles, name=role_name)
    await member.add_roles(role)


class ChatCommands(commands.Cog):
    def __init__(self, ds_bot):
        self.bot = ds_bot

    @commands.command(name='srv')
    async def srv(self, ctx, *, command):
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
        user_url = member.avatar_url
        await ctx.send(user_url)

    @commands.command(name='ban')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.channel.purge(limit=1)
        await ctx.channel.send(f'Пользователь {member} был заблокирован. Причина: {reason}')
        admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
        await admin_channel.send(f'Пользователь {member} был заблокирован. Причина: {reason}')

    @commands.command(name='unban')
    @commands.has_permissions(administrator=True)
    async def unban(self, ctx, *member):
        banned_users = await ctx.guild.bans()
        member = ' '.join(member)
        member_name, member_discriminator = member.split("#")
        for person in banned_users:
            user = person.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unban(user)
                await ctx.channel.purge(limit=1)
                admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
                await admin_channel.send(f'Пользователь {user.mention} разблокирован')

    @commands.command(name='mute')
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        await give_role(member, 'Muted')
        await ctx.channel.purge(limit=1)
        await ctx.channel.send(f'Пользователю {member.mention} был выдан мут. Причина: {reason}')
        admin_channel = discord.utils.get(ctx.guild.text_channels, name='admin')
        await admin_channel.send(f'Пользователю {member.mention} был выдан мут. Причина: {reason}')

    @commands.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, member: discord.Member):
        await remove_role(member, 'Muted')
        await ctx.channel.purge(limit=1)
        await ctx.channel.send(f'С пользователя {member.mention} был снят мут.')


@bot.event
async def on_message(ctx):
    if ctx.author == bot.user:
        return
    author = ctx.author
    with open('ban_words.txt', encoding='utf8') as bw:
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
                embed = discord.Embed(title="Profanity Alert!",
                                      description=f"{ctx.author.name} just said ||{word}||",
                                      color=discord.Color.blurple())
                await admin_channel.send(embed=embed)
    await bot.process_commands(ctx)


@bot.event
async def on_member_join(member):
    server = member.guild
    ava_url = member.avatar_url
    response = requests.get(ava_url).content
    user_invite = 'user_invite.jpg'
    with open(user_invite, 'wb') as file:
        file.write(response)
    image_user = Image.open(user_invite)
    image_user = image_user.convert('RGB')
    image_user.save(user_invite)
    image_user_small = image_user.resize((150, 150))
    image_user_small.save('small_user.jpg')
    invite_image = Image.open('invite.jpg')
    pixels_invite = invite_image.load()
    pixels_user = image_user_small.load()
    x, y = invite_image.size
    for i in range(x):
        for j in range(y):
            if 229 < i < 380 and 84 < j < 235:
                r, g, b = pixels_user[i - 230, j - 85]
                pixels_invite[i, j] = r, g, b
    invite_image.save('final_user_invite.jpg')
    with open('final_user_invite.jpg', 'rb') as file:
        picture = discord.File(file)
        channel = discord.utils.get(server.text_channels, name='приветствие')
        await channel.send(f'По приветствуйте {member.mention}!')
        await channel.send(file=picture)


bot.add_cog(ChatCommands(bot))
TOKEN = "OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.u3fJ3Jp7YiWIEW44ACZYsFrRwvk"
bot.run(TOKEN)
