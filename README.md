# mc-bot

Discord bot that starts, stops, watches, backs up, and maps a Paper or Purpur Minecraft server.

## What it does

- Start, stop, restart, and save the server from Discord
- Idle shutdown when nobody is online, with a countdown
- Crash detection versus an intentional stop, with optional auto-restart
- Wake-on-join: a player connecting while the server is off starts it
- Local backups, with list, restore, delete, and keep
- A Discord channel synced with in-game chat
- Health alerts (TPS, RAM, stuck RCON) in Discord and in-game
- Live console, top-down map, player stats, and `server.properties` editing
- A multi-dimension stress test that snapshots and restores the world

## Requirements

- Python 3.9+
- A Paper or Purpur server. `paper.jar` and `purpur.jar` are both detected.
- `tmux`, used when RCON is down
- A Discord bot token
- RCON is optional, but player count, idle shutdown, TPS, and the live console need it

## Setup

### 1. Get the code

```bash
git clone https://github.com/Spharax/mc-bot.git
cd mc-bot
python3 -m pip install -r requirements.txt  # if you keep a requirements file
```

The bot reads `discord.py`, `aiohttp`, and `python-dotenv`. Install those if they are not already present.

### 2. Create the Discord bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. New application, then Bot, then copy the token.
3. OAuth2, URL Generator: `bot` and `applications.commands`. Invite it.
4. Copy the server id and the channel ids you want for alerts, logs, and chat.
5. Give the bot Send Messages, Read Message History, and Manage Messages in the chat channel.

### 3. Write `.env`

Put `.env` next to `botgrok.py`. Do not commit it.

```bash
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=123456789012345678

MC_ALERT_CHANNEL_ID=123456789012345678
MC_LOG_CHANNEL_ID=123456789012345678
MC_AUDIT_CHANNEL_ID=123456789012345678
MC_CHAT_CHANNEL_ID=123456789012345678

MC_START_SCRIPT=/home/server/start-mc.sh
MC_LOG_PATH=/home/server/minecraft/logs/latest.log
MC_SERVER_DIR=/home/server/minecraft
MC_BACKUP_DIR=/home/server/backups

MC_RCON_HOST=127.0.0.1
MC_RCON_PORT=25575
MC_RCON_PASSWORD=your_rcon_password
```

### 4. Enable RCON

In `server.properties`:

```
enable-rcon=true
rcon.port=25575
rcon.password=your_rcon_password
```

Restart the Minecraft server after changing this. RCON is only read at startup.

### 5. Run it

```bash
python3 botgrok.py
```

It syncs slash commands to `DISCORD_GUILD_ID` and starts watching. On boot it pulls `origin/main` if that is ahead, then restarts onto the new code.

### 6. Keep it running

A systemd unit is the reliable way. Save as `/etc/systemd/system/mcbot.service`:

```ini
[Unit]
Description=mc-bot Discord Minecraft controller
After=network.target

[Service]
Type=simple
User=server
WorkingDirectory=/home/server/mc-bot
ExecStart=/usr/bin/python3 /home/server/mc-bot/botgrok.py
Restart=on-failure
KillMode=process

[Install]
WantedBy=multi-user.target
```

`KillMode=process` matters. The default kills every process in the service, including a Minecraft server the bot started.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mcbot
```

`/botreset` restarts the bot. It does not stop Minecraft.

## Commands

| Command | What it does |
|---|---|
| `/panel` | Buttons for the common actions |
| `/status` | Online, players, uptime |
| `/start` `/stop` `/restart` `/save` | Run the server. Stop and restart ask first. |
| `/health` | TPS, RAM, CPU, disk, temperature |
| `/players` `/tps` `/ping` `/pingall` | Who is on, tick time, latency |
| `/backup make` | Copy the worlds now |
| `/backup list` | List, delete, or pin a backup |
| `/backup restore` | Put a backup back. Admin. |
| `/say` | One line to Minecraft chat |
| `/chatclear` | Clear the synced chat channel |
| `/logdelete` | Delete local log files. Admin, confirms. |
| `/stresstest` | Load test, then restore the snapshot |
| `/stats` `/map` | A player's stats, or a top-down map |
| `/console` | Live console. Admin. |
| `/serveredit` | View or change `server.properties`. Admin. |
| `/rcontest` | Check the RCON connection |
| `/botstop` `/botreset` | Stop or restart the bot. Minecraft stays up. |

In Minecraft, while `MC_CHAT_BACKUP` is on: `!backup`, `!start`, `!tps`, `!pingall`, `!chatclear`.

Commands are refused in DMs. With `DISCORD_GUILD_ID` set, other servers are refused too. `/backup list`, `/backup restore`, `/console`, `/serveredit`, `/logdelete`, and `/botstop` need `MC_ADMIN_ROLE_ID`, or Administrator if that is unset.

## Chat sync

Set `MC_CHAT_CHANNEL_ID`. While the server is up:

- Minecraft chat is posted as `(Steve): hello`
- A message in that channel is said in-game as `<YourName> hello`
- Lines starting with `!` are commands, not relayed

It turns off when the server stops and back on when the server is up again, including after a bot reset. `/chatclear` and `!chatclear` delete the last 500 messages. The bot needs Manage Messages.

## Backups

`/backup make` copies the worlds into `MC_BACKUP_DIR` and writes `backup.txt`. That is the whole local backup. Nothing else is required.

`MC_BACKUP_COMMAND` is optional and does nothing when unset. It is not a shell. The program must be in `MC_BACKUP_ALLOW` (default `rclone,restic,rsync,borg,cp`), shell operators are rejected, and `{dest}` is the new folder as one argument:

```bash
MC_BACKUP_COMMAND=rclone copy {dest} remote:mc
```

`bash`, `python`, and `rm` are refused. A rejected or failing command fails the backup and the reason is reported. `{kind}` is `auto` or `manual`. `{number}` is the counter.

## Restore

`/backup restore` renames the live worlds to `*.before-restore`, then copies the backup in. On success those copies are deleted. Set `MC_RESTORE_DELETE=false` (or `RESTOREDELETE=false`) to keep them. A failed restore puts the old worlds back before anything is deleted. Plugins and config are not touched.

## Health

A warning fires after `MC_HEALTH_SUSTAIN` bad checks (default 3), then repeats every `MC_HEALTH_COOLDOWN` seconds (default 60). In-game it includes TPS, for example `server health is low. TPS 14.2`. The recovery line is green. A fresh server is ignored for `MC_HEALTH_GRACE` seconds.

## Logs

Warnings and errors go to the Discord log channel. Routine success lines are debug and do not. `/logdelete` removes bot logs, the start log, the manual log, Minecraft log archives, and crash reports. The live files are emptied, not unlinked, so the server keeps writing.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `DISCORD_TOKEN` | required | Bot token |
| `DISCORD_GUILD_ID` | 0 | Guild to sync commands to. 0 syncs globally. |
| `MC_SESSION` | `mc` | tmux session name |
| `MC_START_SCRIPT` | `~/start-mc.sh` | Script that launches the server |
| `MC_LOG_PATH` | `~/minecraft/logs/latest.log` | Server log |
| `MC_SERVER_DIR` | unset | Only count a JVM whose cwd is this folder |
| `MC_JAR_NAME` | `paper.jar,purpur.jar` | Jars that count as the server |
| `MC_RCON_HOST` / `PORT` / `PASSWORD` | `127.0.0.1` / `25575` / empty | Empty password disables RCON |
| `MC_ALERT_CHANNEL_ID` | 0 | Crash, health, and idle alerts |
| `MC_LOG_CHANNEL_ID` | 0 | Bot and Minecraft log relay |
| `MC_AUDIT_CHANNEL_ID` | 0 | Who ran which command |
| `MC_CHAT_CHANNEL_ID` | 0 | Synced chat channel. 0 is off. |
| `MC_BACKUP_DIR` | unset | Parent folder for backups |
| `MC_BACKUP_KEEP` | 20 | Finished backups kept per kind. 0 keeps all. |
| `MC_BACKUP_COMMAND` | empty | Optional program after a copy. Not a shell. |
| `MC_BACKUP_ALLOW` | `rclone,restic,rsync,borg,cp` | Binaries that command may run |
| `MC_RESTORE_DELETE` | true | Delete old worlds after a successful restore |
| `MC_AUTO_RESTART` | true | Restart after an unexpected stop |
| `MC_IDLE_SHUTDOWN` / `MC_IDLE_TIMEOUT` | true / 900 | Idle shutdown, in seconds |
| `MC_HEALTH_TPS` | 18 | Warn below this TPS |
| `MC_CHAT_BACKUP` | true | In-game `!` commands |

The docstring at the top of `botgrok.py` lists every variable.

## License

[MIT](LICENSE) © 2026 Spharax

Do not commit `.env`.
