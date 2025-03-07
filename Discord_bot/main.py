import discord
from discord.ext import commands, tasks
import asyncio
import re
import json
import sys
from collections import defaultdict

# Load credentials
try:
    with open('config.json', 'r') as f:
        config = json.load(f)

    DISCORD_TOKEN = str(config.get('discord_token', ''))
    CHANNEL_ID = str(config.get('channel_id', ''))
    MT4_connection_file = str(config.get('MT4_connection_file', ''))
    embed_url = str(config.get('embed_url', ''))

    if not all([DISCORD_TOKEN, CHANNEL_ID, MT4_connection_file, embed_url]):
        print("ERROR: One or more required configuration values are empty in config.json")

except FileNotFoundError:
    print("Error: config.json not found. Please create a config.json file with required credentials.")
    sys.exit(1)
except json.JSONDecodeError:
    print("Error: config.json is not valid JSON. Please check the format.")
    sys.exit(1)
except Exception as e:
    print(f"Error loading config.json: {str(e)}")
    sys.exit(1)


# Main function for parsing limits
def parse_complex_string(input_string):
    # Define patterns
    price_pattern = r'(\d+\.?\d*)'
    symbol_pattern = (
        r'\b(audusd|eurusd|gbpusd|usdcad|usdchf|usdjpy|audcad|audchf|audjpy|audnzd|eth|ethusd|'
        r'cadchf|cadjpy|chfjpy|euraud|eurcad|eurchf|eurgbp|eurjpy|eurnzd|gbpaud|gbpcad|'
        r'gbpchf|gbpjpy|gbpnzd|nzdcad|nzdchf|nzdjpy|nzdusd|gu|gold|oil|silver|nas|nasdaq|'
        r'dxy|spx|dax|dow|bitcoin|btc|eg|uchf|gj|ucad|au|xauusd|usdmxn)\b')
    symbols_that_use_dollars = ['XAUUSD', 'WTI', 'XAGUSG', 'US100', 'USDIDX', 'US500', 'GER30', 'US30', 'BTCUSD']
    position_pattern = r'\b(short|long)\b'

    # Find components in string
    all_numbers = re.findall(price_pattern, input_string)
    symbol_match = re.search(symbol_pattern, input_string.lower())
    position_match = re.search(position_pattern, input_string.lower())

    # Error handling
    if len(all_numbers) < 2:
        print(all_numbers)
        raise ValueError("Not enough numbers found in the input string.")
    if not symbol_match:
        raise ValueError("No valid symbol found in the input string.")
    if not position_match:
        raise ValueError("No position (short/long) found in the input string.")

    # Process symbol
    symbol = symbol_match.group(1).upper()
    symbol_mapping = {
        "GOLD": "XAUUSD", "OIL": "WTI", "SILVER": "XAGUSD",
        "NAS": "US100", "NASDAQ": "US100", "DXY": "USDIDX",
        "SPX": "US500", "DAX": "GER30", "DOW": "US30",
        "BITCOIN": "BTCUSD", "BTC": "BTCUSD", "GU": "GBPUSD",
        "UCAD": "USDCAD", "UCHF": "USDCHF", "AU": "AUDUSD",
        "GJ": "GBPJPY", "EG": "EURGBP", "ETH": "ETHUSD"}
    if symbol in symbol_mapping:
        symbol = symbol_mapping.get(symbol, symbol)

    # Process prices
    prices = all_numbers[:-1]
    processed_prices = []
    for price in prices:
        price_float = float(price)
        # Handles implied 0.xxxxx prices (Ex. AUDUSD 63000 = 0.63000)
        if price_float > 10000 and symbol not in symbols_that_use_dollars:
            price_float /= 100000
            processed_prices.append(f"{price_float:.5f}")
        else:
            processed_prices.append(f"{price_float}")

    # Process position and stop loss
    position = position_match.group(1).upper()
    sl = all_numbers[-1]
    sl_float = float(sl)
    if sl_float > 10000 and symbol not in symbols_that_use_dollars:
        sl_float /= 100000
    sl = sl_float

    # Process expiry (Default to week if not major pair or vth (valid till hit))
    expiry = "WEEK"
    major_forex_pairs = ['EURUSD', 'USDJPY', 'GBPUSD', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD']
    if symbol in major_forex_pairs:
        expiry = "DAY"
    if re.search("vth", input_string.lower()):
        expiry = "WEEK"

    # Generate output
    output = []
    for price in processed_prices:
        output.append(f"{price} {symbol} {position} {sl} {expiry}")

    return "\n".join(output)


# Function used to send information to MT4 via connection_files/connection.txt
def replace_file_content(file_path, command, input_string):
    try:
        with open(file_path, 'w') as file:
            file.write(command + '\n')
            file.write(input_string)
        print(f'Successfully replaced content in {file_path}')
    except Exception as e:
        print(f'Error: {e}')


class MQL4Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='.', intents=discord.Intents.all())
        self.remove_command('help')
        self.channel_id = CHANNEL_ID
        self.channel = None
        self.block_alerts = False
        self.curr_msg = None

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        self.channel = self.get_channel(int(CHANNEL_ID))
        if not self.channel:
            print(f"Couldn't find channel with ID {CHANNEL_ID}")
            sys.exit(1)

    async def setup_hook(self):
        self.check_message.start()
        await self.add_cog(MQL4Commands(self))

    def cog_unload(self):
        self.check_message.cancel()

    # Handles instructions sent from MT4. Checks message.txt every second
    @tasks.loop(seconds=1)
    async def check_message(self):
        try:
            with open("connection_files/message.txt", "r") as file:
                content = file.read().strip()
                with open("connection_files/message.txt", "w") as file_write:
                    file_write.truncate(0)

            if content:
                print("Content found in message.txt:\n", content)
                if self.channel:
                    lines = content.split("\n")

                    # First line of files dictates what kind of message it is
                    if lines[0] == "Error":
                        embed = discord.Embed(title=lines[0], description=lines[1],
                                              color=0xff0000)
                        embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
                        await self.curr_msg.edit(embed=embed)

                    if lines[0] == "addLimits" and self.block_alerts is False:
                        _, symbol, position, sl, expiry = lines[1].split(" ")
                        embed = discord.Embed(title="Limit Added", color=0x00ff6e)
                        embed.set_thumbnail(url=embed_url)
                        embed.add_field(name="Symbol", value=symbol, inline=True)
                        embed.add_field(name="Position", value=position, inline=True)
                        embed.add_field(name="Expiry", value=(expiry.lower()).capitalize(), inline=False)
                        limits = [line.split(" ")[0] for line in lines[1:]]
                        for count, limit in enumerate(limits, start=1):
                            embed.add_field(name=f"Limit {count}", value=limit, inline=True)
                        embed.add_field(name="Stop Loss", value=sl, inline=False)
                        await self.curr_msg.edit(embed=embed)

                    if lines[0] == "delOrder":
                        parts = lines[1].split()
                        symbol = parts[0]
                        position = parts[1].upper()
                        stops_index = parts.index("stops")
                        limits = list(map(float, parts[2:stops_index]))
                        stop_loss_str = parts[stops_index + 1]
                        stop_loss_clean = ''.join(c for c in stop_loss_str if c.isdigit() or c == '.')
                        if stop_loss_clean.endswith('.'):
                            stop_loss_clean = stop_loss_clean[:-1]
                        stop_loss = float(stop_loss_clean)
                        embed = discord.Embed(title="Limit Deleted", color=0x00ff6e)
                        embed.set_thumbnail(url=embed_url)
                        embed.add_field(name="Symbol", value=symbol, inline=False)
                        embed.add_field(name="Position", value=position, inline=False)
                        count = 1
                        for limit in limits:
                            embed.add_field(name="Limit " + str(count), value=limit, inline=True)
                            count += 1
                        embed.add_field(name="Stop Loss", value=stop_loss, inline=False)
                        await self.curr_msg.edit(embed=embed)

                    if lines[0] == "delAllOrders":
                        embed = discord.Embed(title="All orders successfully deleted", color=0x03d100)
                        embed.set_thumbnail(url=embed_url)
                        await self.curr_msg.edit(embed=embed)

        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await self.channel.send(embed=embed)


class MQL4Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add')
    async def add_limits(self, ctx, *, msg: str):
        try:
            print("\nAdding limits: \n" + parse_complex_string(msg))
            embed = discord.Embed(title="Adding Limit . . .", description="Please wait . . .", color=0xdadc50)
            self.bot.curr_msg = await ctx.send(embed=embed)
            replace_file_content(MT4_connection_file, 'addLimits', parse_complex_string(msg))

        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await self.bot.curr_msg.edit(embed=embed)

    @commands.command(name='lotsize')
    async def set_lot_size(self, ctx, lot_size: str):
        try:
            lot_size_float = float(lot_size)
            formatted_lot_size = f"{lot_size_float:.2f}"
            replace_file_content(MT4_connection_file, 'changeLot', formatted_lot_size)
            embed = discord.Embed(title="Lotsize changed", description="Lot size: " + formatted_lot_size,
                                  color=0x03d100)
            embed.set_thumbnail(url=embed_url)
            self.bot.curr_msg = await ctx.send(embed=embed)

        except ValueError:
            embed = discord.Embed(title="Error", description="Invalid input. Please provide a number.",
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error", description=str(e), color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)

    @commands.command(name='setting', aliases=['s'])
    async def change_setting(self, ctx, setting: str, state: str):
        # Ensure the setting provided is valid
        setting = setting.lower()
        valid_settings = ['autospread', 'autolot', 'defaultlotsize', 'risk']
        if setting not in valid_settings:
            embed = discord.Embed(title="Error",
                                  description="Invalid setting. Use 'autospread', 'autolot', 'defaultlotsize', "
                                              "or 'risk'.",
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)
            return

        # Validate state for autoCalcSpread and autoCalcLot (should be 'on' or 'off')
        if setting in ['autospread', 'autolot']:
            if state not in ['on', 'off']:
                embed = discord.Embed(title="Error",
                                      description="Invalid state. Use 'on' or 'off' for this setting.",
                                      color=0xff0000)
                embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
                await ctx.send(embed=embed)
                return

        # Validate that defaultLotSize is a valid number if it's being updated
        if setting == 'defaultlotsize':
            try:
                lot_size_float = float(state)
                formatted_lot_size = f"{lot_size_float:.2f}"
                state = formatted_lot_size
            except ValueError:
                embed = discord.Embed(title="Error",
                                      description="Invalid value for defaultLotSize. "
                                                  "Please provide a valid positive number (e.g., 0.23).",
                                      color=0xff0000)
                embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
                await ctx.send(embed=embed)
                return

        if setting == 'risk':
            try:
                state = int(state)
            except ValueError:
                embed = discord.Embed(title="Error", description="Invalid number. Try again.", color=0xff0000)
                embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
                await ctx.send(embed=embed)
                return

        try:
            # Read the current content of the file
            with open('connection_files/default_settings.txt', 'r') as file:
                lines = file.readlines()

            # Write the updated content back to the file
            with open('connection_files/default_settings.txt', 'w') as file:
                setting_found = False
                for line in lines:
                    # Find the line corresponding to the setting and update its value
                    if line.startswith(setting):
                        file.write(f"{setting} {state}\n")
                        setting_found = True
                    else:
                        file.write(line)

            if setting_found:
                if isinstance(state, str):
                    state = state.capitalize()
                embed = discord.Embed(title="Setting changed",
                                      description=f"{setting.capitalize()}: {state}", color=0x03d100)
                embed.set_thumbnail(url=embed_url)
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(title="Error",
                                      description=setting + " not found in the settings file.",
                                      color=0xff0000)
                embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
                await ctx.send(embed=embed)

        except Exception as e:
            embed = discord.Embed(title="Error",
                                  description=str(e),
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)

    @commands.command(name='viewpendingorders', aliases=['vpo'])
    async def view_pending_orders_closest(self, ctx):
        orders = {}
        try:
            with open('connection_files/active_orders.txt', 'r') as file:
                for line in file:
                    symbol, direction, limit, stop_loss, distance, expiry = line.strip().split()
                    match = re.match(r"(\d+\.\d+|\d+)([a-zA-Z$]+)", distance)
                    if match:
                        distance = float(match.group(1))  # Convert the number to float
                        unit = match.group(2)  # The second group is the rest (e.g., $, pips)
                    key = (symbol, direction, stop_loss, unit)
                    if key in orders:
                        orders[key]['limits'].append(float(limit))
                        orders[key]['distance'] = min(orders[key]['distance'], float(distance))
                    else:
                        orders[key] = {'limits': [float(limit)], 'distance': float(distance)}

            # Sort orders by distance
            sorted_orders = sorted(orders.items(), key=lambda x: x[1]['distance'])

            embed = discord.Embed(title="Current Orders:", color=0x03d100)
            embed.set_thumbnail(url=embed_url)
            count = 1
            for (symbol, direction, stop_loss, unit), order_data in sorted_orders:
                limits_str = " ".join(map(str, sorted(order_data['limits'])))
                embed.add_field(
                    name=f"{count}. {order_data['distance']} {unit} away - {symbol} "
                         f"{direction.lower()} {limits_str} stops {stop_loss}",
                    value="",
                    inline=False)
                count += 1
            self.bot.curr_msg = await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error",
                                  description=str(e),
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)

    @commands.command(name="delete", aliases=["del"])
    async def delete_order(self, ctx, *, order: str):
        try:
            cleaned_string = re.sub(r'\sdistance\s\d+(\.\d+)?\s\S+$', '', order)
            pattern = r'^(\S+)\s+(long|short)\s+([\d\.\s]+)\s*stops\s+([\d\.]+)$'
            match = re.match(pattern, cleaned_string)
            if not match:
                raise ValueError
            symbol, direction, limits, stop_loss = match.groups()
            output = f"{symbol} {direction} {limits.strip()} stops {stop_loss}"
            replace_file_content(MT4_connection_file, 'deleteOrder', output)
            embed = discord.Embed(title="Deleting Limit . . .", description="Please wait . . .", color=0xdadc50)
            self.bot.curr_msg = await ctx.send(embed=embed)
        except ValueError:
            embed = discord.Embed(title="Error",
                                  description="Input string is not in the correct format",
                                  color=0xff0000)
            embed.add_field(name="Example format:", value="^del EURUSD short 1.0544 1.05535 1.05799 stops 1.05921",
                            inline=False)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error",
                                  description=f"Something went wrong with deleting order. "
                                              f"Check discord logs. Error: {e}",
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)

    @commands.command(name="saveandcloseallorders", aliases=["scao"])
    async def save_and_close_all_orders(self, ctx):
        try:
            with open('connection_files/active_orders.txt', 'r') as file:
                lines = file.readlines()
            processed_lines = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    symbol, direction, limit_price, stop_loss, distance, expiry = parts[:6]
                    processed_line = f"{limit_price} {symbol} {direction} {stop_loss} {expiry}"
                    processed_lines.append(processed_line)
            # Write to the output file
            with open('connection_files/saved_orders.txt', 'w') as file:
                file.write('\n'.join(processed_lines))
            replace_file_content("connection_files/connection.txt", "deleteAll", "delete all orders")
            embed = discord.Embed(title="Orders successfully saved!", description="Now deleting orders...",
                                  color=0x03d100)
            embed.set_thumbnail(url=embed_url)
            self.bot.curr_msg = await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(title="Error",
                                  description="Something went wrong with deleting order. Check discord logs."
                                              "Error: " + str(e),
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)

    @commands.command(name="loadallsavedorders", aliases=["laso"])
    async def load_all_saved_orders(self, ctx):
        embed = discord.Embed(title="Loading saved orders . . .", description="Please wait . . .", color=0xdadc50)
        self.bot.curr_msg = await ctx.send(embed=embed)
        config = {}
        self.bot.block_alerts = True

        # Read the file and parse its contents
        with open('connection_files/default_settings.txt', 'r') as file:
            for line in file:
                # Remove whitespace and split into key-value pairs
                parts = line.strip().split()
                if len(parts) == 2:
                    config[parts[0]] = parts[1]

        # Check if autospread is on
        if config.get('autospread') == 'on':
            embed = discord.Embed(title="Error",
                                  description="Please turn autospread off before using! '^setting autospread off'",
                                  color=0xff0000)
            await self.bot.curr_msg.edit(embed=embed)
            return

        try:
            # Read the contents of saved_orders.txt
            with open('connection_files/saved_orders.txt', 'r') as file:
                saved_orders = file.read().strip().split('\n')

            # Group orders by stop loss
            orders_by_stop_loss = defaultdict(list)
            for order in saved_orders:
                parts = order.split()
                if len(parts) >= 4:
                    stop_loss = parts[3]
                    orders_by_stop_loss[stop_loss].append(order)

            # Process each group of orders
            for stop_loss, orders in orders_by_stop_loss.items():
                # Prepare the content for connection.txt
                connection_content = "addLimits\n" + "\n".join(orders)

                # Write the content to connection.txt
                with open('connection_files/connection.txt', 'w') as file:
                    file.write(connection_content)

                # Wait for connection.txt to be empty
                while True:
                    await asyncio.sleep(1)  # Wait for 1 second
                    with open('connection_files/connection.txt', 'r') as file:
                        if not file.read().strip():
                            break

            # Clear the contents of saved_orders.txt
            with open('connection_files/saved_orders.txt', 'w') as file:
                file.write('')

            await asyncio.sleep(3)
            self.bot.block_alerts = False
            embed = discord.Embed(title="All orders have been processed.", color=0x03d100)
            embed.set_thumbnail(url=embed_url)
            await self.bot.curr_msg.edit(embed=embed)

        except Exception as e:
            embed = discord.Embed(title="Error",
                                  description=f"Something went wrong with discord: {e}",
                                  color=0xff0000)
            embed.set_footer(text="If unable to resolve issue, dm @itermy on discord for help.")
            await ctx.send(embed=embed)

    @commands.command(name="deleteall", aliases=["delall"])
    async def delete_all_orders(self, ctx):
        embed = discord.Embed(title="Deleting all limits . . .", description="Please wait . . .", color=0xdadc50)
        self.bot.curr_msg = await ctx.send(embed=embed)
        replace_file_content("connection_files/connection.txt", "deleteAll", "delete all orders")

    @commands.command(name='prefix')
    async def change_prefix(self, ctx, new_prefix: str):
        """Change bot prefix"""
        self.bot.command_prefix = new_prefix
        await ctx.send(f"Command prefix changed to: {new_prefix}")

    @commands.command(name='help')
    async def help_command(self, ctx):
        help_text = f"""
```apache
General commands:
{self.bot.command_prefix}add (paste TM message) - sends limit orders to MT4
{self.bot.command_prefix}delete (paste order in '{self.bot.command_prefix}viewpendingorders' format)
{self.bot.command_prefix}viewpendingorders - displays all active orders
{self.bot.command_prefix}lotsize (number) - sets lot size (autolot must be off)
{self.bot.command_prefix}saveandcloseallorders - saves all current limit orders to saved_orders.txt
{self.bot.command_prefix}loadallsavedorders - loads back all orders from saved_orders.txt
{self.bot.command_prefix}deleteall - deletes all pending orders
{self.bot.command_prefix}prefix (prefix) - changes prefix

Change default settings:
{self.bot.command_prefix}setting autospread (on/off) - toggles Auto-calculate spread. Default: off
{self.bot.command_prefix}setting autolot (on/off) - toggles Auto-calculate lot size. Default: off
{self.bot.command_prefix}setting risk (whole number. e.g. "10" or "5") Default: 10
{self.bot.command_prefix}setting defaultlotsize - sets default lot size for when MetaTrader starts up, Default: 0.01
```
"""
        await ctx.send(help_text)


def main():
    bot = MQL4Bot()
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
