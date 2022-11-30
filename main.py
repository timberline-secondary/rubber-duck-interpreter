import subprocess
from datetime import date, datetime, timedelta
import humanize
import os
import ast
import platform
import psutil
import re
from typing import Any, Tuple

import multiprocess
from discord import Intents
from pathos.multiprocessing import ProcessPool

import dotenv
import discord
from discord.ext import commands
import RestrictedPython
from RestrictedPython import compile_restricted, limited_builtins, safe_builtins, utility_builtins
from RestrictedPython.PrintCollector import PrintCollector

dotenv.load_dotenv()

load_start_delta = datetime.now()


def get_uptime():
    tdelta = datetime.now() - load_start_delta
    d = {}
    d["%H"], rem = divmod(tdelta.seconds, 3600)
    d["%M"], d["%S"] = divmod(rem, 60)
    return f"{str(d['%H']) + 'h ' if d['%H'] > 0 else ''}{str(d['%M']) + 'm ' if d['%M'] > 0 else ''}{str(d['%S']) + 's' if d['%S'] > 0 else ''}"


def interpret(code: str) -> Tuple[str, str]:
    """Interprets the given python code inside a safe execution environment"""
    code += "\nresults = printed"
    byte_code = compile_restricted(
        code,
        filename="<string>",
        mode="exec",
    )
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
    exec(byte_code, data, None)
    return data["results"]


def get_git_info() -> str:
    last_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)[:8]
    current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True)
    return f"{last_commit} @ {current_branch}"


class RubberDuck(discord.Client):
    def __init__(self, *, intents: Intents, **options: Any):
        super().__init__(intents=intents, **options)
        self.pool = ProcessPool(nodes=4)

    async def on_ready(self):
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="your python | [>>]"))
        print(f"[{datetime.now()}] logged in as {self.user}")

    async def on_message(self, message):
        command_str = ">>"
        content = message.content
        if content.startswith(command_str):
            # remove the command prefix itself and (maybe) a space
            source = re.sub(r"{} ?".format(command_str), "", content, 1)
            # remove code markers so code boxes work
            source = re.sub(r"(^`{1,3}(py(thon)?)?|`{1,3}$)", "", source)
            # log output to help debugging on failure
            print(f"[{datetime.now()}] Executed {repr(source)}")
            sent = await message.channel.send(embed=discord.Embed(title="Running code...", color=0x2F3136))

            start_compile = datetime.now()

            embedded = discord.Embed(title="Rubber Duck / Interpret", color=0x2F3136)
            embedded.set_author(name="Rubber Duck", url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                                icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")

            embedded.set_footer(text=f"Rubber Duck - Input from {message.author} ・ {date.today()}")

            result = self.pool.apipe(interpret, source)
            output = None
            try:
                output = result.get(timeout=10)
            except multiprocess.context.TimeoutError:
                output = "Timeout error - do you have an infinite loop?"
            except Exception as e:
                output = "Runtime error: {}".format(e)

            end_compile = datetime.now()

            elapsed_time = humanize.precisedelta(end_compile - start_compile, minimum_unit="milliseconds",
                                                 format="%0.3f")

            embedded.add_field(name="Evaluation",
                               value=f"Input:\n```python\n{source}```",
                               inline=False)
            embedded.add_field(name="\u200B",
                               value="Output:\n```python\n{}```".format(output or "(no output to stdout)"),
                               inline=False)
            embedded.add_field(name="\u200B",
                               value=f"took {elapsed_time}",
                               inline=False)

            await sent.edit(embed=embedded)
        elif content.startswith("<@1047186063606698016> "):
            command = content.replace("<@1047186063606698016> ", "")

            if command == "version" or command == "stats" or command == "info":
                _, _, load_15 = psutil.getloadavg()
                average_usage = (load_15 / os.cpu_count()) * 100

                embedded = discord.Embed(title="Rubber Duck / Info", color=0x2F3136)
                embedded.add_field(name="\u200B",
                                   value=f"Python version:\n`v{platform.python_version()}`",
                                   inline=False)
                embedded.add_field(name="\u200B",
                                   value=f"Rubber Duck Version:\n`{get_git_info()}`",
                                   inline=False)
                embedded.add_field(name="\u200B",
                                   value=f"Uptime:\n`{get_uptime()}`",
                                   inline=False)
                embedded.add_field(name="\u200B",
                                   value=f"CPU usage (average):\n`{average_usage:.1f}%`",
                                   inline=False)
                embedded.add_field(name="\u200B",
                                   value=f"RAM Used:\n`{(psutil.virtual_memory()[3] / 1000000000):.2f}GB ({psutil.virtual_memory()[2]:.1f}%)`",
                                   inline=False)
                embedded.set_author(name="Rubber Duck", url="https://en.wikipedia.org/wiki/Rubber_duck_debugging",
                                    icon_url="https://cdn.discordapp.com/avatars/1047186063606698016/5f73a9caae675ae8d403adaab8f50a8e.webp?size=64")
                embedded.set_footer(text=f"Rubber Duck - Input from {message.author} ・ {date.today()}")

                await message.reply(embed=embedded)

    def run(self):
        token = os.getenv("TOKEN")
        if token:
            super().run(token)
        else:
            raise EnvironmentError("TOKEN environment variable doesn't exist")


intents = discord.Intents.default()
intents.message_content = True

bot = RubberDuck(intents=intents)
bot.run()
