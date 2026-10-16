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
- `tmux` for the console fallback
- Discord bot token
- Optional: RCON enabled for player count, idle shutdown, TPS, and console

## Setup

1. Create `.env` next to `botgrok.py` (do not commit it).
2. Set at least:
   - `DISCORD_TOKEN`
   - `DISCORD_GUILD_ID`
   - Channel IDs (`MC_ALERT_CHANNEL_ID`, `MC_LOG_CHANNEL_ID`, etc.)
   - `MC_RCON_PASSWORD` if you want RCON features
3. Point `MC_START_SCRIPT`, `MC_LOG_PATH`, and `MC_SERVER_DIR` at your server.
4. Run:
   ```bash
   python3 botgrok.py
   ```
   Or use a systemd unit.

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
