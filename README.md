# mc-bot

Discord bot for a Paper Minecraft server.

It starts and stops the server, takes backups, relays logs, draws an on-demand map, and starts the server when someone tries to join while it is off.

## Setup

1. Copy `.env.example` if you have one, or create `.env` next to `botgrok.py`.
2. Set `DISCORD_TOKEN` and the channel and role IDs.
3. Run `python botgrok.py`,or 'python3 botgrok,py' or use the systemd unit.

Do not commit `.env`. It holds the bot token and the RCON password.
ig das ist it 
