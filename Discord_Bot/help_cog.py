from discord.ext import commands


class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = ""
        self.text_channel_list = []
        self.set_message()

    def set_message(self):
        self.help_message = f""""
```
General commands:
{self.bot.command_prefix}add (paste TM message) - sends limit orders to MT4
{self.bot.command_prefix}prefix (prefix) - changes prefix
{self.bot.command_prefix}lotsize X.XX - sets lot size
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


