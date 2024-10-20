from discord.ext import commands


class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = ""
        self.text_channel_list = []
        self.set_message()

    def set_message(self):
        self.help_message = f"""
```apache
General commands:
{self.bot.command_prefix}add (paste TM message) - sends limit orders to MT4
{self.bot.command_prefix}delete (paste order in '{self.bot.command_prefix}viewpendingorders' format)
{self.bot.command_prefix}viewpendingorders - displays all active orders
{self.bot.command_prefix}lotsize (number) - sets lot size (autolot must be off)
{self.bot.command_prefix}prefix (prefix) - changes prefix
{self.bot.command_prefix}deleteall - deletes all pending orders

Change default settings:
{self.bot.command_prefix}setting autospread (on/off) - toggles Auto-calculate spread. Default: off
{self.bot.command_prefix}setting autolot (on/off) - toggles Auto-calculate lot size. Default: off
{self.bot.command_prefix}setting risk (whole number. e.g. "10" or "5") Default: 10
{self.bot.command_prefix}setting defaultlotsize - sets default lot size for when MetaTrader starts up, Default: 0.01
```
"""

    @commands.Cog.listener()
    async def on_ready(self):
        print('Logged in as ' + self.bot.user.name)

    @commands.command(name="help", help="Displays all  available commands")
    async def help(self, ctx):
        await ctx.send(self.help_message)

    @commands.command(name="prefix", help="Change bot prefix")
    async def prefix(self, ctx, *args):
        self.bot.command_prefix = " ".join(args)
        self.set_message()
        await ctx.send(f"prefix set to **'{self.bot.command_prefix}'**")
