# Discord TA-bot-template
A simple template for hosting discord servers for courses at uni, written in python.


# Features
Out of the box, this template offers/requires:

- Automatic role assignment
- Support for multiple servers with one bot
  
Requires:
- Support for MongoDB
  - Unless you change the DB binding


# Setup
All python dependencies can be found in requirements.txt, alternatively, you can install them from the poetry.lock file.

`python -m pip install -r requirements.txt` / `poetry install`

## MongoDB
**Local**

To setup a local instance of MonboDB you can follow MongoDB.inc's manual [here](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/#std-label-install-mdb-community-ubuntu) for Ubuntu. They have guides for other environments such as Red Hat, Debian,SUSE, macOS, and Windows.

As of January 2024 you can do the following for Ubuntu 22.04 LTS (jammy):

1.  `sudo apt install gnupg curl`
2.  `curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor`
3.  `echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list`
4.  `sudo apt update`
5.  `sudo apt-get install -y mongodb-org`

For adjusting system limitations, see MongoDB.inc's guide, link above.


**Atlas**

To setup a remotely hosted free DB instance, you can follow the guide [here](https://www.mongodb.com/docs/atlas/getting-started/).


### Run
---
**systemd**

1. `sudo systemctl start mongod`
   1. If this fail, try: `sudo systemctl daemon-reload` and retry the first
2. `sudo systemctl status mongod` to verify it's running, optinally enable it to start on reboot: `sudo systemctl enable mongod`

Note: If you have an older system you might miss cpu-extensions that MongoDB uses, if you cannot start the server (core dump) you can try community/older versions of mongodb.

## Configuration
The bot requires that you have access to Discord developer portal. For a tutorial, have a look [here](https://discordjs.guide/preparations/setting-up-a-bot-application.html#creating-your-bot).

In the repository you will find a file `env_example` with some config values. The mandatory values are:

- `DISCORD_TOKEN`: Access token to the discord API. Without this you won't be able to interact with your server. This is a password, keep it safe.
- `DATABASE_URI`: Connection link to your mongoDB instance.
- `DATABASE_NAME`: The name of the database you have setup either locally or remotely.

Optional values:
- `CANVAS_URL`: Base url for your canvas instance.
- `CANVAS_TOKEN`: Access token to the canvas API.
- `GITHUB_TOKEN`: Access token for the Github API.
- `GITHUB_URL`: Base url for your github organization.
The bot is by defautl setup with rotating filehandlers for logging. You can modify how many files you will allow and their size with the config variables below.
- `LOGFILE_SIZE`: Size in B for your logfiles, default 1MB.
- `LOGFILE_COUNT`: Number of logfiles before the handlers wrap around and overwrites the earliest logfile, default 10.
- `LOGFILE_FORMAT`: Format of the log output. Default: log-level name time log-message


