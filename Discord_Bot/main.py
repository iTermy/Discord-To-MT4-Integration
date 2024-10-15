import discord
from discord.ext import commands
import os, asyncio
from trading_cog import trading_cog
from help_cog import help_cog

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='^', intents=intents)
bot.remove_command('help')

async def main():
    async with bot:
        await bot.add_cog(trading_cog(bot))
        await bot.add_cog(help_cog(bot))
        await bot.start(os.getenv('TOKEN'))

asyncio.run(main())