from discord.ext import commands
from helper_functions import parse_complex_string, replace_file_content
import re


MT4_connection_file = 'connection.txt'


class trading_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add')
    async def add_limits(self, ctx, *, msg: str):
        print("\nLimits added: \n" + parse_complex_string(msg))
        try:
            replace_file_content(MT4_connection_file, 'addLimits', parse_complex_string(msg))
            await ctx.send("Limits Added: \n" + parse_complex_string(msg) +
                           "\nCheck your broker to verify. If it doesn't work, check your message for any typos.")

        except Exception as e:
            await ctx.send("Something went wrong. Please try again")

    @commands.command(name='lotsize')
    async def set_lot_size(self, ctx, lot_size: str):
        try:
            lot_size_float = float(lot_size)
            formatted_lot_size = f"{lot_size_float:.2f}"
            replace_file_content(MT4_connection_file, 'changeLot', formatted_lot_size)
            await ctx.send(f"Lot size changed to {lot_size}.")
        except ValueError:
            await ctx.send("Invalid input. Please provide a number.")
        except Exception as e:
            await ctx.send("Something went wrong with replace_file_content().")

    @commands.command(name='setting', aliases=['s'])
    async def change_setting(self, ctx, setting: str, state: str):
        # Ensure the setting provided is valid
        setting = setting.lower()
        valid_settings = ['autospread', 'autolot', 'defaultlotsize', 'risk']
        if setting not in valid_settings:
            await ctx.send("Invalid setting. Use 'autospread', 'autolot', 'defaultlotsize', or 'risk'.")
            return

        # Validate state for autoCalcSpread and autoCalcLot (should be 'on' or 'off')
        if setting in ['autospread', 'autolot']:
            if state not in ['on', 'off']:
                await ctx.send("Invalid state. Use 'on' or 'off' for this setting.")
                return

        # Validate that defaultLotSize is a valid number if it's being updated
        if setting == 'defaultlotsize':
            try:
                lot_size_float = float(state)
                formatted_lot_size = f"{lot_size_float:.2f}"
                state = formatted_lot_size
            except ValueError:
                await ctx.send("Invalid value for defaultLotSize. Please provide a valid positive number (e.g., 0.23).")
                return

        if setting == 'risk':
            try:
                state = int(state)
            except ValueError:
                await ctx.send("Invalid number. Try again")
                return

        try:
            # Read the current content of the file
            with open('default_settings.txt', 'r') as file:
                lines = file.readlines()

            # Write the updated content back to the file
            with open('default_settings.txt', 'w') as file:
                setting_found = False
                for line in lines:
                    # Find the line corresponding to the setting and update its value
                    if line.startswith(setting):
                        file.write(f"{setting} {state}\n")
                        setting_found = True
                    else:
                        file.write(line)

            if setting_found:
                await ctx.send(f"Successfully updated {setting} to {state}. It may take 10 seconds to update in MT4")
            else:
                await ctx.send(f"{setting} not found in the settings file.")

        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name='viewpendingorders', aliases=['vpo'])
    async def view_pending_orders_closest(self, ctx):
        orders = {}

        with open('active_orders.txt', 'r') as file:
            for line in file:
                symbol, direction, limit, stop_loss, distance = line.strip().split()
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

        try:
            await ctx.send("Pending orders: ")
            for (symbol, direction, stop_loss, unit), order_data in sorted_orders:
                limits_str = " ".join(map(str, sorted(order_data['limits'])))
                await ctx.send(f"{symbol} {direction.lower()} {limits_str} stops {stop_loss} distance {order_data['distance']} {unit}")
        except Exception as e:
            await ctx.send(f"Error while processing file. Check 'active_orders.txt'. Error code: {e}")


    @commands.command(name="delete", aliases=["del"])
    async def delete_order(self, ctx, *, order: str):
        try:
            print(order)
            cleaned_string = re.sub(r'\sdistance\s\d+(\.\d+)?\s\S+$', '', order)
            print(cleaned_string)
            pattern = r'^(\S+)\s+(long|short)\s+([\d\.\s]+)\s*stops\s+([\d\.]+)$'
            match = re.match(pattern, cleaned_string)
            if not match:
                raise ValueError
            symbol, direction, limits, stop_loss = match.groups()
            output = f"{symbol} {direction} {limits.strip()} stops {stop_loss}"
            replace_file_content(MT4_connection_file, 'deleteOrder', output)
            await ctx.send(f"Deleted order {output}. Please check your broker.")
        except ValueError:
            await ctx.send("Input string is not in the correct format")
        except Exception as e:
            await ctx.send("Something went wrong with deleting order.")

    @commands.command(name="saveandcloseallorders", aliases=["scao"])
    async def save_and_close_all_orders(self, ctx):
        with open('active_orders.txt', 'r') as file:
            lines = file.readlines()

        # Process and rearrange the lines
        processed_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                symbol, direction, limit_price, stop_loss, _ = parts[:5]
                processed_line = f"{limit_price} {symbol} {direction} {stop_loss}"
                processed_lines.append(processed_line)

        # Write to the output file
        with open('saved_orders.txt', 'w') as file:
            file.write('\n'.join(processed_lines))
        replace_file_content("connection.txt", "deleteAll", "delete all orders")
        await ctx.send("Orders closed and saved to 'saved_orders.txt'")

    @commands.command(name="loadallsavedorders", aliases=["laso"])
    async def load_all_saved_orders(self, ctx):
        try:
            # Read the contents of saved_orders.txt
            with open('saved_orders.txt', 'r') as file:
                saved_orders = file.read().strip()

            # Prepare the content for connection.txt
            connection_content = "addLimits\n" + saved_orders

            # Write the content to connection.txt
            with open('connection.txt', 'w') as file:
                file.write(connection_content)

            # Clear the contents of saved_orders.txt
            with open('saved_orders.txt', 'w') as file:
                file.write('')

            await ctx.send(
                "Saved orders loaded into 'connection.txt' successfully. 'saved_orders.txt' has been cleared.")
        except FileNotFoundError:
            await ctx.send("Error: 'saved_orders.txt' not found.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name="deleteall", aliases=["delall"])
    async def delete_all_orders(self, ctx):
        replace_file_content("connection.txt", "deleteAll", "delete all orders")
        await ctx.send("All orders deleted")









