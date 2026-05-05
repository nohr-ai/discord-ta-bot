# Discord TA-bot-template
A simple template for hosting discord servers for courses at uni, written in python.


# Features
Out of the box, this template offers/requires:

- Channel handling for students and a set of `n` closed groups
- Support for multiple servers with one bot


# Setup
All python dependencies can be found in requirements.txt, alternatively, you can install them from the poetry.lock file.

`python -m pip install -r requirements.txt` / `poetry install `/ `uv sync`

## Configuration
The bot requires that you have access to Discord developer portal. For a tutorial, have a look [here](https://discordjs.guide/preparations/setting-up-a-bot-application.html#creating-your-bot).

In the repository you will find a file `env_example` with some config values. The mandatory values are:

- `DISCORD_TOKEN`: Access token to the discord API. Without this you won't be able to interact with your server. This is a password, keep it safe.

The bot is by defautl setup with rotating filehandlers for logging. You can modify how many files you will allow and their size with the config variables below.
- `LOGFILE_SIZE`: Size in B for your logfiles, default 1MB.
- `LOGFILE_COUNT`: Number of logfiles before the handlers wrap around and overwrites the earliest logfile, default 10.
- `LOGFILE_FORMAT`: Format of the log output. Default: log-level name time log-message


# Running the bot
After setting up the environment you can hopefully run the bot with:
```
python discord-ta-bot/Bot.py
```
Alternatively
```
poetry run python discord-ta-bot/Bot.py
```
```
uv run discord-ta-bot/Bot.py
```
