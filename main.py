import subprocess
from datetime import date, datetime
import humanize
import os
import ast
import platform
import psutil
import re
from typing import Tuple

import multiprocess
from pathos.multiprocessing import ProcessPool

import dotenv
import discord
from discord.ext import bridge
import RestrictedPython
from RestrictedPython import compile_restricted, limited_builtins, safe_builtins, utility_builtins
from RestrictedPython.PrintCollector import PrintCollector

# Load environment variables from a .env file
dotenv.load_dotenv()

# Record the time at which the script was started
load_start_delta = datetime.now()


def get_uptime() -> str:
    """Calculate and return the uptime of the script"""
    tdelta = datetime.now() - load_start_delta
    d = {}
    d["%H"], rem = divmod(tdelta.seconds, 3600)
    d["%M"], d["%S"] = divmod(rem, 60)
    return f"{str(d['%H']) + 'h ' if d['%H'] > 0 else ''}{str(d['%M']) + 'm ' if d['%M'] > 0 else ''}{str(d['%S']) + 's' if d['%S'] > 0 else ''}"


def interpret(code: str) -> Tuple[str, str]:
    """Interpret the given code in a safe execution environment and return the results"""
    # Append the code to collect the printed output
    code += "\nresults = printed"

    # Compile the code using RestrictedPython
    byte_code = compile_restricted(
        code,
        filename="<string>",
        mode="exec",
    )

    # Create a safe execution environment
    data = {
        "_print_": PrintCollector,
        "__builtins__": {
            **limited_builtins,
            **safe_builtins,
            **utility_builtins,
            "all": all,
            "any": any,
            "_getiter_": RestrictedPython.Eval.default_guarded_getiter,
            "_iter_unpack_sequence_": RestrictedPython.Guards.guarded_iter_unpack_sequence
        },
        "_getattr_": RestrictedPython.Guards.safer_getattr
    }

    # Execute the code in the safe environment
    exec(byte_code, data, None)

    # Return the printed output
    return data["results"]


def get_git_info() -> str:
    """Get the latest git commit hash and branch and return them as a string"""
    # Get the latest commit hash
    last_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)[:8]

    # Get the current branch
    current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True)

    # Return the commit hash and branch as a string
    return f"{last_commit} @ {current_branch}"


intents = discord.Intents.default()
intents.message_content = True

# Create a Discord bot instance with the specified command prefix, intents, and no help command, to be overwritten by custom
bot = bridge.Bot(command_prefix="<@1047186063606698016> ", intents=intents, help_command=None)

# Load the ID of the message to be edited when the bot is restarted from the environment variables
reboot_id = os.getenv("REBOOT_ID")

# Create a process pool with 4 nodes
pool = ProcessPool(nodes=4)


# Event handler for when the bot is ready
@bot.event
async def on_ready():
    # If a reboot ID was specified, edit the message with the specified ID
    if reboot_id:
        # Create an embedded message
        embedded = discord.Embed(title="Rubber Duck has been restarted! :white_check_mark:", color=0x2F3136)
        embedded.set_author(name="Rubber Duck / Restarted",
                            url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                            icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")
        embedded.set_footer(text=f"Rubber Duck - Restarted @ {date.today()}")

        # Extract the channel ID and message ID from the reboot ID
        channel_id = int(reboot_id.split("-")[0])
        message_id = int(reboot_id.split("-")[1])

        # Get the message from the specified channel and update it with the embedded message
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        await message.edit(embed=embedded)

    # Set the bot's presence on Discord
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.listening, name="your python | [>>]"))

    # Log a startup message to the console
    print(f"[{datetime.now()}] logged in as {bot.user}")


# Event handler for when a message is sent on Discord
@bot.event
async def on_message(message):
    # process commands
    await bot.process_commands(message)

    # not a command, try to interpret
    command_str = ">>"
    content = message.content
    if content.startswith(command_str):
        # Remove the command prefix and any space after it
        source = re.sub(r"{} ?".format(command_str), "", content, 1)

        # Remove code markers so code boxes work
        source = re.sub(r"(^`{1,3}(py(thon)?)?|`{1,3}$)", "", source)

        # Log the code that is being executed
        print(f"[{datetime.now()}] Executed {repr(source)}")

        # Send a message indicating that the code is running
        sent = await message.reply(embed=discord.Embed(title="Running code...", color=0x2F3136))

        # Record the start time of the code execution
        start_compile = datetime.now()

        # Create an embedded message to display the code output
        embedded = discord.Embed(title="Rubber Duck / Interpret", color=0x2F3136)
        embedded.set_author(name="Rubber Duck", url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                            icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")

        # Add the user and the current date to the footer of the embedded message
        embedded.set_footer(text=f"Rubber Duck - Input from {message.author} ・ {date.today()}")

        # Execute the code in a separate process
        result = pool.apipe(interpret, source)
        output = None

        # Try to get the output of the code execution, with a timeout of 10 seconds
        try:
            output = result.get(timeout=10)
        except multiprocess.context.TimeoutError:
            output = "Timeout error - do you have an infinite loop?"
        except Exception as e:
            output = "Runtime error: {}".format(e)

        # Record end of runtime
        end_compile = datetime.now()

        # Combine the start time and end time to create and elapsed time value
        elapsed_time = humanize.precisedelta(end_compile - start_compile, minimum_unit="milliseconds",
                                             format="%0.3f")

        # Create an embed for the interpreted code
        embedded.add_field(name="Evaluation",
                           value=f"Input:\n```python\n{source}```",
                           inline=False)
        embedded.add_field(name="\u200B",
                           value="Output:\n```python\n{}```".format(output or "(no output to stdout)"),
                           inline=False)
        embedded.add_field(name="\u200B",
                           value=f"took {elapsed_time}",
                           inline=False)

        # Edit the message to update it with the interpreted code
        await sent.edit(embed=embedded)


@bot.bridge_command(aliases=["stat", "info", "up"], description="Get statistics of Rubber Duck.")
async def stats(ctx):
    # get the load average in the last 15 minutes
    _, _, load_15 = psutil.getloadavg()

    # compute average CPU usage based on the number of cores
    average_usage = (load_15 / os.cpu_count()) * 100

    # create an embedding to hold the stats
    embedded = discord.Embed(title="Rubber Duck / Info", color=0x2F3136)

    # add fields with relevant stats
    embedded.add_field(name="\u200B",
                       value=f"Python version:\n`v{platform.python_version()}`",
                       inline=True)
    embedded.add_field(name="\u200B",
                       value=f"Rubber Duck Version:\n`{get_git_info()}`",
                       inline=True)
    embedded.add_field(name="\u200B",
                       value=f"Uptime:\n`{get_uptime()}`",
                       inline=True)
    embedded.add_field(name="\u200B",
                       value=f"CPU usage (average):\n`{average_usage:.1f}%`",
                       inline=True)
    embedded.add_field(name="\u200B",
                       value=f"RAM Used:\n`{(psutil.virtual_memory()[3] / 1000000000):.2f}GB ({psutil.virtual_memory()[2]:.1f}%)`",
                       inline=True)

    # set the author and footer of the embedding
    embedded.set_author(name="Rubber Duck", url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                        icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")
    embedded.set_footer(text=f"Rubber Duck - Input from {ctx.author} ・ {date.today()}")

    # send the embedding as a reply to the original command
    await ctx.reply(embed=embedded)


@bot.bridge_command(aliases=["rs"], description="Restart the docker instance.")
async def restart(ctx):

    # Check if the user who triggered the command has the correct ID
    if ctx.author.id == 291050399509774340:

        # Create an embedded message with the text "Restarting..."
        embedded = discord.Embed(title="Restarting...", color=0x2F3136)

        # Create an embed
        embedded.set_author(name="Rubber Duck / Restarting",
                            url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                            icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")
        embedded.set_footer(text=f"Rubber Duck - Restarting... @ {date.today()}")

        # Send the message
        sent = await ctx.reply(embed=embedded)

        # Store the channel ID and the message ID in the reboot_id variable
        reboot_id = f"{sent.channel.id}-{sent.id}"

        # Get the TOKEN environment variable
        token = os.getenv("TOKEN")

        # Change the bot's presence to "do not disturb"
        await bot.change_presence(status=discord.Status.do_not_disturb)

        # Call the "reboot" script with the reboot_id and the TOKEN
        subprocess.check_output(["./reboot", reboot_id, token])
    else:
        # If the user does not have the correct ID, send an error message
        embedded = discord.Embed(title=":warning: Insufficient Permissions!", color=0x2F3136)
        embedded.set_author(name="Rubber Duck / Restart",
                            url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                            icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")
        embedded.set_footer(text=f"Rubber Duck - Restart failed @ {date.today()}")
        await ctx.reply(embed=embedded)


@bot.bridge_command(aliases=["?", "??"], description="Sends all the available commands for the bot.")
async def help(ctx):

    # Define a list of available commands
    command_list = [
        {"name": "stats", "aliases": ["stat", "info", "up"], "desc": "Get statistics of Rubber Duck."},
        {"name": "restart", "aliases": ["rs"], "desc": "Restart the docker instance."}, {"name": "ping", "aliases": ["latency"], "desc": "Sends the bot's latency."}
    ]

    # Create an embedded message with the title "Commands"
    embedded = discord.Embed(title="Commands", color=0x2F3136)

    # For each command in the list, add a field to the message with the command's name, aliases, and description
    for command in command_list:
        embedded.add_field(name=command["name"],
                           value=f"aliases: {', '.join(command['aliases'])}\n{command['desc']}", inline=True)

    # Add a field to the message with information about using the interpreter
    embedded.add_field(name="Interpreter",
                       value="To run the python interpreter prefix any python code (including code-blocks) with >> to run the interpreter\n\ni.e.: >> print('hello, world!')",
                       inline=False)

    # Set the author of the message
    embedded.set_author(name="Rubber Duck / Help", url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                        icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")

    # Set the footer of the message with the current date
    embedded.set_footer(text=f"Rubber Duck - Help ・ {date.today()}")

    # Send the message
    await ctx.reply(embed=embedded)


@bot.bridge_command(aliases=["latency"], description="Sends the bot's latency.")
async def ping(ctx):
    embedded = discord.Embed(title="Ping has been appreciated! :white_check_mark:", color=0x2F3136)
    embedded.set_author(name="Rubber Duck / Ping",
                        url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                        icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")
    embedded.set_footer(text=f"Ping: {bot.latency:.2f}ms")
    await ctx.reply(embed=embedded)


bot.run(os.getenv("TOKEN"))
