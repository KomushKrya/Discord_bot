import discord
import logging
import requests


logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

TOKEN = "OTYxMjIwMjk4ODUyNjg3OTIy.Yk10KQ.kB4KlfbG86T2sYMqV6t2meeWRd8"


class YLBotClient(discord.Client):
    async def on_ready(self):
        logger.info(f'{self.user} has connected to Discord!')
        for guild in self.guilds:
            logger.info(
                f'{self.user} подключились к чату:\n'
                f'{guild.name}(id: {guild.id})')

    async def on_message(self, message):
        if message.author == self.user:
            return
        if "кот" in message.content.lower() or 'кош' in message.content.lower():
            response = requests.get("https://api.thecatapi.com/v1/images/search").json()
            cat = response[0]['url']
            await message.channel.send(cat)
        elif "пёс" in message.content.lower() or 'соба' in message.content.lower():
            response = requests.get("https://dog.ceo/api/breeds/image/random").json()
            dog = response['message']
            await message.channel.send(dog)


intents = discord.Intents.default()
intents.members = True
client = YLBotClient(intents=intents)
client.run(TOKEN)