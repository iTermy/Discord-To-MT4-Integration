from discord.ext import commands
from helper_functions import parse_complex_string, replace_file_content
import re


MT4_connection_file = 'connection.txt'


class trading_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add')
    async def test_input(self, ctx, *, msg: str):
        print("\nLimits added: \n" + parse_complex_string(msg))
        try:
            replace_file_content(MT4_connection_file, parse_complex_string(msg))
            await ctx.send("Limits added: \n" + parse_complex_string(msg))
            await ctx.send("\n\n Check your broker to verify. If it doesn't work, check your message for any typos.")

        except Exception as e:
            await ctx.send("Something went wrong. Please try again")

    @commands.command(name='lotsize')
    async def set_lot_size(self, ctx, lot_size: str):
        # Check if the input matches the required format
        if not re.match(r'^\d\.\d{2}$', lot_size):
            await ctx.send("Invalid format. Please use '#.##' format (e.g., 0.23).")
            return

        try:
            replace_file_content("lot_size.txt", lot_size)
            await ctx.send(f"Lot size changed to {lot_size}.")
        except Exception as e:
            await ctx.send("Invalid input. Please provide a valid number.")
