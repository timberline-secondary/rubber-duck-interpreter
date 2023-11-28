### Python Interpreter Bot

A simple and straight-forward discord bot to handle running python in a secure environment, providing and easy way to debug code, while in discord.

Invite the bot --> [here](https://discord.com/oauth2/authorize?client_id=1047186063606698016&scope=bot&permissions=2147485696)

##### How?

The bot is running in a dockerized environment (using python:3.11) and is set to automatically start-up on the server through the `rubber_duck.service` file.

##### Python execution

Using the `>>` will trigger the bot to run any python code that comes after it, and yes, code-blocks are supported.

##### Utility commands

- Stats [stat/up/info]: Get statistics of the bot.
- Ping [latency]: Sends the bot's latency.

##### Restart

The restart command kills the docker container, pulling new updates from github and creating a _new_ docker container, while not creating a docker-in-docker container.

Of course, this is only avaliable to certain people..

##### Inspiration

This bot is based off of [BenjaminHinchliff's Discord Python Interpreter Bot](https://github.com/BenjaminHinchliff/discord-python-interpreter-bot)
