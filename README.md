# mc-bot

Discord bot that starts, stops, watches, backs up, and maps a Paper Minecraft server.

## What it does

- Start, stop, restart, and save the server from Discord (`/start`, `/stop`, `/restart`, `/save`)
- Idle shutdown when no one is online, with a countdown warning
- Crash detection vs intentional stop, with optional auto-restart
- Backups (manual and automatic) with list / restore / delete / keep
- Restore safety net: live worlds are renamed to `*.before-restore` and kept
- Live log relay and command audit to Discord channels
- On-demand top-down map (`/map`)
- Player stats, inventory, and health (`/stats`)
- Live console session (`/console`)
- Health alerts (TPS, RAM, stuck RCON) in Discord and in-game
- Wake-on-join: starting the server when a player tries to connect while it is off
- Multi-dimension stress test (`/stresstest`) with snapshot and restore
- Edit `server.properties` from Discord (`/serveredit`)

## Requirements

- Python 3.9+
- A Paper (or compatible) Minecraft server
- `tmux` (used for the console fallback)
- A Discord bot token
- Optional but recommended: RCON enabled on the Minecraft server (for player count, idle shutdown, TPS, and live console)

## How to set up and run

### 1. Get the code

```bash
git clone https://github.com/Spharax/mc-bot.git
cd mc-bot
```

### 2. Create a Discord bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application → Bot → copy the **Token**.
3. Under OAuth2 → URL Generator, select the `bot` and `applications.commands` scopes and invite the bot to your server.
4. Note your server (guild) ID and the channel IDs you want to use for alerts, logs, etc.

### 3. Create the `.env` file

Create a file named `.env` in the same folder as `botgrok.py` (do **not** commit this file):

```bash
# Required
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=123456789012345678

# Recommended channel IDs
MC_ALERT_CHANNEL_ID=123456789012345678
MC_LOG_CHANNEL_ID=123456789012345678
MC_AUDIT_CHANNEL_ID=123456789012345678

# Minecraft / server paths (adjust to your setup)
MC_START_SCRIPT=/path/to/your/start-mc.sh
MC_LOG_PATH=/path/to/minecraft/logs/latest.log
MC_SERVER_DIR=/path/to/minecraft

# RCON (optional but enables many features)
MC_RCON_HOST=127.0.0.1
MC_RCON_PORT=25575
MC_RCON_PASSWORD=your_rcon_password
```

See the table below and the docstring at the top of `botgrok.py` for the full list of variables and their defaults.

### 4. Enable RCON (optional but recommended)

In your Minecraft `server.properties`:

```
enable-rcon=true
rcon.port=25575
rcon.password=your_rcon_password
```

Restart the Minecraft server after changing this.

### 5. Run the bot

```bash
python3 botgrok.py
```

The bot will sync its slash commands to the guild you set in `DISCORD_GUILD_ID` and start monitoring.

### 6. Run it permanently (recommended)

Use `tmux`, `screen`, or a systemd service so it survives logout:

**tmux example:**
```bash
tmux new -s mcbot
python3 botgrok.py
# Detach with Ctrl+B then D
```

**Simple systemd unit** (save as `/etc/systemd/system/mc-bot.service`):
```ini
[Unit]
Description=mc-bot Discord Minecraft controller
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/mc-bot
ExecStart=/usr/bin/python3 /path/to/mc-bot/botgrok.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mc-bot
```

## Important environment variables

| Variable | Purpose |
|---|---|
| `DISCORD_TOKEN` | Bot token (required) |
| `DISCORD_GUILD_ID` | Guild to sync commands to |
| `MC_RCON_HOST` / `MC_RCON_PORT` / `MC_RCON_PASSWORD` | RCON connection |
| `MC_ALERT_CHANNEL_ID` | Crash, health, and idle alerts |
| `MC_LOG_CHANNEL_ID` | Minecraft log relay |
| `MC_AUDIT_CHANNEL_ID` | Who ran which command |
| `MC_BACKUP_DIR` | Where backups are stored |
| `MC_IDLE_SHUTDOWN` / `MC_IDLE_TIMEOUT` | Idle shutdown |
| `MC_AUTO_RESTART` | Restart after unexpected stops |
| `MC_HEALTH_*` | Health-alert thresholds |
| `MC_START_LOG_MAX_MB` / `MC_BOT_LOG_MAX_MB` | Log rotation sizes in MiB |

See the module docstring at the top of `botgrok.py` for the full list and defaults.

## Restore safety

`/backup restore` renames the current worlds to `*.before-restore` (or a timestamped name) before copying the backup in. Those copies are **not** deleted on success and are **not** removed by the pre-start cleanup, so a bad restore can be undone by hand. Only known world folders ending in `.old` or `.old-layout` are cleaned up automatically.

## Stress test

`/stresstest` takes a snapshot, then runs load bursts in the overworld, nether, and end (fills, chunk loading, mobs, explosions, etc.). The world is restored from the snapshot when the test ends.

## License

[MIT](LICENSE) © 2026 Spharax

Do not commit `.env`.
