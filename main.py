import discord
from discord.ext import commands
import logging
from database import DataBase

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


async def give_role(ctx, role_name):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    await discord.Member.add_roles(ctx.author, role)


async def mute(ctx):
    await ctx.channel.purge(limit=1)
    await give_role(ctx, 'Muted')


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
                    await mute(ctx)
                    await ctx.channel.send(f'Пользователю {author.mention} был выдан мут из-за использования '
                                           f'запрещенных слов!')
    await bot.process_commands(ctx)

bot.add_cog(ChatCommands(bot))
TOKEN = "OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.uhwFKqUvMunyou7w8jYKo2lkrdg"
bot.run(TOKEN)
# OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.uhwFKqUvMunyou7w8jYKo2lkrdg
