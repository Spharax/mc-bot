#!/usr/bin/env python3
"""Discord bot that starts, stops, and watches a Paper/Minecraft server.

Environment (see .env next to this file):

  DISCORD_TOKEN            required
  DISCORD_GUILD_ID         this server only (0 = global sync; DMs are still refused)
  MC_SESSION               tmux session name (default mc)
  MC_START_SCRIPT          start script (default ~/start-mc.sh)
  MC_LOG_PATH              server log (default ~/minecraft/logs/latest.log)
  MC_START_LOG             start-script log (default ~/mc-bot-start.log)
  MC_JAR_NAME              jar name used to find the process (default paper.jar)
  MC_SERVER_DIR            optional: only count a JVM whose working directory is
                           this folder (use it if two Paper servers may run)
  MC_RCON_HOST             default 127.0.0.1
  MC_RCON_PORT             default 25575
  MC_RCON_PASSWORD         empty disables RCON, player count, and idle shutdown
  MC_ALERT_CHANNEL_ID      crash / auto-restart / health alerts
  MC_ALERT_MENTION         optional ping prefix on crash alerts
  MC_AUDIT_CHANNEL_ID      who ran which command (0 = keep audit in the log channel)
  MC_AUTO_RESTART          default true
  MC_AUTO_RESTART_MAX      default 3 (0 = never auto-restart)
  MC_AUTO_RESTART_WINDOW   seconds, default 1800 (30 minutes)
  MC_IDLE_SHUTDOWN         default true
  MC_IDLE_TIMEOUT          seconds, default 900 (15 minutes), minimum 60
  MC_IDLE_CHANNEL_ID       defaults to MC_ALERT_CHANNEL_ID
  MC_BACKUP_DIR            parent folder; each backup is a subfolder
  MC_BACKUP_SOURCE         comma-separated paths to copy (default: worlds)
  MC_BACKUP_COMMAND        optional command after the copy; MC_BACKUP_DEST is set
  MC_BACKUP_TIMEOUT        seconds, default 600
  MC_BACKUP_KEEP           finished backups kept per kind (auto, manual), default 20;
                           older ones are deleted after a successful backup. 0 = keep all
  MC_CHAT_BACKUP           in-game !backup / !pingall / !tps / !start for any player, default true
  MC_START_CHANNEL_ID      Discord channel that accepts !start, default 1556021831218110564
  MC_CHAT_BACKUP_COOLDOWN  seconds between in-game !backup runs, default 600
  MC_STATE_DIR             lock, backup counters, autosave marker (default: bot dir)
  MC_BOT_LOG_DIR           bot's own log files (default: state dir/logs)
  MC_MANUAL_LOG_CHANNEL_ID /log output only; not the mc-bot or Minecraft channel
  MC_MANUAL_LOG_PATH       file for /log lines (default: manual.log in bot log dir)
  MC_ENV_FILE              optional extra env file, loaded over the one beside the bot
  MC_AUTO_BACKUP           default false; offline-only backup after uptime/playtime
  MC_AUTO_BACKUP_AFTER     seconds of uptime or playtime, default 21600 (6 hours)
  MC_AUTO_BACKUP_METRIC    uptime (process running) or playtime (someone online)
  MC_AUTO_BACKUP_SKIPS     missed intervals before a warning, default 2
  MC_AUTO_BACKUP_RETRY     seconds before a failed auto-backup is tried again
  MC_MONITOR_INTERVAL      seconds, default 15, minimum 5
  MC_POLL_INTERVAL         seconds between process checks while waiting, default 5
  MC_EDIT_INTERVAL         min seconds between progress-message edits, default 10
  MC_STOP_TIMEOUT          seconds, default 180
  MC_START_TIMEOUT         seconds, default 300
  MC_LAUNCH_TIMEOUT        seconds, default 60
  MC_LOG_FALLBACK_AFTER    seconds, default 30
  MC_PORT_WAIT             seconds after stop before start, default 5
  MC_ADMIN_ROLE_ID         role for /backup list, /backup restore, console,
                           serveredit and botstop (unset = Administrator
                           permission instead)
  MC_LOG_CHANNEL_ID        channel that receives the bot log ([mc-bot]) and the
                           Minecraft log ([Minecraft]); 0 = off. Bot lines use
                           the host timezone; Minecraft lines keep the server's
  MC_AUDIT_LEVEL           lowest audit line posted, default INFO (independent
                           of MC_LOG_DISCORD_LEVEL)
  MC_BOT_LOG_MAX_MB        size of one bot log file before rotating, default 2 MiB
  MC_START_LOG_MAX_MB      rotate the start-script log at this size, default 2 MiB
  MC_LOG_BOT               relay the bot's own log lines, default true
  MC_LOG_MINECRAFT         relay latest.log (with start/stop separators), default true
  MC_LOG_DISCORD_LEVEL     lowest level of bot lines sent to Discord, default INFO
  MC_LOG_FLUSH_INTERVAL    seconds lines are batched before posting, default 2
  MC_LOG_TAIL_INTERVAL     seconds between reads of latest.log, default 2
  MC_LOG_QUEUE_MAX         lines held while Discord is slow, default 2000
  MC_HEALTH_ALERTS         warn about high RAM, low TPS, a stuck server (true);
                           CPU is only shown in the warning, never a trigger
  MC_HEALTH_INTERVAL       seconds between health checks, default 30
  MC_HEALTH_RAM            with -Xmx: warn when RSS grows past the heap by the
                           larger of 1 GiB or (100 - this)% of the heap (a full
                           heap is normal). With no -Xmx: warn when the Minecraft
                           process uses this % of system RAM. Default 90.
                           Other programs do not trigger it. CPU never triggers.
  MC_HEALTH_TPS            warn when TPS is below this, default 18
  MC_HEALTH_SUSTAIN        checks in a row before a warning, default 3
  MC_HEALTH_STUCK_AFTER    seconds without an RCON answer = stuck, default 60
  MC_HEALTH_GRACE          seconds after a server start to ignore, default 180
  MC_HEALTH_COOLDOWN       min seconds between health messages (Discord and in-game), default 60
  MC_PROPERTIES_PATH       server.properties for /serveredit (default: next to the
                           logs folder of MC_LOG_PATH, or MC_SERVER_DIR)
  MC_CONSOLE_INTERVAL      seconds between /console refreshes, default 3
  MC_LOG_LEVEL             console + file level: DEBUG/INFO/WARNING/ERROR, default INFO
  MC_BOT_LOG_FILE          rotating bot log file (default logs/mc-bot.log, off = none)
  MC_LOG_KEEP              local files kept for normal logs, default 20
  MC_LOG_KEEP_HIGH         files kept for high-volume logs (the server's dated
                           archives, start-script log, manual log), default 5.
                           Crash reports are kept (newest 50)
  MC_LOG_PRUNE_INTERVAL    seconds between local log cleanup, default 600
  Discord channels are not trimmed. Local files are.

Commands are refused in DMs. When DISCORD_GUILD_ID is set, other servers are
refused too. Every command is open to members of that server except /backup
list, /backup restore, console, serveredit and botstop, which need
MC_ADMIN_ROLE_ID (or the Administrator permission when it is unset). Stop and
restart ask for confirmation first. /ping only accepts a public IP. In game,
any player can type !backup (one per MC_CHAT_BACKUP_COOLDOWN), !pingall and !tps
while MC_CHAT_BACKUP is on.
Permission and busy checks run before the first await and every long command
defers right after them, so Discord does not expire the interaction (error
10062) and refusals stay private (an ephemeral reply is only honoured if it is
the first response).

In-game lines from say_bot() (health, warnings, ping list) are sent as `say [bot-warn]: ...`. say_game() (including /say) uses `say [bot]: ...`.
Health warnings (TPS under the limit, high server RAM, stuck RCON) are also
said in Minecraft chat, and that line repeats on the same cooldown as Discord
(default 60s) while the problem lasts. A failed in-game line is logged once
per cooldown, not on every check.

How the monitor tells a crash from a stop: before the bot sends `stop` it
records the process and the latest.log inode and size. `Stopping server`
counts only if it is appended after that point in the same file. A line from
an earlier boot cannot excuse this exit. If the log is rotated before that
line appears, the requested stop is not called a crash. If the process is
still alive after EXPECTED_STOP_MAX, or dies after that window, it is a crash
even if `Stopping server` was logged. An in-game /stop has no recorded offset,
so that path still reads the last 512 KB.

Requires Python 3.9+ (asyncio.to_thread).
"""

import asyncio
import collections
import random
import difflib
import functools
import gzip
import io
import struct
import zlib
import ipaddress
import json
import logging
import logging.handlers
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import traceback
import typing
from types import SimpleNamespace

import aiohttp
import discord
from discord import app_commands
from dotenv import load_dotenv


# ============================================================
# ENV + LOGGING
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))
_extra_env = os.getenv("MC_ENV_FILE", "").strip()
if _extra_env:
    load_dotenv(os.path.expanduser(_extra_env), override=True)


def env_path(name, default=""):
    """Absolute path from an env var. Empty stays empty. ~ is expanded."""

    raw = os.getenv(name, "").strip()
    if not raw:
        raw = default
    if not raw:
        return ""
    return os.path.realpath(os.path.expanduser(raw))

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}
LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def env_level(name, default="INFO"):
    """Return a logging level from an environment variable."""
    return LOG_LEVELS.get(os.getenv(name, "").strip().upper(), LOG_LEVELS[default])


FILE_LEVEL = env_level("MC_LOG_LEVEL")

log = logging.getLogger("mcbot")
cmd_log = log.getChild("cmd")  # who ran which command

if not log.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter(LOG_FORMAT))
    _handler.setLevel(FILE_LEVEL)
    log.addHandler(_handler)
    # Every handler filters for itself (console and file: MC_LOG_LEVEL,
    # Discord channel: MC_LOG_DISCORD_LEVEL), so the logger passes everything.
    log.setLevel(logging.DEBUG)
    log.propagate = False


def env_int(name, default, minimum=None):
    """Read an integer environment variable, clamped to a minimum."""
    raw = os.getenv(name)
    value = default
    if raw is not None and raw.strip() != "":
        try:
            value = int(raw)
        except ValueError:
            reporter = log.error if name.endswith("_ID") else log.warning
            reporter("%s=%r is not a number, using %s", name, raw, default)
    # A zero interval would spin the event loop, so clamp where it matters.
    if minimum is not None and value < minimum:
        log.warning("%s=%s is below %s, using %s", name, value, minimum, minimum)
        value = minimum
    return value


def env_float(name, default, minimum=None):
    """Read a float environment variable, clamped to a minimum."""
    raw = os.getenv(name)
    value = default
    if raw is not None and raw.strip() != "":
        try:
            value = float(raw)
        except ValueError:
            log.warning("%s=%r is not a number, using %s", name, raw, default)
    if minimum is not None and value < minimum:
        log.warning("%s=%s is below %s, using %s", name, value, minimum, minimum)
        value = minimum
    return value


def env_bool(name, default=False):
    """Read a boolean environment variable (1/true/yes/on)."""
    raw = os.getenv(name, "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes", "on")


_last_warned = {}


def warn_throttled(key, message, *args, every=300):
    """Log a repeating condition (RCON down) at most once per `every` seconds."""

    now = time.monotonic()
    if now - _last_warned.get(key, -every - 1) > every:
        _last_warned[key] = now
        log.warning(message, *args)


# ============================================================
# CONFIG
# ============================================================

VERSION = "1.216"

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = env_int("DISCORD_GUILD_ID", 0)
ADMIN_ROLE_ID = env_int("MC_ADMIN_ROLE_ID", 0)
DISCORD_LIMIT = 1990

MC_SESSION = os.getenv("MC_SESSION", "mc")
START_SCRIPT = os.path.expanduser(os.getenv("MC_START_SCRIPT", "~/start-mc.sh"))
LOG_PATH = os.path.expanduser(
    os.getenv("MC_LOG_PATH", "~/minecraft/logs/latest.log")
)
START_LOG = os.path.expanduser(os.getenv("MC_START_LOG", "~/mc-bot-start.log"))
JAR_NAME = os.getenv("MC_JAR_NAME", "paper.jar")
# End-anchored, and the jar name must be its own path segment. mypaper.jar
# and paper.jar.bak are not the server.
SERVER_PATTERN = (
    r"^([^ ]*/)?java (?:.*[\s/\"'])?"
    + re.escape(JAR_NAME)
    + r"(?: |$)"
)
SERVER_DIR = env_path("MC_SERVER_DIR")
STATE_DIR = env_path("MC_STATE_DIR", BASE_DIR)
BOT_LOG_DIR = env_path("MC_BOT_LOG_DIR", os.path.join(STATE_DIR, "logs"))
BACKUP_DIR = env_path("MC_BACKUP_DIR")
MANUAL_LOG_PATH = env_path("MC_MANUAL_LOG_PATH", os.path.join(BOT_LOG_DIR, "manual.log"))
LOCK_PATH = env_path("MC_LOCK_PATH", os.path.join(STATE_DIR, ".mcbot.lock"))

RCON_HOST = os.getenv("MC_RCON_HOST", "127.0.0.1")
RCON_PORT = env_int("MC_RCON_PORT", 25575, 1)
RCON_PASSWORD = os.getenv("MC_RCON_PASSWORD", "")

ALERT_CHANNEL_ID = env_int("MC_ALERT_CHANNEL_ID", 0)
ALERT_MENTION = os.getenv("MC_ALERT_MENTION", "")
AUDIT_CHANNEL_ID = env_int("MC_AUDIT_CHANNEL_ID", 0)
BOT_WARN_PREFIX = "[bot-warn]:"
AUTO_RESTART = env_bool("MC_AUTO_RESTART", True)
AUTO_RESTART_MAX = env_int("MC_AUTO_RESTART_MAX", 3, 0)
AUTO_RESTART_WINDOW = env_int("MC_AUTO_RESTART_WINDOW", 1800, 1)
BACKUP_COMMAND = os.getenv("MC_BACKUP_COMMAND", "").strip()
CHAT_BACKUP = env_bool("MC_CHAT_BACKUP", True)
WAKE_ON_PING = env_bool("MC_WAKE_ON_PING", True)
START_CHANNEL_ID = env_int("MC_START_CHANNEL_ID", 1556021831218110564)
BACKUP_TIMEOUT = env_int("MC_BACKUP_TIMEOUT", 600, 1)
# Finished backups kept per kind (auto / manual); older ones are deleted after a
# successful backup. 0 keeps everything.
BACKUP_KEEP = env_int("MC_BACKUP_KEEP", 20, 0)
CHAT_BACKUP_COOLDOWN = env_int("MC_CHAT_BACKUP_COOLDOWN", 600, 0)
BACKUP_SOURCE = os.getenv("MC_BACKUP_SOURCE", "").strip()
# Automatic backups run only while the server is offline. /backup may still
# freeze a live world. The warning waits until this many intervals were skipped.
AUTO_BACKUP = env_bool("MC_AUTO_BACKUP", False)
AUTO_BACKUP_AFTER = env_int("MC_AUTO_BACKUP_AFTER", 21600, 60)
AUTO_BACKUP_METRIC = os.getenv("MC_AUTO_BACKUP_METRIC", "uptime").strip().lower()
if AUTO_BACKUP_METRIC not in ("uptime", "playtime"):
    log.warning(
        "MC_AUTO_BACKUP_METRIC=%r is not uptime or playtime, using uptime",
        AUTO_BACKUP_METRIC,
    )
    AUTO_BACKUP_METRIC = "uptime"
if AUTO_BACKUP_METRIC == "playtime" and not RCON_PASSWORD:
    log.warning("Playtime backups need MC_RCON_PASSWORD; counting uptime instead")
    AUTO_BACKUP_METRIC = "uptime"
AUTO_BACKUP_SKIPS = env_int("MC_AUTO_BACKUP_SKIPS", 2, 2)
AUTO_BACKUP_RETRY = env_int("MC_AUTO_BACKUP_RETRY", 1800, 60)
BACKUP_STATE_PATH = env_path("MC_BACKUP_STATE", os.path.join(STATE_DIR, ".backup-state.json"))
# Written while autosave is off so a killed bot can send save-on next start.
AUTOSAVE_MARKER = os.path.join(STATE_DIR, ".autosave-off")

IDLE_SHUTDOWN = env_bool("MC_IDLE_SHUTDOWN", True)
IDLE_TIMEOUT = env_int("MC_IDLE_TIMEOUT", 900, 60)
IDLE_CHANNEL_ID = env_int("MC_IDLE_CHANNEL_ID", 0) or ALERT_CHANNEL_ID
IDLE_EDIT_INTERVAL = 60
# Idle shutdown needs RCON (player count) and a channel for the warning.
IDLE_ACTIVE = IDLE_SHUTDOWN and bool(RCON_PASSWORD) and bool(IDLE_CHANNEL_ID)

MONITOR_INTERVAL = env_int("MC_MONITOR_INTERVAL", 15, 5)
POLL_INTERVAL = env_int("MC_POLL_INTERVAL", 5, 1)
EDIT_INTERVAL = env_int("MC_EDIT_INTERVAL", 10, 1)
STOP_TIMEOUT = env_int("MC_STOP_TIMEOUT", 180, 1)
START_TIMEOUT = env_int("MC_START_TIMEOUT", 300, 1)
LAUNCH_TIMEOUT = env_int("MC_LAUNCH_TIMEOUT", 60, 1)
LOG_FALLBACK_AFTER = env_int("MC_LOG_FALLBACK_AFTER", 30, 0)
# Java often needs a few seconds to release the port after exit.
PORT_WAIT = env_int("MC_PORT_WAIT", 5, 0)
SAVE_WAIT = 2
SAVE_TIMEOUT = 120
LOG_READ_MAX = 512_000
TOKEN_LIFETIME = 14 * 60  # interaction tokens die after 15 minutes
TOKEN_REANCHOR_AFTER = 12 * 60  # move long progress onto a bot message before that
# A bot-issued stop that hasn't taken effect after this long is forgotten.
# A timed-out stop only keeps this if the server logged "Stopping server".
EXPECTED_STOP_MAX = max(STOP_TIMEOUT * 4, 600)
AMBIGUOUS_ALERT_EVERY = 1800

# Discord log channel: [mc-bot] lines and the Minecraft log, in one place.
LOG_CHANNEL_ID = env_int("MC_LOG_CHANNEL_ID", 0)
MANUAL_LOG_CHANNEL_ID = env_int("MC_MANUAL_LOG_CHANNEL_ID", 0)
LOG_BOT = env_bool("MC_LOG_BOT", True)
LOG_MINECRAFT = env_bool("MC_LOG_MINECRAFT", True)
LOG_DISCORD_LEVEL = env_level("MC_LOG_DISCORD_LEVEL")
LOG_FLUSH_INTERVAL = env_int("MC_LOG_FLUSH_INTERVAL", 2, 1)
LOG_TAIL_INTERVAL = env_int("MC_LOG_TAIL_INTERVAL", 2, 1)
LOG_QUEUE_MAX = env_int("MC_LOG_QUEUE_MAX", 2000, 100)
LOG_RELAY_ACTIVE = bool(LOG_CHANNEL_ID) and (LOG_BOT or LOG_MINECRAFT)

# Local retention. Discord history is left alone.
LOG_KEEP = env_int("MC_LOG_KEEP", 20, 1)
LOG_KEEP_HIGH = env_int("MC_LOG_KEEP_HIGH", 5, 1)
LOG_PRUNE_INTERVAL = env_int("MC_LOG_PRUNE_INTERVAL", 600, 60)
START_LOG_MAX_BYTES = env_int("MC_START_LOG_MAX_MB", 2, 1) * 1024 * 1024
BOT_LOG_MAX_BYTES = env_int("MC_BOT_LOG_MAX_MB", 2, 1) * 1024 * 1024


def setup_file_logging():
    """Rotating log file next to the bot, so history survives a restart."""

    raw = os.getenv("MC_BOT_LOG_FILE", "").strip()
    if raw.lower() in ("off", "none", "false", "0"):
        return None

    path = os.path.expanduser(raw) if raw else os.path.join(BOT_LOG_DIR, "mc-bot.log")
    if not os.path.isabs(path):
        path = os.path.join(BOT_LOG_DIR, path)

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            path,
            maxBytes=BOT_LOG_MAX_BYTES,
            backupCount=LOG_KEEP,
            encoding="utf-8",
        )
    except OSError as error:
        log.warning("Can't write the bot log file %s: %s", path, error)
        return None

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    handler.setLevel(FILE_LEVEL)
    log.addHandler(handler)
    return path


BOT_LOG_FILE = setup_file_logging()


def _mtime(path):
    """Internal: mtime."""
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0


def prune_files(paths, keep):
    """Delete all but the newest `keep` files. Never follows directories."""

    files = [path for path in paths if os.path.isfile(path)]
    files.sort(key=_mtime, reverse=True)
    removed = 0
    for path in files[keep:]:
        try:
            os.remove(path)
            removed += 1
        except OSError:
            pass
    return removed


def rotate_capped(path, max_bytes, keep):
    """Rotate one append-only log and drop rotations past `keep`."""

    try:
        size = os.path.getsize(path)
    except OSError:
        return
    if size < max_bytes:
        prune_files([f"{path}.{i}" for i in range(1, keep + 3)], keep - 1)
        return
    for index in range(keep - 1, 0, -1):
        src = f"{path}.{index}"
        dst = f"{path}.{index + 1}"
        if not os.path.isfile(src):
            continue
        if index + 1 >= keep:
            try:
                os.remove(src)
            except OSError:
                pass
        else:
            try:
                os.replace(src, dst)
            except OSError:
                pass
    try:
        os.replace(path, f"{path}.1")
    except OSError:
        pass


# Only Minecraft's own rotated archives (2026-10-10-1.log.gz, debug-1.log.gz) are
# pruned. Plugin logs and anything else in logs/ are left alone.
SERVER_ARCHIVE_RE = re.compile(r"^(?:\d{4}-\d{2}-\d{2}-\d+|debug-\d+)\.log(?:\.gz)?$")
# Crash reports are small, rare, and the first thing needed after a crash.
CRASH_REPORTS_KEEP = 50


def prune_local_logs():
    """Delete old local logs. latest.log, plugin logs and Discord history are not touched."""

    removed = 0
    rotate_capped(START_LOG, START_LOG_MAX_BYTES, LOG_KEEP_HIGH)
    removed += prune_files(
        [f"{START_LOG}.{i}" for i in range(1, LOG_KEEP_HIGH + 5)],
        LOG_KEEP_HIGH - 1,
    )
    if BOT_LOG_FILE:
        removed += prune_files(
            [f"{BOT_LOG_FILE}.{i}" for i in range(1, LOG_KEEP + 5)],
            LOG_KEEP,
        )
    log_dir = os.path.dirname(LOG_PATH)
    live = os.path.basename(LOG_PATH)
    if os.path.isdir(log_dir):
        archived = []
        for name in os.listdir(log_dir):
            if name == live or name.startswith("."):
                continue
            if SERVER_ARCHIVE_RE.match(name):
                archived.append(os.path.join(log_dir, name))
        removed += prune_files(archived, LOG_KEEP_HIGH)
    root = os.path.dirname(log_dir)
    crash_dir = os.path.join(root, "crash-reports")
    if os.path.isdir(crash_dir):
        crashes = [
            os.path.join(crash_dir, name)
            for name in os.listdir(crash_dir)
            if name.endswith((".txt", ".log"))
        ]
        removed += prune_files(crashes, CRASH_REPORTS_KEEP)
    # Age-based cleanup so old logs cannot fill the disk.
    now = time.time()
    extra_dirs = [log_dir, crash_dir, BOT_LOG_DIR, os.path.join(BOT_LOG_DIR, "logs")]
    for directory in extra_dirs:
        if not directory or not os.path.isdir(directory):
            continue
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if not os.path.isfile(path) or name == live:
                continue
            age = now - _mtime(path)
            leftover = name.startswith("map-") and name.endswith(".png")
            # why: arbitrary .txt is not a log; crash reports are pruned by count above
            old_log = name.endswith((".log.gz", ".log.1")) or "debug" in name
            if leftover or (old_log and age > 2 * 86400):
                try:
                    os.remove(path)
                    removed += 1
                except OSError:
                    pass
    return removed


async def log_prune_loop():
    """Background loop that prunes old log files."""
    await bot.wait_until_ready()
    while True:
        try:
            removed = await asyncio.to_thread(prune_local_logs)
            if removed:
                log.info("Pruned %s old local log file(s)", removed)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Log prune failed")
        await asyncio.sleep(LOG_PRUNE_INTERVAL)


# ============================================================
# STATE
# ============================================================

# Only guild events are needed. The default intents also stream messages,
# typing, reactions and voice events that this bot never looks at.
intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

tps_lock = None

current_op = None
# Operations that start, stop or restart the server and report their own
# failures. A process exit during one of these is not a crash.
SELF_MANAGED_OPS = frozenset(
    {"start", "stop", "restart", "idle-shutdown", "auto-restart"}
)

# Set just before this bot sends `stop`: SimpleNamespace(pid, at, ino, offset).
# It names the one process whose exit is expected, so it can never excuse a
# different one. recent_stop is the same record kept after a timeout.
expected_stop = None
recent_stop = None

auto_restart_times = []
_bg_tasks = set()


def spawn(coro):
    """create_task that keeps a reference and logs failures."""

    def done(task):
        """Done."""
        _bg_tasks.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error("Background task failed", exc_info=task.exception())

    task = asyncio.create_task(coro)
    _bg_tasks.add(task)
    task.add_done_callback(done)
    return task


# ============================================================
# BOT
# ============================================================

def describe_user(user):
    """Return a short description of a Discord user."""
    return f"{user} ({user.id})"


def command_label(interaction):
    """Return the name of the command being invoked."""
    command = getattr(interaction, "command", None)
    return f"/{command.qualified_name}" if command is not None else "interaction"


def format_args(interaction):
    """Format command arguments for the audit log."""
    try:
        return " ".join(f"{key}={value!r}" for key, value in interaction.namespace)
    except Exception:
        return ""


class MCCommandTree(app_commands.CommandTree):
    """Writes one audit line for every slash command that is run."""

    async def interaction_check(self, interaction):
        """Interaction check."""
        try:
            cmd_log.info(
                "%s %s by %s (guild %s, channel %s)",
                command_label(interaction),
                format_args(interaction),
                describe_user(interaction.user),
                interaction.guild_id,
                interaction.channel_id,
            )
            capture_log(
                "commands",
                f"{command_label(interaction)} {format_args(interaction)} by {describe_user(interaction.user)}",
            )
        except Exception:
            pass  # logging must never block a command
        problem = guild_problem(interaction)
        if problem:
            # Autocomplete cannot send a chat reply. Returning False yields no choices.
            if interaction.type is discord.InteractionType.autocomplete:
                return False
            try:
                if not interaction.response.is_done():
                    await deny(interaction, problem)
            except EDIT_ERRORS:
                pass
            return False
        return True


class MCServerBot(discord.Client):
    """Discord bot that manages a Paper Minecraft server."""

    def __init__(self):
        """Internal: init."""
        super().__init__(
            intents=intents,
            max_messages=None,  # no message cache needed
            # Nothing the bot sends may ping, unless a call opts in (alerts).
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.tree = MCCommandTree(self)
        self.monitor_task = None
        self.health_task = None
        self.prune_task = None
        self._cleaned_up = False
        self._booted = False   # one-time setup done (setup_hook runs on every login)
        self._started = False  # background tasks started

    async def setup_hook(self):
        """Setup hook."""
        # discord.py calls this on every login(), and run_bot_forever() may log
        # in again after a network failure. Only the command sync repeats.
        if not self._booted:
            self._booted = True
            await self._first_boot()
        await self._sync_commands()
        if not self._started:
            self._started = True
            await self._start_background()

    async def _first_boot(self):
        """Internal: first boot."""
        global tps_lock

        # Created here, inside the running loop. Python 3.9+ is required
        # (asyncio.to_thread); locks bind to the running loop at creation.
        tps_lock = asyncio.Lock()

        install_loop_handlers(asyncio.get_running_loop())
        if LOG_RELAY_ACTIVE:
            start_log_relay()  # first, so everything below reaches the channel
        log_startup_banner()

    async def _sync_commands(self):
        """Internal: sync commands."""
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            # Guild sync plus leftover global commands shows each command twice.
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            log.info("Slash commands synced to guild %s and cleared globally", GUILD_ID)
        else:
            await self.tree.sync()
            log.info("Global slash commands synced")

    async def _start_background(self):
        """Internal: start background."""
        log_startup_notes()
        log_props_note()
        spawn(startup_rcon_check())
        spawn(tps_sample_loop())
        spawn(warn_server_dir_mismatch())
        spawn(recover_interrupted_backup())
        if CHAT_BACKUP:
            spawn(chat_backup_loop())
        if WAKE_ON_PING:
            spawn(wake_on_ping_loop())
            log.info("Wake on join: a Minecraft join attempt starts the server")
        if AUDIT_CHANNEL_ID:
            start_audit_relay()
        self.prune_task = asyncio.create_task(log_prune_loop())
        log.info(
            "Local logs: keep %s normal, %s high-volume, prune every %ss. "
            "Discord history is not deleted.",
            LOG_KEEP,
            LOG_KEEP_HIGH,
            LOG_PRUNE_INTERVAL,
        )

        if HEALTH_ALERTS:
            self.health_task = asyncio.create_task(health_loop())
            log.info(
                "Health alerts on: RSS above the heap (or %s%% of system RAM if -Xmx is unknown), "
                "TPS<%s, stuck>=%ss (CPU is only reported) "
                "(every %ss, at most one message per %ss)%s",
                HEALTH_RAM,
                HEALTH_TPS,
                HEALTH_STUCK_AFTER,
                HEALTH_INTERVAL,
                HEALTH_COOLDOWN,
                "" if ALERT_CHANNEL_ID else " | MC_ALERT_CHANNEL_ID is unset, so warnings only reach the log",
            )

        # setup_hook runs once, unlike on_ready which fires on every reconnect.
        if ALERT_CHANNEL_ID or AUTO_RESTART or IDLE_ACTIVE or AUTO_BACKUP:
            self.monitor_task = asyncio.create_task(monitor_loop())
            log.info(
                "Monitor started (alerts=%s, auto-restart=%s, idle-shutdown=%s, auto-backup=%s)",
                bool(ALERT_CHANNEL_ID),
                AUTO_RESTART,
                IDLE_ACTIVE,
                AUTO_BACKUP,
            )

    async def close(self):
        """Close."""
        # close() can be called twice (/botstop, then discord.py's own cleanup).
        if not self._cleaned_up:
            self._cleaned_up = True
            await shutdown_cleanup()
        await super().close()


bot = MCServerBot()


def install_loop_handlers(loop):
    """Log errors nobody caught, and shut down cleanly on SIGTERM (systemd stop)."""

    def on_loop_error(_loop, context):
        """On loop error."""
        error = context.get("exception")
        message = context.get("message", "Unhandled error in the event loop")
        if error is not None:
            log.error("%s: %r", message, error, exc_info=error)
        else:
            log.error("%s", message)

    loop.set_exception_handler(on_loop_error)

    def on_sigterm():
        """On sigterm."""
        log.warning("SIGTERM received, shutting down")
        spawn(bot.close())

    try:
        loop.add_signal_handler(signal.SIGTERM, on_sigterm)
        loop.add_signal_handler(signal.SIGINT, on_sigterm)
    except (NotImplementedError, RuntimeError, ValueError):
        pass  # not supported here (Windows)


def log_startup_banner():
    """Log the version and configuration banner."""
    log.info(
        "Starting MC bot %s (python %s, discord.py %s)",
        VERSION,
        sys.version.split()[0],
        discord.__version__,
    )
    log.info(
        "Config: server log=%s | tmux session=%s | rcon=%s | idle-shutdown=%s | "
        "auto-restart=%s | admin role=%s | alert=%s | audit=%s | log=%s",
        LOG_PATH,
        MC_SESSION,
        "on" if RCON_PASSWORD else "off",
        "on" if IDLE_ACTIVE else "off",
        "on" if AUTO_RESTART else "off",
        ADMIN_ROLE_ID or "Administrator permission",
        ALERT_CHANNEL_ID or "none",
        AUDIT_CHANNEL_ID or "none",
        LOG_CHANNEL_ID or "none",
    )
    if BOT_LOG_FILE:
        log.info(
            "Writing the bot log to %s (level %s)",
            BOT_LOG_FILE,
            logging.getLevelName(FILE_LEVEL),
        )


async def shutdown_cleanup():
    """Leave nothing half-finished and push the last log lines out."""

    log.info("Bot shutting down")

    for task in (bot.monitor_task, bot.health_task, bot.prune_task, relay.tail_task):
        if task is not None:
            task.cancel()

    if log_sessions:
        for session in list(log_sessions.values()):
            session.stop.set()
        await asyncio.sleep(1)

    if console_sessions:
        for session in list(console_sessions):
            session.end_reason = "The bot is shutting down."
            session.close()
        await asyncio.sleep(1)  # let the consoles show that they ended

    if idle.since is not None or idle.status is not None:
        try:
            await cancel_idle_shutdown("The bot is shutting down.")
        except Exception as error:
            log.warning("Couldn't clear the idle warning: %r", error)

    log.info("Bot stopped. The Minecraft server was left as it was.")
    await relay.shutdown()
    await audit.shutdown()
    await rcon.close()


def log_startup_notes():
    """Log non-fatal configuration warnings."""
    if LOG_CHANNEL_ID and not (LOG_BOT or LOG_MINECRAFT):
        log.warning(
            "MC_LOG_CHANNEL_ID is set but MC_LOG_BOT and MC_LOG_MINECRAFT are "
            "both off, so nothing is relayed."
        )
    if LOG_CHANNEL_ID and LOG_MINECRAFT:
        log.warning(
            "Minecraft log relay is on for channel %s. latest.log can contain "
            "player IPs when log-ips=true. That channel should be admin-only.",
            LOG_CHANNEL_ID,
        )
    if AUDIT_CHANNEL_ID:
        log.info("Command audit goes to channel %s (not the log channel).", AUDIT_CHANNEL_ID)
    elif LOG_CHANNEL_ID:
        log.info("MC_AUDIT_CHANNEL_ID is unset, so command audit stays in the log channel.")
    if not RCON_PASSWORD:
        log.warning(
            "RCON password not configured. RCON features, idle shutdown and "
            "RCON-based readiness checks are unavailable."
        )
    elif IDLE_SHUTDOWN and not IDLE_CHANNEL_ID:
        log.warning(
            "Idle shutdown is OFF: it needs a channel for the countdown message. "
            "Set MC_ALERT_CHANNEL_ID (or MC_IDLE_CHANNEL_ID) to a real channel ID."
        )

    if not GUILD_ID:
        log.warning(
            "DISCORD_GUILD_ID is 0, so slash commands sync to every server this "
            "bot is in. Set it to your server's ID. DMs are refused either way."
        )
    if ADMIN_ROLE_ID:
        log.info(
            "/backup list, /backup restore, console, serveredit and botstop need "
            "role %s. Every other command is open to this server.",
            ADMIN_ROLE_ID,
        )
    else:
        log.warning(
            "MC_ADMIN_ROLE_ID is unset, so /backup list, /backup restore, console, "
            "serveredit and botstop need the Administrator permission. Set it to "
            "your admin role's ID."
        )


# ============================================================
# PERMISSIONS, OPERATION LOCK, RESPONSES
# ============================================================

def guild_problem(interaction):
    """Why this interaction is in the wrong place, or None if it may run."""

    if getattr(interaction, "guild_id", None) is None:
        return "This bot only works in a server, not in DMs."
    if GUILD_ID and interaction.guild_id != GUILD_ID:
        return "This bot is locked to a different server."
    return None


async def gate(interaction, *, admin=False):
    """Refuse a DM, the wrong server, or a non-admin. True if the command may run.

    Sends the refusal when this is a real command. Autocomplete gets no message.
    """

    problem = guild_problem(interaction)
    if problem is None and admin and not member_is_admin(interaction):
        problem = ADMIN_DENIED
    if problem is None:
        return True
    if getattr(interaction, "type", None) is discord.InteractionType.autocomplete:
        return False
    if not interaction.response.is_done():
        try:
            await deny(interaction, problem)
        except EDIT_ERRORS:
            pass
    return False


ADMIN_DENIED = (
    "[!] Only the admin role can use that command."
    if ADMIN_ROLE_ID
    else "[!] Only members with the Administrator permission can use that command."
)


def member_is_admin(interaction) -> bool:
    """The admin role (Administrator if no role is set). Needed for /backup list|restore,
    console, serveredit and botstop. Everything else is open to the whole server."""

    if interaction.guild is None:
        return False
    if ADMIN_ROLE_ID:
        return any(
            role.id == ADMIN_ROLE_ID
            for role in getattr(interaction.user, "roles", ())
        )
    return bool(interaction.permissions.administrator)


def try_lock(name):
    """Try to acquire the single-instance lock."""
    global current_op

    if current_op is not None:
        return False
    current_op = name
    invalidate_confirms(f"`/{name}` started.")
    return True


open_confirms = set()


def invalidate_confirms(reason):
    """Close stop/restart buttons once another operation has started."""

    for view in list(open_confirms):
        spawn(view.invalidate(reason))


def release():
    """Release the single-instance lock."""
    global current_op
    current_op = None


def _log_mark():
    """(inode, size) of latest.log, so a stop can be checked against later bytes only."""

    try:
        info = os.stat(LOG_PATH)
        return info.st_ino, info.st_size
    except OSError:
        return None, 0


def process_start_ticks(pid):
    """Kernel start time of a process, so a recycled PID is not the same JVM."""

    try:
        with open(f"/proc/{pid}/stat", "rb") as file:
            rest = file.read().rsplit(b")", 1)[1].split()
        return int(rest[19])
    except (OSError, IndexError, ValueError):
        return None


def note_controlled_stop(pid):
    """Remember the process this bot is about to stop, and where the log was."""

    global expected_stop, recent_stop
    inode, offset = _log_mark()
    expected_stop = SimpleNamespace(
        pid=pid,
        at=time.monotonic(),
        ino=inode,
        offset=offset,
        saw_shutdown=False,
        started=process_start_ticks(pid),
    )
    # Survives a timed-out /stop clearing expected_stop, so a slow clean exit
    # is not later reported as a stop this bot did not issue.
    recent_stop = expected_stop


def clear_controlled_stop():
    """Forget the current controlled-stop expectation."""
    global expected_stop
    expected_stop = None


def clear_recent_stop():
    """Forget the recent-stop record."""
    global recent_stop
    recent_stop = None


def recent_stop_by_us():
    """True for about 2x MC_STOP_TIMEOUT after this bot sent stop."""

    if recent_stop is None:
        return False
    return time.monotonic() - recent_stop.at <= STOP_TIMEOUT * 2


def _stop_log_replaced(stop):
    """True if latest.log was rotated or truncated after the stop was requested."""

    if stop is None or stop.ino is None:
        return False
    try:
        info = os.stat(LOG_PATH)
    except OSError:
        return True
    return info.st_ino != stop.ino or info.st_size < stop.offset


def shutdown_after_stop(stop=None):
    """True if `Stopping server` was written after this stop was requested.

    Only bytes appended to the same file count. A line from an earlier boot,
    or from before the stop command, cannot excuse this exit. Once seen, the
    result is kept, so a later truncate cannot erase it.
    """

    stop = expected_stop if stop is None else stop
    if stop is None:
        return False
    if stop.saw_shutdown:
        return True
    if _stop_log_replaced(stop):
        return False
    try:
        with open(LOG_PATH, "rb") as file:
            file.seek(stop.offset)
            data = file.read()
    except OSError:
        return False
    if STOPPING_RE.search(data):
        stop.saw_shutdown = True
        return True
    return False


def release_stop_expectation_unless_shutting_down():
    """A timed-out stop must not hide a later crash of the same PID.

    Keep the expectation only when `Stopping server` was appended after the
    stop command. If that line never appeared, a later exit of this PID is a
    crash. The expectation still expires after EXPECTED_STOP_MAX.
    """

    if expected_stop is None:
        return
    if time.monotonic() - expected_stop.at > EXPECTED_STOP_MAX:
        log.warning(
            "Stop for PID %s exceeded %ss. A later exit will be a crash.",
            expected_stop.pid,
            EXPECTED_STOP_MAX,
        )
        clear_controlled_stop()
        return
    if shutdown_after_stop():
        log.info(
            "Stop timed out, but Stopping server was logged after the command. "
            "PID %s is still an expected stop until %ss.",
            expected_stop.pid,
            EXPECTED_STOP_MAX,
        )
        return
    if _stop_log_replaced(expected_stop):
        log.warning(
            "Stop timed out and latest.log rotated before Stopping server. "
            "PID %s is still an expected stop, so a deliberate stop is not restarted.",
            expected_stop.pid,
        )
        return
    log.warning(
        "Stop timed out and Stopping server was not logged after the command. "
        "A later exit of PID %s will be treated as a crash.",
        expected_stop.pid,
    )
    clear_controlled_stop()


def one_line(text, width=200):
    """Collapse a message to a single log line."""

    text = re.sub(r"\s+", " ", str(text)).replace("**", "").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def clip_discord(text, limit=DISCORD_LIMIT):
    """Clip text to Discord's message length limit."""
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2300-\u23FF"
    "\uFE0F"
    "\u200D"
    "]+"
)


def calm(text):
    """Drop decorative emoji from Discord text. In-game lines are unchanged."""

    if text is None:
        return text
    text = _EMOJI_RE.sub("", str(text))
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


async def deny(interaction, text):
    """First response, private. Only valid before the interaction is deferred."""

    text = calm(text)
    if text == ADMIN_DENIED:
        cmd_log.warning(
            "Permission denied: %s by %s",
            command_label(interaction),
            describe_user(interaction.user),
        )
    else:
        cmd_log.info(
            "%s by %s answered: %s",
            command_label(interaction),
            describe_user(interaction.user),
            text,
        )
    await interaction.response.send_message(text, ephemeral=False)


async def begin(interaction, op=None, *, ephemeral=False):
    """Permission check, busy check, then defer: nothing here awaits earlier.

    Refusals are sent as the *first* response so ephemeral is honoured; after
    a public defer, Discord would show them to the whole channel.
    Returns True to proceed. When op is given the caller must release().
    """

    if not await gate(interaction):
        return False

    if op is not None and not try_lock(op):
        await deny(interaction, f"Busy: `/{current_op}` is still in progress.")
        return False

    try:
        await interaction.response.defer(ephemeral=ephemeral)
    except BaseException:
        if op is not None:
            release()
        raise
    return True


def managed(op):
    """Wrap a no-argument admin command: begin(), run, release()."""

    def decorate(fn):
        """Decorate."""
        @functools.wraps(fn)
        async def wrapper(interaction):
            """Wrapper."""
            if not await begin(interaction, op):
                return
            try:
                await fn(interaction)
            finally:
                release()

        return wrapper

    return decorate


async def followup_text(interaction, text, ephemeral=False):
    """Send a follow-up text message to an interaction."""
    return await interaction.followup.send(
        clip_discord(calm(text)), ephemeral=ephemeral
    )


async def followup_embed(interaction, embed, ephemeral=False):
    """Send a follow-up embed to an interaction."""
    return await interaction.followup.send(embed=embed, ephemeral=ephemeral)


EDIT_ERRORS = (discord.HTTPException, aiohttp.ClientError, asyncio.TimeoutError)


class Status:
    """A Discord message that is edited as an operation progresses.

    Edits are cosmetic, so a failed one never aborts a server operation, and
    progress edits are rate-limited to keep Discord traffic low. A followup
    dies with the interaction token at 15 minutes, so a long run is moved
    onto a normal channel message first.
    """

    def __init__(self, message, interaction=None, min_gap=None):
        """Internal: init."""
        self.message = message
        self.interaction = interaction
        self.min_gap = EDIT_INTERVAL if min_gap is None else min_gap
        self.last = time.monotonic()  # creating the message counted as an edit
        self.born = self.last
        self.anchored = interaction is None  # alert messages already use the bot token

    @property
    def alive(self):
        """Alive."""
        return self.message is not None

    async def reanchor(self, text):
        """Post a channel message and edit that from here on. Bot token, no 15-minute cap."""

        if self.anchored:  # why: anchored is set from interaction is None, so the second check was dead
            return True
        channel = self.interaction.channel
        if channel is None:
            channel = bot.get_partial_messageable(self.interaction.channel_id)
        try:
            posted = await channel.send(clip_discord(calm(text)))
        except EDIT_ERRORS as error:
            log.warning("Couldn't move the status message off the interaction: %s", error)
            return False
        self.message = posted
        self.anchored = True
        self.last = time.monotonic()
        log.info("Status moved to a channel message before the interaction token expired")
        return True

    async def set(self, text, force=False):
        """Set."""
        if self.message is None and not self.anchored:
            await self.reanchor(text)
        if (
            not self.anchored
            and time.monotonic() - self.born >= TOKEN_REANCHOR_AFTER
        ):
            await self.reanchor(text)
        if self.message is None:
            return False

        if force:
            log.info("Status: %s", one_line(text))

        now = time.monotonic()
        if not force and now - self.last < self.min_gap:
            return True

        try:
            await self.message.edit(content=clip_discord(calm(text)))
        except discord.NotFound:
            if not self.anchored and await self.reanchor(text):
                return True
            self.message = None  # deleted; stop trying
            return False
        except EDIT_ERRORS as error:
            if not self.anchored and await self.reanchor(text):
                return True
            log.debug("Message edit failed: %r", error)
            return False

        self.last = now
        return True


async def open_status(interaction, text):
    """First message of a deferred command, as an editable Status."""

    return Status(
        await interaction.followup.send(clip_discord(calm(text)), wait=True),
        interaction,
    )


# ============================================================
# DISCORD LOG RELAY ([mc-bot] and [Minecraft] lines in one channel)
# ============================================================

# Never sent to Discord: a failure to post would otherwise post about itself.
relay_log = log.getChild("relay")

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
FORMAT_CODE_RE = re.compile("§.")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
RELAY_LINE_MAX = 400
RELAY_MESSAGE_MAX = 1900


def relay_clean(text):
    """Sanitize a log line before relaying it."""
    text = ANSI_RE.sub("", text)
    text = FORMAT_CODE_RE.sub("", text)
    text = text.replace("\t", " ")
    text = CONTROL_RE.sub("", text)
    return text.replace("```", "'" * 3)


_IPV4_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
)
_IPV6_RE = re.compile(
    r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
    r"|\b(?:[0-9a-fA-F]{1,4}:){1,7}:"
    r"|\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b"
)


def redact_ips(text):
    """Hide player addresses in text that may be posted outside an admin channel."""

    if not text:
        return text
    text = _IPV4_RE.sub("[ip]", str(text))
    return _IPV6_RE.sub("[ip]", text)


class MinecraftLogTail:
    """Follows latest.log like `tail -F`.

    One handle stays open, so when the server renames the old log on boot the
    last lines of the old session are still read before the new file is
    opened. A new file or a shorter file means a new session. At start only
    new lines are followed, the old history is not replayed.
    """

    MAX_PER_POLL = 512 * 1024

    def __init__(self, path):
        """Internal: init."""
        self.path = path
        self.file = None
        self.ino = None
        self.carry = b""
        self.primed = False
        self.warned = False

    def close(self):
        """Close."""
        if self.file is not None:
            try:
                self.file.close()
            except OSError:
                pass
        self.file = None

    def _open(self, from_start):
        """Internal: open."""
        try:
            handle = open(self.path, "rb")
        except OSError:
            return False
        self.close()
        self.file = handle
        self.ino = os.fstat(handle.fileno()).st_ino
        self.carry = b""
        if not from_start:
            handle.seek(0, os.SEEK_END)
        return True

    def _flush_carry(self, events):
        """Internal: flush carry."""
        if self.carry:
            events.append(("line", self.carry.decode("utf-8", "replace").rstrip("\r")))
            self.carry = b""

    def _drain(self, events):
        """Internal: drain."""
        read = 0
        while read < self.MAX_PER_POLL:
            data = self.file.read(_CHUNK)
            if not data:
                break
            read += len(data)
            parts = (self.carry + data).split(b"\n")
            self.carry = parts.pop()
            for part in parts:
                events.append(("line", part.decode("utf-8", "replace").rstrip("\r")))
        if len(self.carry) > 65536:  # a "line" that never ends
            self._flush_carry(events)

    def poll(self):
        """Return [("line", text) | ("session", None)] since the last call."""

        events = []
        try:
            if not self.primed:
                self.primed = True
                if self._open(from_start=False):
                    relay_log.info("Following the Minecraft log %s", self.path)
                else:
                    relay_log.warning(
                        "Minecraft log %s doesn't exist yet. It will be followed "
                        "once the server creates it. Check MC_LOG_PATH if it "
                        "never shows up.",
                        self.path,
                    )
                return events

            if self.file is not None:
                self._drain(events)

            try:
                stat = os.stat(self.path)
            except OSError:
                return events  # between rotation and the new file

            if self.file is None:
                if self._open(from_start=True):
                    events.append(("session", None))
                    self._drain(events)
            elif stat.st_ino != self.ino:
                self._drain(events)  # whatever the old file got meanwhile
                self._flush_carry(events)
                if self._open(from_start=True):
                    events.append(("session", None))
                    self._drain(events)
            elif stat.st_size < self.file.tell():
                self._flush_carry(events)
                self.file.seek(0)
                events.append(("session", None))
                self._drain(events)
            self.warned = False
        except OSError as error:
            if not self.warned:
                self.warned = True
                relay_log.warning("Can't read the Minecraft log %s: %s", self.path, error)
        return events


class DiscordLogHandler(logging.Handler):
    """Hands the bot's own log lines to the relay as [mc-bot] lines."""

    def __init__(self, relay):
        """Internal: init."""
        super().__init__(level=LOG_DISCORD_LEVEL)
        self.relay = relay
        self.addFilter(
            lambda record: not record.name.startswith("mcbot.relay")
            and not (AUDIT_CHANNEL_ID and record.name.startswith("mcbot.cmd"))
        )

    def emit(self, record):
        """Emit."""
        try:
            text = (
                f"{time.strftime('%H:%M:%S', time.localtime(record.created))} "
                f"{record.levelname:<7} {record.getMessage()}"
            )
            if record.exc_info and record.exc_info[1] is not None:
                text += " | " + "".join(
                    traceback.format_exception_only(*record.exc_info[:2])
                ).strip()
            self.relay.add_threadsafe("mc-bot", text)
        except Exception:
            self.handleError(record)


class LogRelay:
    """Batches log lines and posts them to MC_LOG_CHANNEL_ID.

    Lines wait in a bounded queue (oldest dropped first, and counted), so a
    slow Discord can never grow memory or block the bot. Everything is sent
    in the order it arrived, so [mc-bot] and [Minecraft] lines interleave
    correctly and the separators land between the right sessions.
    """

    def __init__(self):
        """Internal: init."""
        self.queue = collections.deque()
        self.dropped = 0
        self.wake = None
        self.loop = None
        self.channel = None
        self.handler = None
        self.tail = None
        self.tail_task = None
        self.flush_task = None
        self.started = False
        self.closed = False
        # True while the last server session already has its "stopped" line.
        self.stop_marked = True
        self._last_error = -300.0

    # ---- feeding the queue

    def _push(self, line):
        """Internal: push."""
        if len(self.queue) >= LOG_QUEUE_MAX:
            self.queue.popleft()
            self.dropped += 1
        self.queue.append(line)
        if self.wake is not None:
            self.wake.set()

    def add(self, prefix, text):
        """Add."""
        if self.closed:
            return
        for raw in str(text).splitlines():
            line = relay_clean(raw)
            if not line.strip():
                continue
            if len(line) > RELAY_LINE_MAX:
                line = line[: RELAY_LINE_MAX - 1] + "…"
            self._push(f"[{prefix}]: {line}")

    def add_threadsafe(self, prefix, text):
        """Add threadsafe."""
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            self.add(prefix, text)
            return
        try:
            loop.call_soon_threadsafe(self.add, prefix, text)
        except RuntimeError:
            pass  # loop closed while shutting down

    def separator(self, label):
        """Separator."""
        if self.closed or not self.started:
            return
        self._push(f"-------- {label} ({time.strftime('%Y-%m-%d %H:%M:%S')}) --------")

    # ---- server session markers

    def poll_tail(self):
        """Poll tail."""
        if self.tail is None:
            return
        for kind, text in self.tail.poll():
            if kind == "session":
                if not self.stop_marked:
                    self.separator("server stopped")  # the old session never got one
                self.separator("server started")
                self.stop_marked = False
            else:
                self.stop_marked = False
                self.add("Minecraft", text)

    def server_up(self, first):
        """The monitor saw the server process come up."""

        self.stop_marked = False
        if not first and self.tail is None:
            self.separator("server started")

    def server_stopped(self):
        """The server process is gone. Safe to call more than once."""

        if not self.started or self.closed:
            return
        self.poll_tail()  # the last lines of the old session go out first
        if self.stop_marked:
            return
        self.separator("server stopped")
        self.stop_marked = True

    # ---- lifecycle

    def start(self):
        """Slash command: start the Minecraft server."""
        self.loop = asyncio.get_running_loop()
        self.wake = asyncio.Event()
        self.started = True
        self.separator("mc-bot started")

        if LOG_BOT:
            self.handler = DiscordLogHandler(self)
            log.addHandler(self.handler)

        if LOG_MINECRAFT:
            self.tail = MinecraftLogTail(LOG_PATH)
            self.tail.poll()  # remember where the log ends right now
            self.tail_task = spawn(self._tail_loop())

        self.flush_task = spawn(self._flush_loop())
        relay_log.info(
            "Log relay on: channel %s, bot lines=%s (from %s), Minecraft lines=%s",
            LOG_CHANNEL_ID,
            LOG_BOT,
            logging.getLevelName(LOG_DISCORD_LEVEL),
            LOG_MINECRAFT,
        )

    async def _tail_loop(self):
        """Internal: tail loop."""
        while True:
            try:
                self.poll_tail()
            except Exception:
                relay_log.exception("Minecraft log tail failed")
            await asyncio.sleep(LOG_TAIL_INTERVAL)

    async def _flush_loop(self):
        """Internal: flush loop."""
        await bot.wait_until_ready()
        while True:
            if not self.queue:
                self.wake.clear()
                await self.wake.wait()
            await asyncio.sleep(LOG_FLUSH_INTERVAL)  # let a burst collect
            try:
                await self.flush()
            except asyncio.CancelledError:
                raise
            except Exception:
                relay_log.exception("Log flush failed")
                await asyncio.sleep(5)

    async def _get_channel(self):
        """Internal: get channel."""
        if self.channel is None:
            channel = bot.get_channel(LOG_CHANNEL_ID)
            if channel is None:
                channel = await bot.fetch_channel(LOG_CHANNEL_ID)
            self.channel = channel
        return self.channel

    def _report_failure(self, message, *args):
        """Internal: report failure."""
        now = time.monotonic()
        if now - self._last_error >= 300:
            self._last_error = now
            relay_log.error(message, *args)

    async def _send(self, text, count):
        """Internal: send."""
        for attempt in (1, 2, 3):
            try:
                channel = await self._get_channel()
                await channel.send(text)
                return True
            except (discord.Forbidden, discord.NotFound) as error:
                self.channel = None
                self.dropped += count
                self._report_failure(
                    "Can't post to log channel %s (%s). Check MC_LOG_CHANNEL_ID "
                    "and that the bot can view and send messages there.",
                    LOG_CHANNEL_ID,
                    error,
                )
                await asyncio.sleep(30)
                return False
            except EDIT_ERRORS as error:
                relay_log.warning(
                    "Couldn't post a log batch (attempt %s/3): %r", attempt, error
                )
                await asyncio.sleep(2 * attempt)
        self.dropped += count
        return False

    async def flush(self):
        """Flush."""
        if self.dropped:
            skipped, self.dropped = self.dropped, 0
            self.add("mc-bot", f"{skipped} log lines were skipped (Discord was slow or unreachable)")

        while self.queue:
            batch, size = [], 0
            while self.queue:
                need = len(self.queue[0]) + 1
                if batch and size + need > RELAY_MESSAGE_MAX:
                    break
                batch.append(self.queue.popleft())
                size += need
            if not await self._send("```\n" + "\n".join(batch) + "\n```", len(batch)):
                return

    async def shutdown(self):
        """Shutdown."""
        if not self.started or self.closed:
            return

        self.poll_tail()  # the last lines before the bot went away
        self.separator("mc-bot stopped")
        if self.handler is not None:
            log.removeHandler(self.handler)
            self.handler = None
        self.closed = True

        for task in (self.tail_task, self.flush_task):
            if task is not None:
                task.cancel()
        if self.flush_task is not None:
            try:
                await self.flush_task
            except BaseException:
                pass  # cancelled, as intended

        try:
            await asyncio.wait_for(self.flush(), 10)
        except Exception as error:
            relay_log.warning("Final log flush failed: %r", error)
        if self.tail is not None:
            self.tail.close()


relay = LogRelay()


def start_log_relay():
    """Start the Minecraft log relay."""
    relay.start()


class AuditRelay:
    """Command audit lines for MC_AUDIT_CHANNEL_ID, separate from the log channel."""

    def __init__(self):
        """Internal: init."""
        self.queue = collections.deque()
        self.wake = None
        self.loop = None
        self.channel = None
        self.handler = None
        self.flush_task = None
        self.started = False
        self.closed = False
        self.dropped = 0

    def add(self, text):
        """Add."""
        if self.closed:
            return
        line = relay_clean(str(text)).strip()
        if not line:
            return
        if len(line) > RELAY_LINE_MAX:
            line = line[: RELAY_LINE_MAX - 1] + "…"
        if len(self.queue) >= LOG_QUEUE_MAX:
            self.queue.popleft()
            self.dropped += 1
        self.queue.append(line)
        if self.wake is not None:
            self.wake.set()

    def add_threadsafe(self, text):
        """Add threadsafe."""
        loop = self.loop
        if loop is None or loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            self.add(text)
            return
        try:
            loop.call_soon_threadsafe(self.add, text)
        except RuntimeError:
            pass

    def start(self):
        """Slash command: start the Minecraft server."""
        self.loop = asyncio.get_running_loop()
        self.wake = asyncio.Event()
        self.started = True
        self.handler = logging.Handler(level=env_level("MC_AUDIT_LEVEL", "INFO"))
        self.handler.emit = lambda record: self.add_threadsafe(record.getMessage())
        cmd_log.addHandler(self.handler)
        self.flush_task = spawn(self._flush_loop())
        log.info("Audit relay on: channel %s", AUDIT_CHANNEL_ID)

    async def _flush_loop(self):
        """Internal: flush loop."""
        await bot.wait_until_ready()
        while True:
            if not self.queue:
                self.wake.clear()
                await self.wake.wait()
            await asyncio.sleep(LOG_FLUSH_INTERVAL)
            try:
                await self.flush()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Audit flush failed")
                await asyncio.sleep(5)

    async def flush(self):
        """Flush."""
        while self.queue:
            batch, size = [], 0
            while self.queue:
                need = len(self.queue[0]) + 1
                if batch and size + need > RELAY_MESSAGE_MAX:
                    break
                batch.append(self.queue.popleft())
                size += need
            skipped = 0
            if self.dropped:
                skipped, self.dropped = self.dropped, 0
            payload = list(batch)
            if skipped:
                payload.insert(0, f"... {skipped} audit line(s) skipped (queue full)")
            try:
                if self.channel is None:
                    self.channel = bot.get_channel(AUDIT_CHANNEL_ID)
                    if self.channel is None:
                        self.channel = await bot.fetch_channel(AUDIT_CHANNEL_ID)
                await self.channel.send("```\n" + "\n".join(payload) + "\n```")
            except asyncio.CancelledError:
                self._requeue_audit(batch, skipped)
                raise
            except Exception as error:
                self.channel = None
                self._requeue_audit(batch, skipped)
                warn_throttled(
                    "audit-post",
                    "Couldn't post to audit channel %s: %s",
                    AUDIT_CHANNEL_ID,
                    error,
                )
                return

    def _requeue_audit(self, batch, skipped):
        """Internal: requeue audit."""
        if skipped:
            self.dropped += skipped
        for line in reversed(batch):
            self.queue.appendleft(line)

    async def shutdown(self):
        """Shutdown."""
        if not self.started or self.closed:
            return
        self.closed = True
        if self.handler is not None:
            cmd_log.removeHandler(self.handler)
        if self.flush_task is not None:
            self.flush_task.cancel()
        try:
            await asyncio.wait_for(self.flush(), 5)
        except Exception:
            pass


audit = AuditRelay()


def start_audit_relay():
    """Start the command-audit relay."""
    audit.start()


# ============================================================
# RCON
# ============================================================

COLOR_RE = re.compile(r"§.")

# Source RCON packet types.
RCON_RESPONSE = 0
RCON_COMMAND = 2
RCON_AUTH = 3
RCON_AUTH_RESPONSE = 2
RCON_MAX_PACKETS = 64
RCON_FRAGMENT_SIZE = 4096   # Minecraft splits long replies into chunks of this many characters
RCON_FRAGMENT_WAIT = 0.5    # how long to wait for another chunk after a full-size one


def strip_colors(text):
    """Remove Minecraft color and formatting codes from text."""
    return COLOR_RE.sub("", text)


class RconError(Exception):
    """Raised when an RCON exchange fails."""
    pass


RCON_ERRORS = (
    RconError,
    OSError,  # includes ConnectionError
    asyncio.IncompleteReadError,
    asyncio.TimeoutError,
)


RCON_LOGIN_REJECTED = (
    "RCON login rejected: MC_RCON_PASSWORD doesn't match rcon.password "
    "in server.properties"
)


def describe_rcon_error(error):
    """A readable reason for an RCON failure (repr() of a timeout is empty)."""

    if isinstance(error, ConnectionRefusedError):
        return (
            f"connection refused at {RCON_HOST}:{RCON_PORT} (RCON is off, the "
            "port is wrong, or the server isn't up yet)"
        )
    if isinstance(error, asyncio.TimeoutError):
        return f"no answer from {RCON_HOST}:{RCON_PORT} (timed out)"
    if isinstance(
        error, (asyncio.IncompleteReadError, ConnectionResetError, BrokenPipeError)
    ):
        return (
            "the server closed the connection (wrong password, or "
            f"{RCON_HOST}:{RCON_PORT} isn't the RCON port)"
        )
    if isinstance(error, RconError):
        return str(error)
    return repr(error)


def _rcon_packet(pkt_id, ptype, body):
    """Build an RCON packet."""
    payload = (
        pkt_id.to_bytes(4, "little", signed=True)
        + ptype.to_bytes(4, "little", signed=True)
        + body.encode("utf-8")
        + b"\x00\x00"
    )
    return len(payload).to_bytes(4, "little", signed=True) + payload


async def _rcon_read(reader):
    """Read one RCON packet from a stream."""
    length = int.from_bytes(await reader.readexactly(4), "little", signed=True)
    if length < 10 or length > 65535:
        raise RconError(f"bad packet length {length}")

    data = await reader.readexactly(length)
    pkt_id = int.from_bytes(data[0:4], "little", signed=True)
    ptype = int.from_bytes(data[4:8], "little", signed=True)
    return pkt_id, ptype, data[8:-2].decode("utf-8", errors="replace")


class Rcon:
    """One persistent, serialised RCON connection.

    Minecraft logs a line when each RCON client connects and again when it
    disconnects, so connecting for every poll (the monitor polls every 15s)
    flooded latest.log and re-did the TCP + auth handshake each time. The
    connection is opened on demand, reused, and reopened if the server
    restarted or dropped it.

    Exactly one packet is sent per write, and the next one only after the
    reply arrived: vanilla Minecraft reads one packet per socket read and
    closes the connection if two arrive together. A reply shorter than
    RCON_FRAGMENT_SIZE is complete; a full-size chunk means more may follow.
    """

    def __init__(self):
        """Internal: init."""
        self._reader = None
        self._writer = None
        self._lock = None

    def _drop(self):
        """Internal: drop."""
        writer, self._reader, self._writer = self._writer, None, None
        if writer is not None:
            try:
                writer.close()
            except Exception:
                pass

    async def close(self):
        """Close."""
        writer = self._writer
        self._drop()
        if writer is not None:
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _connect(self, timeout):
        """Internal: connect."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(RCON_HOST, RCON_PORT), timeout
        )
        try:
            writer.write(_rcon_packet(1, RCON_AUTH, RCON_PASSWORD))
            await writer.drain()
            # The auth reply can be preceded by an empty packet.
            for _ in range(RCON_MAX_PACKETS):
                pkt_id, ptype, _body = await asyncio.wait_for(
                    _rcon_read(reader), timeout
                )
                if pkt_id == -1:
                    raise RconError(RCON_LOGIN_REJECTED)
                if ptype == RCON_AUTH_RESPONSE and pkt_id == 1:
                    break
            else:
                raise RconError("RCON login failed (no valid reply from the server)")
        except BaseException:
            writer.close()
            raise
        self._reader, self._writer = reader, writer
        log.info("RCON connected to %s:%s", RCON_HOST, RCON_PORT)

    async def _exchange(self, command, timeout, trace):
        """Internal: exchange."""
        self._writer.write(_rcon_packet(2, RCON_COMMAND, command))
        await self._writer.drain()
        trace.sent = True

        for _ in range(RCON_MAX_PACKETS):
            # The first packet may take a while (the command runs on the server
            # thread); later chunks follow immediately, so don't wait long.
            wait = timeout if trace.packets == 0 else RCON_FRAGMENT_WAIT
            try:
                pkt_id, _ptype, body = await asyncio.wait_for(
                    _rcon_read(self._reader), wait
                )
            except asyncio.TimeoutError:
                if trace.packets == 0:
                    raise
                return "".join(trace.parts)  # no further chunk came

            trace.packets += 1
            if pkt_id != 2:
                continue  # not a reply to our command
            trace.parts.append(body)
            if len(body) < RCON_FRAGMENT_SIZE:
                return "".join(trace.parts)  # short chunk = last chunk
        raise RconError("RCON reply too long")

    async def _run(self, command, timeout, expect_close):
        """Internal: run."""
        for attempt in (0, 1):
            reused = self._writer is not None
            if not reused:
                await self._connect(timeout)

            trace = SimpleNamespace(sent=False, packets=0, parts=[])
            try:
                return await self._exchange(command, timeout, trace)
            except RCON_ERRORS as error:
                # The stream may be mid-reply, so it is never reused.
                log.debug("RCON command %r failed: %r", command, error)
                self._drop()
                if expect_close and trace.sent:
                    return "".join(trace.parts)
                if trace.parts:
                    log.warning(
                        "RCON reply for %r ended before the last chunk: %s",
                        command,
                        describe_rcon_error(error),
                    )
                    return "".join(trace.parts)
                # A connection left over from before a server restart fails
                # before any reply. Retry once on a fresh connection.
                # Do not open a second connection if this one already carried the
                # command. A dropped reply is not proof it failed to run.
                stale = (
                    reused
                    and attempt == 0
                    and not trace.sent
                    and trace.packets == 0
                    and isinstance(
                        error, (ConnectionError, asyncio.IncompleteReadError)
                    )
                )
                if not stale:
                    error.sent = trace.sent
                    raise
        raise RconError("RCON retry failed")  # pragma: no cover

    async def command(self, command, expect_close=False, timeout=5.0):
        """Command."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        try:
            await asyncio.wait_for(self._lock.acquire(), timeout)
        except asyncio.TimeoutError:
            raise RconError("RCON busy") from None

        try:
            return await self._run(command, timeout, expect_close)
        finally:
            if expect_close:
                self._drop()  # the server is going away
            self._lock.release()


rcon = Rcon()


async def rcon_ready():
    """True if the server answers a console command over RCON right now."""

    if not RCON_PASSWORD:
        return False
    try:
        await rcon.command("list", timeout=3)
    except RCON_ERRORS:
        return False
    return True


async def rcon_diagnose(timeout=5.0):
    """One fresh login on a throwaway connection. Returns (ok, explanation)."""

    if not RCON_PASSWORD:
        return False, "MC_RCON_PASSWORD is empty in .env, so RCON is switched off."

    probe = Rcon()
    try:
        output = await probe.command("list", timeout=timeout)
    except RCON_ERRORS as error:
        return False, describe_rcon_error(error)
    finally:
        await probe.close()
    return True, strip_colors(output).strip() or "(empty reply)"


async def startup_rcon_check():
    """Warn once if RCON is missing. The bot keeps running on tmux either way."""

    await bot.wait_until_ready()
    if not RCON_PASSWORD:
        log.warning(
            "RCON password not configured. The bot keeps running; player count, "
            "idle shutdown and TPS stay unavailable."
        )
        await send_alert(
            embed=panel(
                "RCON is not set up",
                [
                    "The bot is running without RCON.",
                    "Start, stop, save and the tmux console still work.",
                    "Player count, idle shutdown and TPS checks do not.",
                    "Set enable-rcon=true in server.properties and MC_RCON_PASSWORD in .env, then restart the Minecraft server.",
                ],
                COLOR_WAIT,
            )
        )
        return
    try:
        if not await server_running():
            log.info("RCON check skipped: the Minecraft server is offline.")
            return
        ok, detail = await rcon_diagnose()
    except Exception as error:
        log.warning("RCON check couldn't run: %r", error)
        await send_alert(
            embed=panel(
                "RCON check failed",
                [
                    "The bot is still running and will use tmux for console commands.",
                    f"Check error: {error}",
                    "Player count, idle shutdown and TPS stay unavailable until RCON answers.",
                ],
                COLOR_BAD,
            )
        )
        return

    if ok:
        log.info("RCON check passed (%s:%s): %s", RCON_HOST, RCON_PORT, detail)
        return
    log.warning(
        "RCON check FAILED (%s:%s): %s. The bot falls back to tmux for "
        "commands, and players/idle-shutdown stay unavailable. Run /rcontest "
        "for details.",
        RCON_HOST,
        RCON_PORT,
        detail,
    )
    await send_alert(
        embed=panel(
            "RCON is not answering",
            [
                "The bot is still running. Console commands fall back to tmux.",
                f"{RCON_HOST}:{RCON_PORT} — {detail}",
                "Player count, idle shutdown and TPS stay unavailable.",
                "Run /rcontest after enable-rcon=true and a server restart.",
            ],
            COLOR_BAD,
        )
    )


# ============================================================
# CONSOLE (RCON first, tmux as fallback)
# ============================================================

async def tmux_send(command: str):
    """Send a literal line to the Minecraft tmux session."""
    # -l sends the text literally, so a command can never be read as a key
    # name, and -- stops a leading dash from being read as an option.
    try:
        for args in (("-l", "--", command), ("Enter",)):
            proc = await asyncio.create_subprocess_exec(
                "tmux",
                "send-keys",
                "-t",
                MC_SESSION,
                *args,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            if await proc.wait() != 0:
                return False
    except OSError:
        return False
    return True


async def send_console(command, expect_close=False, timeout=5.0):
    """Run a console command, preferring RCON and falling back to tmux."""
    if RCON_PASSWORD:
        try:
            output = await rcon.command(
                command, expect_close=expect_close, timeout=timeout
            )
            return True, output
        except RCON_ERRORS as error:
            # The packet may already have run. Sending it again through tmux
            # would double say, kick, op, give, and similar commands.
            if getattr(error, "sent", False) and not command_is_idempotent(command):
                log.warning(
                    "RCON sent %r but the reply dropped. Not sending it again through tmux.",
                    command,
                )
                return False, None
            log.warning(
                "RCON '%s' failed (%s), falling back to tmux",
                command,
                describe_rcon_error(error),
            )

    return await tmux_send(command), None


def command_is_idempotent(command):
    """True if a console command is safe to retry."""
    first = command.split(" ", 1)[0].lower()
    if first.startswith("minecraft:"):
        first = first[len("minecraft:"):]
    return first in {"list", "save-all", "save-on", "save-off", "seed", "tps"}


async def save_world():
    """Flush the world to disk. Paper's plain save-all is async."""

    log.info("Saving the world")
    use_rcon = bool(RCON_PASSWORD)
    if use_rcon:
        try:
            output = await rcon.command("save-all flush", timeout=SAVE_TIMEOUT)
            lowered = strip_colors(output).lower()
            if "unknown" not in lowered and "incorrect" not in lowered:
                log.info("World saved over RCON: %s", one_line(strip_colors(output)))
                return True
            log.warning("save-all flush unsupported (%s)", output)
        except RCON_ERRORS as error:
            if getattr(error, "sent", False):
                log.warning(
                    "save-all flush was sent but the reply dropped (%s). Not sending it again.",
                    describe_rcon_error(error),
                )
                return True
            log.warning(
                "save-all flush failed (%s), trying tmux", describe_rcon_error(error)
            )
            use_rcon = False  # no point retrying RCON for plain save-all

    if use_rcon:
        ok, _ = await send_console("save-all", timeout=30)
    else:
        ok = await tmux_send("save-all")
    if not ok:
        log.error("Couldn't save the world: RCON and tmux both failed")
        return False
    await asyncio.sleep(SAVE_WAIT)
    log.info("World saved (save-all sent, waited %ss)", SAVE_WAIT)
    return True


async def send_stop():
    """Send `stop`, recording which process it was for. True if it was sent."""

    pid = await find_server_pid(force=True)
    if pid is None:
        log.warning("Stop not sent: the server process is already gone")
        return False
    log.info("Sending stop to the Minecraft server (pid %s)", pid)
    note_controlled_stop(pid)
    ok, _ = await send_console("stop", expect_close=True)
    if not ok:
        log.error("The stop command could not be sent: RCON and tmux both failed")
        clear_controlled_stop()
        clear_recent_stop()
    return ok


# ============================================================
# SERVER PROCESS
# ============================================================

HAVE_PROC = os.path.isdir("/proc/self")
SERVER_RE = re.compile(SERVER_PATTERN)
_server_pid = None  # cached so the common "still running" check forks nothing
_server_scan_at = 0.0
SERVER_SCAN_EVERY = 5  # re-scan at most every 5s so a second JVM is caught quickly without rescanning on every status poll


class AmbiguousServer(Exception):
    """More than one matching JVM: the bot refuses to guess which to control."""

    def __init__(self, pids):
        """Internal: init."""
        super().__init__(f"multiple matching servers: {sorted(pids)}")
        self.pids = sorted(pids)


def _proc_snapshot(pid):
    """(state, cmdline) from /proc, or None if the process is gone."""

    try:
        with open(f"/proc/{pid}/stat", "rb") as file:
            stat = file.read()
        with open(f"/proc/{pid}/cmdline", "rb") as file:
            cmdline = file.read()
        state = stat.rsplit(b")", 1)[1].split()[0]
    except (OSError, IndexError):
        return None
    return state, cmdline.replace(b"\0", b" ").decode("utf-8", "ignore")


def _cwd_matches(pid):
    """Internal: cwd matches."""
    if not SERVER_DIR or not HAVE_PROC:
        return True
    try:
        return os.path.realpath(f"/proc/{pid}/cwd") == SERVER_DIR
    except OSError:
        return False


def _is_live_server(pid):
    """True for a running (not zombie) JVM of our jar."""

    snap = _proc_snapshot(pid)
    return (
        snap is not None
        and snap[0] not in (b"Z", b"X")
        and SERVER_RE.search(snap[1]) is not None
        and _cwd_matches(pid)
    )


def _scan_proc():
    """Internal: scan proc."""
    try:
        names = os.listdir("/proc")
    except OSError:
        return []
    return [int(n) for n in names if n.isdigit() and _is_live_server(int(n))]


def _scan_cwd_mismatch():
    """PIDs running our jar whose working directory is not MC_SERVER_DIR.

    Those are ignored by find_server_pid, so /start can launch a second server.
    """

    if not SERVER_DIR or not HAVE_PROC:
        return []
    try:
        names = os.listdir("/proc")
    except OSError:
        return []
    mismatched = []
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        snap = _proc_snapshot(pid)
        if (
            snap is None
            or snap[0] in (b"Z", b"X")
            or SERVER_RE.search(snap[1]) is None
            or _cwd_matches(pid)
        ):
            continue
        mismatched.append(pid)
    return mismatched


async def warn_server_dir_mismatch():
    """Warn server dir mismatch."""
    if not SERVER_DIR or not HAVE_PROC:
        return
    pids = await asyncio.to_thread(_scan_cwd_mismatch)
    if not pids:
        return
    log.warning(
        "Java process(es) running %s but not in MC_SERVER_DIR=%s (PIDs %s). "
        "They are ignored, so the bot may treat the server as offline and "
        "/start can launch a second one. Fix the cwd or MC_SERVER_DIR.",
        JAR_NAME,
        SERVER_DIR,
        sorted(pids),
    )


async def pid_is_live(pid):
    """Non-/proc fallback: False for a missing or zombie process."""

    try:
        proc = await asyncio.create_subprocess_exec(
            "ps", "-o", "stat=", "-p", str(pid),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
    except OSError:
        return True

    stat = out.decode().strip()
    return bool(stat) and not stat.startswith("Z")


async def _pgrep_pids():
    """Internal: pgrep pids."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "pgrep", "-f", "--", SERVER_PATTERN,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
    except OSError:
        return None
    return [int(part) for part in out.split() if part.isdigit()]


async def find_server_pid(*, force=False):
    """PID of the one running server, None if offline.

    Raises AmbiguousServer if several JVMs match, instead of picking one.
    force=True skips the short cache so start/stop cannot miss a second JVM.
    """

    global _server_pid, _server_scan_at

    now = time.monotonic()
    if (
        not force
        and _server_pid is not None
        and HAVE_PROC
        and _is_live_server(_server_pid)
    ):
        if now - _server_scan_at < SERVER_SCAN_EVERY:
            return _server_pid
        # Recheck for a second JVM, but not on every status poll.
        others = await asyncio.to_thread(_scan_proc)
        _server_scan_at = now
        if len(others) > 1:
            _server_pid = None
            raise AmbiguousServer(others)
        if _server_pid in others:
            return _server_pid
        _server_pid = None

    if HAVE_PROC:
        # Reading /proc in a worker thread costs far less than forking pgrep
        # on every monitor tick while the server is offline.
        pids = await asyncio.to_thread(_scan_proc)
    else:
        pids = await _pgrep_pids()
        if pids is None:
            warn_throttled("pgrep", "pgrep is not available")
            return None

    live = []
    for pid in pids:
        if _is_live_server(pid) if HAVE_PROC else await pid_is_live(pid):
            live.append(pid)

    if len(live) > 1:
        raise AmbiguousServer(live)
    if live:
        _server_pid = live[0] if HAVE_PROC else None
        _server_scan_at = time.monotonic()
        return live[0]
    return None


async def server_running(*, force=False):
    """True if a matching Minecraft server process is running."""
    return (await find_server_pid(force=force)) is not None


async def server_age(pid):
    """Seconds the server process has been up, or None."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ps", "-o", "etimes=", "-p", str(pid),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
        return int(out.decode().strip())
    except (OSError, ValueError):
        return None


def read_sys_int(path):
    """Read sys int."""
    try:
        with open(path, encoding="utf-8") as file:
            return int(file.read().strip())
    except (OSError, ValueError):
        return None


def host_power_lines():
    """Battery percent, watt draw, and machine uptime. Missing sensors stay visible."""

    lines = []
    try:
        with open("/proc/uptime", encoding="utf-8") as file:
            seconds = float(file.read().split()[0])
        lines.append(f"Hardware uptime: {format_uptime(seconds)}")
    except (OSError, ValueError, IndexError):
        lines.append("Hardware uptime: unavailable")

    root = "/sys/class/power_supply"
    try:
        names = sorted(os.listdir(root))
    except OSError:
        names = []
    percent = None
    status = None
    watts = []
    for name in names:
        base = os.path.join(root, name)
        try:
            kind = open(os.path.join(base, "type"), encoding="utf-8").read().strip().lower()
        except OSError:
            continue
        if kind != "battery":
            continue
        cap = read_sys_int(os.path.join(base, "capacity"))
        if cap is not None:
            percent = cap
        try:
            status = open(os.path.join(base, "status"), encoding="utf-8").read().strip()
        except OSError:
            pass
        power = read_sys_int(os.path.join(base, "power_now"))
        if power is None:
            current = read_sys_int(os.path.join(base, "current_now"))
            voltage = read_sys_int(os.path.join(base, "voltage_now"))
            if current is not None and voltage is not None:
                power = current * voltage // 1_000_000  # microamps * microvolts -> microwatts
        if power is not None:
            watts.append(power / 1_000_000)
    if percent is None:
        lines.append("Battery: none")
    else:
        lines.append(f"Battery: {percent}%" + (f" ({status.lower()})" if status else ""))
    lines.append(f"Power: {sum(watts):.1f} W" if watts else "Power: unavailable")
    return lines


def format_uptime(seconds):
    """Format a duration in seconds as a human-readable string."""
    seconds = max(0, int(seconds))
    minutes = seconds // 60
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"


def format_bytes(num):
    """Format bytes."""
    num = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024
    return f"{num:.1f} TB"


def folder_size(path):
    """Folder size."""
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


_disk_cache = {"at": 0.0, "text": "Disk: unavailable"}


def disk_usage_text():
    """Used / total. Recomputed at most once every 10 minutes."""

    now = time.time()
    if now - _disk_cache["at"] < 600:
        return _disk_cache["text"]
    try:
        usage = shutil.disk_usage("/")
        text = f"Disk: {format_bytes(usage.used)} / {format_bytes(usage.total)}"
    except OSError:
        text = "Disk: unavailable"
    _disk_cache["at"] = now
    _disk_cache["text"] = text
    return text


def format_ram(kb):
    """Format a kilobyte count as a human-readable size."""
    if kb is None:
        return "unavailable"
    if kb >= 1024 * 1024:
        return f"{kb / 1024 / 1024:.1f} GB"
    if kb >= 1024:
        return f"{kb / 1024:.0f} MB"
    return f"{kb} KB"


def _proc_rss_kb(pid):
    """Internal: proc rss kb."""
    try:
        with open(f"/proc/{pid}/status", "r", encoding="utf-8") as file:
            for line in file:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError, IndexError, ValueError):
        pass
    return None


def _proc_ticks(pid):
    """Internal: proc ticks."""
    try:
        with open(f"/proc/{pid}/stat", "r", encoding="utf-8") as file:
            rest = file.read().rsplit(")", 1)[1].split()
        return int(rest[11]) + int(rest[12])  # utime + stime
    except (OSError, IndexError, ValueError):
        return None


async def _ps_usage(pid):
    """Internal: ps usage."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ps", "-o", "rss=,pcpu=", "-p", str(pid),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
        parts = out.decode().split()
        return int(float(parts[0])), float(parts[1])
    except (OSError, ValueError, IndexError):
        return None, None


async def process_usage(pid):
    """Return (rss_kb, cpu_percent). Either may be None."""

    rss_kb = _proc_rss_kb(pid)
    cpu = None
    before = _proc_ticks(pid)
    if before is not None:
        await asyncio.sleep(0.4)
        after = _proc_ticks(pid)
        if after is not None:
            try:
                hz = os.sysconf("SC_CLK_TCK")
            except (OSError, ValueError):
                hz = 100
            cpu = max(0.0, (after - before) / hz / 0.4 * 100)

    if rss_kb is None or cpu is None:
        ps_rss, ps_cpu = await _ps_usage(pid)
        rss_kb = ps_rss if rss_kb is None else rss_kb
        cpu = ps_cpu if cpu is None else cpu
    return rss_kb, cpu


def process_cmdline(pid):
    """Return the command line of a process."""
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as file:
            raw = file.read()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", "ignore")


_HEAP_RE = re.compile(
    r"(?:^|\s)-Xmx(\d+)([kKmMgG]?)(?=\s|$)"
    r"|-XX:MaxHeapSize=(\d+)([kKmMgG]?)(?=\s|$)"
)


def _unit_kb(number, suffix):
    """Java size suffixes. No suffix means bytes."""

    n = int(number)
    suffix = (suffix or "").lower()
    if suffix == "g":
        return n * 1024 * 1024
    if suffix == "m":
        return n * 1024
    if suffix == "k":
        return n
    return max(1, n // 1024)


def heap_limit_kb(cmdline):
    """Max heap from -Xmx / -XX:MaxHeapSize, in KiB, or None if it isn't there."""

    best = None
    for match in _HEAP_RE.finditer(cmdline or ""):
        if match.group(1) is not None:
            best = _unit_kb(match.group(1), match.group(2))
        else:
            best = _unit_kb(match.group(3), match.group(4))
    return best


def ram_pressure(rss_kb, memory, xmx_kb):
    """(high, message). A JVM sitting on its configured heap is not high.

    Other programs never trip this: without a visible -Xmx the percent is the
    Minecraft RSS only, and with -Xmx only that process's RSS above its heap.
    """

    if rss_kb is None:
        return False, None
    if xmx_kb:
        slack = max(1024 * 1024, int(xmx_kb * max(0, 100 - HEALTH_RAM) / 100))
        if rss_kb > xmx_kb + slack:
            return True, (
                f"High RAM: Minecraft is using {format_ram(rss_kb)}, "
                f"{format_ram(rss_kb - xmx_kb)} above its max heap {format_ram(xmx_kb)} "
                f"(allowed overhead {format_ram(slack)})"
            )
        return False, None
    pct = server_ram_percent(rss_kb, memory)
    if pct is not None and pct >= HEALTH_RAM:
        return True, (
            f"High RAM: Minecraft is using {pct:.0f}% of system memory "
            f"(limit {HEALTH_RAM}%, max heap unknown)"
        )
    return False, None


def format_players(info):
    """Format an (online, max) player tuple."""
    if info is None:
        return "Players: unavailable" if RCON_PASSWORD else "Players: RCON not configured"
    online, maximum = info
    return f"Players: {online}" if maximum is None else f"Players: {online}/{maximum}"


# ============================================================
# START SCRIPT
# ============================================================

async def launch_server():
    """Start the Minecraft server via the configured start script."""
    # A new JVM must not inherit the excuse recorded for the process we stopped.
    clear_recent_stop()
    clear_controlled_stop()
    try:
        log_offset = os.path.getsize(START_LOG)
    except OSError:
        log_offset = 0

    log.info("Launching the start script %s (output: %s)", START_SCRIPT, START_LOG)
    rotate_capped(START_LOG, START_LOG_MAX_BYTES, LOG_KEEP_HIGH)
    logfile = open(START_LOG, "ab")
    try:
        logfile.write(
            f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} start requested ---\n".encode()
        )
        logfile.flush()
        proc = await asyncio.create_subprocess_exec(
            START_SCRIPT,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=logfile,
            stderr=logfile,
            start_new_session=True,
        )
    finally:
        # The child inherited the fd; closing the parent copy is correct.
        logfile.close()

    log.info("Start script running (pid %s)", proc.pid)
    spawn(proc.wait())  # reap it, and keep the transport referenced
    return SimpleNamespace(proc=proc, log_offset=log_offset)


def is_stale_world_name(name):
    """True only for known world folders with a stale suffix.

    Matches world.old, world_nether.old-layout, world_the_end.old, etc.
    Does not match plugins.old, config.old, or arbitrary *.old folders.
    """
    for suffix in (".old", ".old-layout"):
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            if base in ("world", "world_nether", "world_the_end") or base.startswith("world"):
                return True
    return False


def clean_stale_world_folders():
    """Delete leftover world copies before start.

    Only known world folders ending in .old or .old-layout.
    *.before-restore copies are kept as a restore safety net.
    """

    root = server_root()
    removed = []
    try:
        names = os.listdir(root)
    except OSError:
        return removed
    for name in names:
        path = os.path.join(root, name)
        if is_stale_world_name(name) and os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
            removed.append(name)
            log.info("Removed stale world folder %s", name)
    return removed


def remove_legacy_dimension_folders():
    """Paper 26 crashes if world_nether exists beside world/dimensions.

    PAPER_DIMS (defined with the backup helpers) is shared with this cleanup.

    The nested folder is the layout Paper 26.3 loads. The old folder is only
    a migration source, and Paper refuses to overwrite files already there.
    """

    root = server_root()
    nested = os.path.join(root, "world", "dimensions", "minecraft")
    removed = []
    for dim, folder in PAPER_DIMS:
        if not os.path.isdir(os.path.join(nested, dim)):
            continue
        for name in (folder, folder + ".old-layout", folder + ".old"):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                removed.append(name)
                log.info("Removed legacy dimension folder %s", name)
    return removed


async def launch_or_report(msg):
    """Start the server or report why it cannot be started."""
    # /start already checked, but a crash restart or a race must not exec the
    # script while Paper is up. The start script also exits immediately if the
    # tmux session still exists, which is exactly what a Paper 26 shutdown looks
    # like for up to a minute.
    if await server_running(force=True):
        await msg.set(
            "[+] **Server is already running.** Not launching a second process.",
            force=True,
        )
        return None
    if not await wait_until_fully_stopped(msg):
        await msg.set("[!] The old server did not finish shutting down.")
        return None
    await close_wake_listener()
    removed = await asyncio.to_thread(clean_stale_world_folders)
    removed.extend(await asyncio.to_thread(remove_legacy_dimension_folders))
    if removed:
        await msg.set("Removed old world folders: " + ", ".join(removed))

    try:
        return await launch_server()
    except OSError as error:
        log.error("Couldn't run the start script %s: %s", START_SCRIPT, error)
        await msg.set(f"[!] Couldn't run the start script:\n`{error}`", force=True)
        return None


# ============================================================
# LOG HELPERS
# ============================================================

READY_RE = re.compile(rb"Done \([\d.,]+s\)!")
STARTING_RE = re.compile(rb"Starting minecraft server version", re.IGNORECASE)
# The vanilla/Paper line is `]: Stopping server`. Player chat can contain the
# same words and must not hide a crash or block an auto-restart.
STOPPING_RE = re.compile(rb"\]: Stopping server")
_CHUNK = 32 * 1024


class LogCursor:
    """Follows the server log from the moment it is created.

    Reads only bytes appended since the previous poll, instead of re-reading
    up to a megabyte every few seconds, and never matches a "Done" line from
    an earlier session. A new inode or a shorter file means the log rotated,
    so the new file belongs to this boot.
    """

    def __init__(self, path=None):
        """Internal: init."""
        self.path = path or LOG_PATH
        try:
            stat = os.stat(self.path)
            self.ino, self.pos = stat.st_ino, stat.st_size
        except OSError:
            self.ino, self.pos = None, 0
        self.start_ino, self.start_pos = self.ino, self.pos
        self.carry = b""
        self.ready = False

    def poll(self):
        """True once Done was logged. False while waiting. None if unreadable."""

        if self.ready:
            return True
        try:
            stat = os.stat(self.path)
            if stat.st_ino != self.ino or stat.st_size < self.pos:
                self.ino, self.pos, self.carry = stat.st_ino, 0, b""
            with open(self.path, "rb") as file:
                file.seek(self.pos)
                while not self.ready:
                    data = file.read(_CHUNK)
                    if not data:
                        break
                    self.pos += len(data)
                    window = self.carry + data
                    self.carry = window[-64:]  # a Done line can straddle reads
                    self.ready = READY_RE.search(window) is not None
        except OSError:
            return None
        return self.ready

    def start_offset(self):
        """Where this boot's output begins (0 if the log rotated)."""

        try:
            stat = os.stat(self.path)
        except OSError:
            return 0
        same = stat.st_ino == self.start_ino and stat.st_size >= self.start_pos
        return self.start_pos if same else 0

    def tail(self, n=4):
        """Tail."""
        return tail_lines(self.path, n, self.start_offset())


def _read_tail(path, size):
    """Internal: read tail."""
    if size <= 0:
        return None  # why: callers treat None as unreadable; b"" would hide a bad size
    try:
        with open(path, "rb") as file:
            file.seek(0, os.SEEK_END)
            end = file.tell()
            file.seek(max(0, end - size))
            return file.read()
    except OSError:
        return None


def boot_state():
    """True if the newest boot in the log tail reached Done, False if it is
    still loading, None if the log says nothing.

    Used by /status, which has no start marker. Comparing the last
    'Starting minecraft server' with the last Done avoids treating an older
    Done in the same file as the current boot.
    """

    data = _read_tail(LOG_PATH, LOG_READ_MAX)
    if data is None:
        return None

    start = done = -1
    for match in STARTING_RE.finditer(data):
        start = match.start()
    for match in READY_RE.finditer(data):
        done = match.start()

    if start < 0 and done < 0:
        return None
    if done < 0:
        return False
    return start < 0 or done > start


def log_shows_clean_stop():
    """True if this bot's stop logged `Stopping server` after the command.

    Unexpected stops (in-game /stop) have no recorded offset, so those still
    use the last LOG_READ_MAX bytes, and only a shutdown after the newest
    `Starting minecraft server` line counts.
    """

    if expected_stop is not None:
        return shutdown_after_stop()

    data = _read_tail(LOG_PATH, LOG_READ_MAX)
    if not data:
        return False

    stop = -1
    for match in STOPPING_RE.finditer(data):
        stop = match.start()
    if stop < 0:
        return False

    start = -1
    for match in STARTING_RE.finditer(data):
        start = match.start()
    return stop > start


def tail_lines(path, n=6, start=0):
    """Return the last n lines of a file, respecting a start offset."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as file:
            # A rotated or truncated log is shorter than the old start offset.
            origin = 0 if start > size else max(start, size - 12000)
            file.seek(origin)
            data = file.read().decode(errors="ignore")
    except OSError:
        return []

    lines = [line.rstrip() for line in data.splitlines() if line.strip()]
    return lines[-n:]


def _clip(line, width=120):
    """Internal: clip."""
    line = redact_ips(line).replace("```", "'''")
    return line if len(line) <= width else line[: width - 1] + "…"


def failure_details(cursor=None, launch=None):
    """Return recent log lines that explain a failed start or stop."""
    sections = []

    if launch:
        script = [
            line
            for line in tail_lines(START_LOG, 4, launch.log_offset)
            if not line.startswith("--- ")
        ]
        if script:
            sections.append(
                "start script:\n" + "\n".join(_clip(line) for line in script)
            )

    server = cursor.tail(4) if cursor else tail_lines(LOG_PATH, 4)
    if server:
        sections.append(
            "server log:\n" + "\n".join(_clip(line) for line in server)
        )

    if not sections:
        return ""

    body = "\n\n".join(sections)
    if len(body) > 1200:  # leave room for the message this is appended to
        body = body[:1199] + "…"
    return "\n```\n" + body + "\n```"


# ============================================================
# WAIT FOR SERVER STATE
# ============================================================

async def wait_for_state(
    msg, want_running, t0, working_text, done_text, timeout_text, timeout=None
):
    """Poll until the server reaches the desired running state."""
    timeout = STOP_TIMEOUT if timeout is None else timeout

    while True:
        elapsed = int(time.monotonic() - t0)

        if (await server_running()) == want_running:
            if not want_running:
                relay.server_stopped()
            await msg.set(f"{done_text} (took {elapsed}s)", force=True)
            return True

        if elapsed >= timeout:
            # A stop that never started shutting down must not hide a later crash.
            if not want_running:
                release_stop_expectation_unless_shutting_down()
            await msg.set(
                f"{timeout_text} (gave up after {elapsed}s)", force=True
            )
            return False

        await msg.set(f"{working_text} ({elapsed}s)")
        await asyncio.sleep(POLL_INTERVAL)


async def wait_for_ready(
    msg, t0, cursor, launch, working_text, done_text, timeout_text
):
    """Wait until the server really accepts players.

    The log's Done line is the primary signal. If the log can't be read, an RCON
    reply is the fallback. A live process alone never counts as ready.
    """

    seen_running = False
    last_stage = None

    async def fail(text):
        """Fail."""
        await msg.set(text + failure_details(cursor, launch), force=True)
        return False

    while True:
        elapsed = time.monotonic() - t0

        if await server_running():
            seen_running = True
            ready = cursor.poll()

            if ready is True:
                await msg.set(f"{done_text} (took {int(elapsed)}s)", force=True)
                return True

            if ready is None and elapsed >= LOG_FALLBACK_AFTER:
                if await rcon_ready():
                    await msg.set(
                        f"{done_text} (took {int(elapsed)}s; confirmed over RCON)",
                        force=True,
                    )
                    return True
                if not RCON_PASSWORD:
                    await msg.set(
                        "[.] **Server process is running, readiness unverified.**\n"
                        "The log can't be read and RCON isn't configured, so the "
                        "bot can't tell when loading finishes. Check "
                        "`MC_LOG_PATH`." + failure_details(cursor, launch),
                        force=True,
                    )
                    return False

            stage = "process up, loading world"

        elif seen_running:
            return await fail("[!] Server process exited while starting.")

        else:
            code = launch.proc.returncode if launch else None
            if code not in (None, 0):
                return await fail(f"[!] Start script failed (exit code {code}).")
            if elapsed >= LAUNCH_TIMEOUT:
                return await fail(
                    f"[!] Server process never appeared after {int(elapsed)}s."
                )
            stage = "launching process"

        if elapsed >= START_TIMEOUT:
            return await fail(f"{timeout_text} (gave up after {int(elapsed)}s)")

        # A stage change is shown at once; the ticking counter is throttled.
        await msg.set(
            f"{working_text} · {stage} ({int(elapsed)}s)",
            force=stage != last_stage,
        )
        last_stage = stage
        await asyncio.sleep(POLL_INTERVAL)


# ============================================================
# PLAYER COUNT
# ============================================================

PLAYER_COUNT_RE = re.compile(
    r"There are\s+(\d+)\s+of\s+(?:a max of\s+)?(\d+)\s+players?\s+online",
    re.IGNORECASE,
)
PLAYER_SLASH_RE = re.compile(
    r"(\d+)\s*/\s*(\d+)\s+players?\s+online", re.IGNORECASE
)
PLAYER_FALLBACK_RES = (
    re.compile(r"There are\s+(\d+)\s+players?", re.IGNORECASE),
    re.compile(r"(\d+)\s+players?\s+online", re.IGNORECASE),
)


async def get_player_info():
    """Return (online, max) or None if RCON failed. max may be None."""

    if not RCON_PASSWORD:
        return None

    try:
        output = await rcon.command("list")
    except RCON_ERRORS as error:
        warn_throttled(
            "players", "RCON player check failed: %s", describe_rcon_error(error)
        )
        return None

    clean = strip_colors(output)
    for pattern in (PLAYER_COUNT_RE, PLAYER_SLASH_RE):
        match = pattern.search(clean)
        if match:
            return int(match.group(1)), int(match.group(2))

    for pattern in PLAYER_FALLBACK_RES:
        match = pattern.search(clean)
        if not match:
            continue
        # "0 of a max of 20 players online" must not report 20 as the online count.
        before = clean[max(0, match.start() - 24):match.start()]
        if re.search(r"max of\s*$", before, re.IGNORECASE):
            continue
        return int(match.group(1)), None
    return None


async def get_player_count():
    """Return the number of online players, or None on failure."""
    info = await get_player_info()
    return None if info is None else info[0]


# ============================================================
# IDLE SHUTDOWN
# ============================================================

class IdleState:
    """Idle countdown. The clock only advances while the count is known."""

    def __init__(self):
        """Internal: init."""
        self.reset()

    def reset(self):
        """Reset."""
        self.since = None
        self.paused_at = None
        self.pause_noted = False
        self.status = None  # Status for the channel warning

    def elapsed(self, now):
        """Elapsed."""
        if self.since is None:
            return 0
        paused = 0.0 if self.paused_at is None else now - self.paused_at
        return max(0, int(now - self.since - paused))

    def remaining(self, now):
        """Remaining."""
        return max(0, IDLE_TIMEOUT - self.elapsed(now))

    def pause(self, now):
        """Pause."""
        if self.since is not None and self.paused_at is None:
            self.paused_at = now

    def resume(self, now):
        """Resume."""
        if self.paused_at is None:
            return
        if self.since is not None:
            self.since += now - self.paused_at
        self.paused_at = None
        self.pause_noted = False


idle = IdleState()


def format_remaining(remaining):
    """Format remaining idle time."""
    return f"{remaining // 60}:{remaining % 60:02d}"


def idle_text(remaining):
    """Text for the idle-shutdown countdown."""
    return (
        "[!] **Minecraft server is empty.**\n"
        f"Server will shut down in **{format_remaining(remaining)}** "
        "if nobody joins."
    )


async def get_idle_channel():
    """Return the channel used for idle-shutdown warnings."""
    if not IDLE_CHANNEL_ID:
        return None

    channel = bot.get_channel(IDLE_CHANNEL_ID)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(IDLE_CHANNEL_ID)
    except EDIT_ERRORS as error:
        log.warning("Couldn't fetch idle channel: %r", error)
        return None


async def ensure_idle_message(now):
    """Create or update the idle-shutdown countdown message."""
    if idle.status is not None and idle.status.alive:
        return True

    channel = await get_idle_channel()
    if channel is None or idle.since is None:
        return False

    try:
        message = await channel.send(idle_text(idle.remaining(now)))
    except EDIT_ERRORS as error:
        log.warning("Couldn't send idle warning: %r", error)
        return False

    idle.status = Status(message, min_gap=IDLE_EDIT_INTERVAL)
    return True


async def cancel_idle_shutdown(reason="A player joined."):
    """Cancel a pending idle shutdown."""
    log.info("Idle shutdown cancelled: %s", reason)
    warning = idle.status
    idle.reset()
    if warning is not None:
        await warning.set(f"[+] **Idle shutdown cancelled.**\n{reason}", force=True)


async def idle_offline():
    """Clear idle state when the server goes offline."""
    warning = idle.status
    idle.reset()
    if warning is not None:
        await warning.set("[-] **Minecraft server went offline.**", force=True)


async def note_idle_pause(now):
    """Record that the idle countdown is paused."""
    if idle.since is None:
        return

    idle.pause(now)
    if idle.pause_noted:
        return
    idle.pause_noted = True
    if idle.status is not None:
        await idle.status.set(
            "[!] **Minecraft server is empty.**\n"
            "Player check unavailable. Idle timer is paused.",
            force=True,
        )


async def run_idle_shutdown():
    """Shut the server down after the idle timeout."""
    if not try_lock("idle-shutdown"):
        return

    try:
        # One last look, taken while holding the lock.
        count = await get_player_count()
        now = time.monotonic()

        # Never shut down if RCON can't tell us.
        if count is None:
            log.warning("Idle shutdown skipped: player count unavailable.")
            await note_idle_pause(now)
            return

        if count > 0:
            await cancel_idle_shutdown("A player joined.")
            return

        if not await ensure_idle_message(now):
            return

        log.info("Idle countdown finished: saving the world and stopping the server")
        msg = idle.status
        await msg.set(
            "[-] **Idle timer reached 0.**\n"
            "Saving the world and shutting down...",
            force=True,
        )

        if not await save_world():
            await msg.set(
                "[!] **Idle shutdown aborted.**\nCouldn't save the world. "
                "The idle countdown starts over.",
                force=True,
            )
            idle.reset()  # try again after a full countdown, not every tick
            return

        # A player may have joined while the world was saving. Look again
        # right before stopping.
        count = await get_player_count()
        if count is None:
            await msg.set(
                "[!] **Idle shutdown aborted.**\n"
                "Player check unavailable after saving. The idle countdown "
                "starts over.",
                force=True,
            )
            idle.reset()
            return
        if count > 0:
            await cancel_idle_shutdown("A player joined while the world saved.")
            return

        if not await send_stop():
            await msg.set(
                "[!] **Idle shutdown failed.**\nCouldn't send the stop command.",
                force=True,
            )
            idle.reset()
            return

        # If it doesn't stop in time the expectation stays: a slow shutdown
        # that finishes later is still the stop this bot asked for.
        await wait_for_state(
            msg,
            False,
            time.monotonic(),
            "[-] Shutting down...",
            "[-] **Minecraft server is offline.**",
            "[!] Server is still running.",
        )
        idle.reset()
    finally:
        release()


async def idle_tick():
    """One idle-shutdown step. Called only while the server is up and idle."""

    if _stress_running:
        if idle.since is not None:
            await cancel_idle_shutdown("A stress test is running.")
        return

    count = await get_player_count()
    now = time.monotonic()

    # Unknown count must not advance, or expire, the timer.
    if count is None:
        await note_idle_pause(now)
        return

    idle.resume(now)

    if count > 0:
        if idle.since is not None:
            await cancel_idle_shutdown("A player joined.")
        return

    if idle.since is None:
        idle.since = now
        log.info("Server is empty, idle countdown started (%s seconds)", IDLE_TIMEOUT)
        await ensure_idle_message(now)
        return

    remaining = idle.remaining(now)
    if remaining > 0:
        if await ensure_idle_message(now):
            await idle.status.set(idle_text(remaining))
        return

    await run_idle_shutdown()


# ============================================================
# TPS
# ============================================================

TPS_RE = re.compile(r"TPS from last ([^:\n]+):\s*([^\n]+)")
TPSLOG_INTERVAL = 60
TPSLOG_MAX = 20


async def tmux_capture():
    """Tmux capture."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux", "capture-pane", "-p", "-J", "-t", MC_SESSION, "-S", "-500",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await proc.communicate()
    except OSError:
        return ""
    return out.decode(errors="ignore")


MSPT_RE = re.compile(r"MSPT from last ([^:\n]+):\s*([^\n]+)")


async def _metric(command, pattern, timeout=6.0):
    """Read a Paper TPS or MSPT line over RCON, then the tmux console."""

    if RCON_PASSWORD:
        try:
            output = await rcon.command(command)
            found = pattern.findall(strip_colors(output))
            if found:
                labels, values = found[-1]
                return labels.strip(), values.strip()
        except RCON_ERRORS as error:
            log.warning("RCON %s failed: %s", command, describe_rcon_error(error))

    if tps_lock is None:
        return None

    async with tps_lock:
        before = await tmux_capture()
        if not await tmux_send(command):
            return None
        waited = 0.0
        while waited < timeout:
            await asyncio.sleep(0.5)
            waited += 0.5
            after = await tmux_capture()
            # why: counting matches in the 500-line scrollback false-times-out when old lines scroll off
            if after.startswith(before):
                fresh = after[len(before):]
            else:
                tail = before[-200:]
                index = after.find(tail) if tail else -1
                fresh = after[index + len(tail):] if index >= 0 else after
            found = pattern.findall(fresh)
            if found:
                labels, values = found[-1]
                return labels.strip(), values.strip()
    return None


async def get_tps(timeout=6.0):
    """Query the server TPS via RCON."""
    return await _metric("tps", TPS_RE, timeout)


async def get_mspt(timeout=6.0):
    """Query the server MSPT via RCON."""
    return await _metric("mspt", MSPT_RE, timeout)


def fmt_tps(labels, values):
    """Fmt tps."""
    names = [part.strip() for part in labels.split(",")]
    nums = [part.strip() for part in values.split(",")]
    return " | ".join(f"{name}: {value}" for name, value in zip(names, nums))


# ============================================================
# ALERTS, AUTO RESTART, CRASH DETECTION
# ============================================================

async def send_alert(text=None, allow_mentions=False, embed=None):
    """Post a message or embed to the alert channel."""
    content = clip_discord(calm(text)) if text else None
    summary = content or (embed.title if embed is not None else "")
    log.info("Alert: %s", one_line(summary))
    capture_log("alerts", one_line(summary))

    if not ALERT_CHANNEL_ID:
        log.warning("[alert, no channel configured] %s", summary)
        return None

    extra = {}
    if allow_mentions:
        extra["allowed_mentions"] = discord.AllowedMentions(
            everyone=True, roles=True, users=True
        )

    try:
        channel = bot.get_channel(ALERT_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(ALERT_CHANNEL_ID)
        return await channel.send(content, embed=embed, **extra)
    except EDIT_ERRORS as error:
        log.error("Couldn't send alert: %s", error)
        return None


async def say_game(text, prefix="[bot]"):
    """Say one line in Minecraft chat. prefix is kept so players can see it is the bot."""

    body = clean_chat(text, 180)
    payload = f"{prefix} {body}".strip()
    ok, _output = await send_console(f"say {payload}")
    if not ok:
        log.warning("In-game message not delivered: %s", payload)
    return ok


async def say_bot(text):
    """Say one line in Minecraft. Every bot line starts with [bot-warn]:."""

    body = clean_chat(text, 200)
    if body.lower().startswith("[bot-warn]"):
        body = body.split(":", 1)[-1].strip()
    payload = f"{BOT_WARN_PREFIX} {body}".strip()
    if not RCON_PASSWORD:
        return False, "RCON isn't configured."
    try:
        await rcon.command(f"say {payload}")
    except RCON_ERRORS as error:
        warn_throttled(
            "say-bot",
            "In-game warning not delivered: %s",
            describe_rcon_error(error),
        )
        return False, describe_rcon_error(error)
    return True, payload


async def auto_restart():
    """Restart the server after an unexpected stop, within limits."""
    if AUTO_RESTART_MAX <= 0:
        log.info("Auto-restart is off (MC_AUTO_RESTART_MAX=0).")
        return

    now = time.monotonic()
    auto_restart_times[:] = [
        stamp for stamp in auto_restart_times if now - stamp < AUTO_RESTART_WINDOW
    ]

    if len(auto_restart_times) >= AUTO_RESTART_MAX:
        await send_alert(
            "[!] **Auto-restart disabled for now.**\n"
            f"The server has restarted {len(auto_restart_times)} times "
            f"in the last {AUTO_RESTART_WINDOW // 60} minutes."
        )
        return

    if not try_lock("auto-restart"):
        await send_alert(
            f"[!] **Auto-restart skipped.** `/{current_op}` is in progress."
        )
        return

    try:
        auto_restart_times.append(now)
        log.warning(
            "Auto-restart %s of %s allowed per %s minutes",
            len(auto_restart_times),
            AUTO_RESTART_MAX,
            AUTO_RESTART_WINDOW // 60,
        )
        msg = Status(
            await send_alert(
                "[.] **Minecraft crashed.**\nAttempting automatic restart..."
            )
        )
        t0 = time.monotonic()
        cursor = LogCursor()
        launch = await launch_or_report(msg)
        if launch is None:
            return

        await wait_for_ready(
            msg, t0, cursor, launch,
            "[.] Auto-restarting",
            "[+] **Server is back up.**",
            "[!] **Auto-restart failed.**",
        )
    finally:
        release()


def process_was_replaced(was_running, previous_pid, pid):
    """True when the JVM was swapped without the monitor seeing it go down."""

    return bool(
        was_running
        and previous_pid is not None
        and pid is not None
        and pid != previous_pid
    )


def forget_stop_if_other_process(pid):
    """A different JVM must not inherit the excuse recorded for the one we stopped.

    The PID can be reused. The kernel start time tells a new process apart from
    a one-tick gap where the same process was briefly invisible.
    """

    if pid is None or recent_stop is None:
        return False
    if recent_stop.pid != pid:
        clear_recent_stop()
        return True
    started = process_start_ticks(pid)
    recorded = getattr(recent_stop, "started", None)
    if started is not None and recorded is not None and started != recorded:
        clear_recent_stop()
        return True
    return False


def our_stop_explains(dead_pid, force_crash=False):
    """True only when this bot asked that same process to stop, and the log agrees."""

    if force_crash or dead_pid is None or recent_stop is None:
        return False
    if recent_stop.pid != dead_pid or not recent_stop_by_us():
        return False
    return bool(shutdown_after_stop(recent_stop) or _stop_log_replaced(recent_stop))


async def handle_unexpected_stop(dead_pid=None, force_crash=False):
    """The server process vanished and this bot did not ask for it.

    The log is consulted only to *describe* an unexpected stop: a normal
    shutdown line means someone stopped it in game, so it is not restarted.
    force_crash is a stop whose window already expired; that line must not
    hide the kill.
    """

    clean = False if force_crash else log_shows_clean_stop()
    # A slow finish of our own /stop is not "someone else stopped it".
    # Only a shutdown line after that command counts, not an older one in the tail.
    if our_stop_explains(dead_pid, force_crash):
        log.info(
            "Server finished a stop this bot requested %ss ago (pid %s). Not alerting.",
            int(time.monotonic() - recent_stop.at),
            dead_pid,
        )
        return
    log.warning(
        "Minecraft stopped without this bot (%s)",
        "log shows a normal shutdown" if clean else "no shutdown in the log, likely a crash",
    )
    if clean:
        await send_alert(
            "[-] **Minecraft server stopped.**\n"
            "The stop was not issued by this bot (the log shows a normal "
            "shutdown), so it will not be restarted automatically."
        )
        return

    mention = f"{ALERT_MENTION} " if ALERT_MENTION else ""
    await send_alert(
        f"{mention}[x] **Minecraft server went offline unexpectedly.**\n"
        "It may have crashed." + failure_details(),
        allow_mentions=bool(ALERT_MENTION),
    )

    if AUTO_RESTART and AUTO_RESTART_MAX > 0:
        # Crash recovery is about to start the server, so this offline gap
        # is not a closed server. Hold the automatic backup until it is.
        global backup_hold_until
        backup_hold_until = time.monotonic() + START_TIMEOUT
        spawn(auto_restart())  # don't block the monitor for the whole restart


# ============================================================
# MONITOR
# ============================================================

def new_monitor_state():
    """New monitor state."""
    return SimpleNamespace(last_running=None, last_ambiguous=None, last_pid=None)


async def monitor_tick(state):
    """One monitor cycle: detect start/stop/crash and idle state."""
    try:
        pid = await find_server_pid(force=True)
    except AmbiguousServer as error:
        now = time.monotonic()
        warn_throttled("ambiguous", "Several matching servers: %s", error.pids)
        last = state.last_ambiguous
        if last is None or now - last > AMBIGUOUS_ALERT_EVERY:
            state.last_ambiguous = now
            await send_alert(
                "[!] **More than one Minecraft server process matches.**\n"
                f"PIDs {error.pids}. The bot won't start, stop or restart "
                "anything until only one is left (or `MC_SERVER_DIR` is set)."
            )
        return

    running = pid is not None
    was_running = state.last_running
    previous_pid = state.last_pid
    state.last_running = running
    state.last_pid = pid
    forget_stop_if_other_process(pid)

    stop = expected_stop
    if stop is not None and running:
        # A different process is up, or the stop never took effect: this
        # expectation is stale and must not hide a later crash.
        if pid != stop.pid or time.monotonic() - stop.at > EXPECTED_STOP_MAX:
            clear_controlled_stop()
            if recent_stop is not None and recent_stop.pid != pid:
                clear_recent_stop()
            stop = None

    self_managed = current_op in SELF_MANAGED_OPS
    expired = False
    replaced = process_was_replaced(was_running, previous_pid, pid)

    if was_running is None:
        log.info(
            "Monitor sees the Minecraft server %s",
            f"running (pid {pid})" if running else "offline",
        )
        if running:
            relay.server_up(first=True)
    elif replaced:
        log.warning(
            "Minecraft PID changed from %s to %s without an observed stop.",
            previous_pid,
            pid,
        )
        if not self_managed:
            await send_alert(
                "[x] **Minecraft process was replaced.**\n"
                f"PID {previous_pid} disappeared and PID {pid} is up. "
                "Something else restarted it, so the bot did not start another copy."
                + failure_details()
            )
    elif running != was_running:
        if running:
            log.info("Minecraft server process is up (pid %s)", pid)
            relay.server_up(first=False)
        elif stop is not None and time.monotonic() - stop.at > EXPECTED_STOP_MAX:
            log.warning(
                "PID %s exited %ss after the stop request. The shutdown window expired, so this is a crash.",
                stop.pid,
                int(time.monotonic() - stop.at),
            )
            clear_controlled_stop()
            stop = None
            expired = True
        elif stop is not None and shutdown_after_stop(stop):
            log.info("Minecraft server process ended after Stopping server (pid %s)", stop.pid)
        elif stop is not None and _stop_log_replaced(stop):
            log.warning(
                "Stop was requested for pid %s, but latest.log rotated before Stopping server. "
                "Not treating that as a crash.",
                stop.pid,
            )
        elif stop is not None:
            log.warning(
                "Stop was requested for pid %s but Stopping server was not logged after the command. Treating it as a crash.",
                stop.pid,
            )
            clear_controlled_stop()
            stop = None
        elif self_managed:
            log.info("Minecraft server process ended during /%s", current_op)
        else:
            log.warning("Minecraft server process ended and this bot did not stop it")
        if not running:
            relay.server_stopped()

    if not running and idle.since is not None:
        await idle_offline()

    if was_running and not running:
        if expired or (stop is None and not self_managed):
            await handle_unexpected_stop(previous_pid, force_crash=expired)

    if not running:
        # Only keep the controlled-stop expectation if the log shows a normal shutdown.
        # Otherwise clear it so handle_unexpected_stop reports the exit.
        if stop is None or not log_shows_clean_stop():
            clear_controlled_stop()

    if (
        running
        and IDLE_ACTIVE
        and stop is None
        and current_op is None
    ):
        await idle_tick()

    await sample_backup_clock(pid if running else None)
    if running:
        await warn_overdue_backup()
    elif current_op is None and not backup_restart_hold():
        await auto_backup_if_due()


async def monitor_loop():
    """Background loop that watches the server process."""
    await bot.wait_until_ready()
    state = new_monitor_state()

    while True:
        try:
            await monitor_tick(state)
        except Exception:
            log.exception("Monitor tick failed")
        await asyncio.sleep(MONITOR_INTERVAL)


# ============================================================
# HEALTH ALERTS (RAM, TPS, a stuck server; CPU is only reported)
# ============================================================

HEALTH_ALERTS = env_bool("MC_HEALTH_ALERTS", True)
HEALTH_INTERVAL = env_int("MC_HEALTH_INTERVAL", 30, 10)
HEALTH_RAM = env_int("MC_HEALTH_RAM", 90, 1)
# Paper's 1-minute TPS is often 19.9x on a healthy server, so 20 false-alarms.
HEALTH_TPS = env_float("MC_HEALTH_TPS", 18.0, 1.0)
HEALTH_SUSTAIN = env_int("MC_HEALTH_SUSTAIN", 3, 1)
HEALTH_STUCK_AFTER = env_int("MC_HEALTH_STUCK_AFTER", 60, 10)
HEALTH_GRACE = env_int("MC_HEALTH_GRACE", 180, 0)
HEALTH_COOLDOWN = env_int("MC_HEALTH_COOLDOWN", 60, 30)
HEALTH_PROBE_TIMEOUT = 10.0
CPU_COUNT = os.cpu_count() or 1


class HealthState:
    """Tracks health-alert state for the current server process."""
    def __init__(self):
        """Internal: init."""
        self.tps_supported = True
        self.last_message = -1e9
        self.alerting = False
        self.incident = 0
        self.opened = 0.0
        self.reset()

    def reset(self):
        """Forget everything about the current server process."""

        self.pid = None
        self.seen_at = 0.0
        self.high_ram = 0
        self.low_tps = 0
        self.stuck_since = None
        self.alerting = False


hstate = HealthState()


def server_ram_percent(rss_kb, memory):
    """Minecraft RSS as a percent of system RAM. Other programs do not count."""

    if rss_kb is None or memory is None or memory[1] <= 0:
        return None
    return rss_kb * 100 / memory[1]


def system_memory():
    """(used_kb, total_kb) of the whole machine, or None."""

    try:
        values = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            for line in file:
                name, _, rest = line.partition(":")
                if name in ("MemTotal", "MemAvailable"):
                    values[name] = int(rest.split()[0])
                    if len(values) == 2:
                        break
        return values["MemTotal"] - values["MemAvailable"], values["MemTotal"]
    except (OSError, KeyError, IndexError, ValueError):
        return None


async def health_probe(state):
    """One cheap RCON round trip. responded is True/False, or None if unknown."""

    result = SimpleNamespace(responded=None, tps=None, tps_text=None)
    if not RCON_PASSWORD:
        return result

    command = "tps" if state.tps_supported else "list"
    try:
        output = await rcon.command(command, timeout=HEALTH_PROBE_TIMEOUT)
    except asyncio.TimeoutError:
        result.responded = False  # connected (or tried to), but no answer
        return result
    except RCON_ERRORS as error:
        # Refused, busy, login problems: not evidence the server is stuck.
        warn_throttled(
            "health-rcon", "Health check can't use RCON: %s", describe_rcon_error(error)
        )
        return result

    result.responded = True
    clean = strip_colors(output)
    found = TPS_RE.findall(clean)
    if found:
        labels, values = found[-1]
        result.tps_text = fmt_tps(labels.strip(), values.strip())
        number = re.search(r"\d+(?:\.\d+)?", values)
        if number:
            result.tps = float(number.group())
    elif command == "tps" and "unknown" in clean.lower():
        state.tps_supported = False  # vanilla has no /tps; use `list` from now on
        log.info("The server has no tps command. Health checks skip TPS.")
    return result


def health_stats(pid_age, probe, rss_kb, cpu, cpu_total, memory, players, xmx_kb=None):
    """Health stats."""
    lines = [
        "TPS: " + (probe.tps_text or "unavailable"),
        format_players(players),
    ]
    if pid_age is not None:
        lines.append(f"Uptime: {format_uptime(pid_age)}")
    if cpu is None:
        lines.append("CPU: unavailable")
    else:
        lines.append(
            f"CPU: server {cpu:.0f}% of one core "
            f"({cpu_total:.0f}% of {CPU_COUNT} core{'s' if CPU_COUNT != 1 else ''})"
        )
    if memory is None:
        lines.append(
            f"RAM: server {format_ram(rss_kb)}"
            + (f" | max heap {format_ram(xmx_kb)}" if xmx_kb else "")
        )
    else:
        used, total = memory
        lines.append(
            f"RAM: server {format_ram(rss_kb)}"
            + (f" | max heap {format_ram(xmx_kb)}" if xmx_kb else "")
            + f" | system {used * 100 / total:.0f}% used "
            f"({format_ram(used)} of {format_ram(total)})"
        )
    if probe.responded is None:
        lines.append("Responding: unknown (no RCON)")
    elif probe.responded:
        lines.append("Responding: yes")
    else:
        lines.append("Responding: **NO**")
    return lines


async def health_tick():
    """One health check: RAM, TPS, stuck RCON."""
    state = hstate
    try:
        pid = await find_server_pid()
    except AmbiguousServer:
        return

    if pid is None:
        if state.alerting:
            await close_health_incident(state, "Server went offline.")
        state.reset()
        return

    now = time.monotonic()
    if pid != state.pid:
        state.reset()
        state.pid = pid
        state.seen_at = now

    # Booting, or the bot itself is starting/stopping/saving the server.
    if now - state.seen_at < HEALTH_GRACE or current_op is not None or expected_stop is not None:
        return

    (rss_kb, cpu), probe, cmdline = await asyncio.gather(
        process_usage(pid), health_probe(state), asyncio.to_thread(process_cmdline, pid)
    )
    memory = system_memory()
    cpu_total = None if cpu is None else cpu / CPU_COUNT
    xmx_kb = heap_limit_kb(cmdline)
    high_ram, ram_detail = ram_pressure(rss_kb, memory, xmx_kb)
    state.high_ram = state.high_ram + 1 if high_ram else 0
    state.low_tps = state.low_tps + 1 if probe.tps is not None and probe.tps < HEALTH_TPS else 0
    if probe.responded is False:
        if state.stuck_since is None:
            state.stuck_since = now
    elif probe.responded:
        state.stuck_since = None
    stuck_for = 0 if state.stuck_since is None else time.monotonic() - state.stuck_since

    problems = []
    if state.high_ram >= HEALTH_SUSTAIN and ram_detail:
        problems.append(ram_detail)
    if state.low_tps >= HEALTH_SUSTAIN:
        problems.append(f"Low TPS: {probe.tps:.1f} (limit {HEALTH_TPS})")
    if stuck_for >= HEALTH_STUCK_AFTER:
        problems.append(f"Server not responding for {int(stuck_for)}s (it may be frozen)")

    if problems:
        log.warning("Health problems: %s", one_line(" | ".join(problems)))
        capture_log("health", one_line(" | ".join(problems)))
    # One health message per cooldown, with every stat in it.
    if now - state.last_message < HEALTH_COOLDOWN:
        return

    if problems:
        state.last_message = time.monotonic()
        was_alerting = state.alerting
        fresh = not was_alerting
        if fresh:
            state.incident += 1
            state.opened = time.time()
        state.alerting = True
        players = None
        if probe.responded:
            try:
                players = await asyncio.wait_for(get_player_info(), 4)
            except asyncio.TimeoutError:
                players = None
        age = await server_age(pid)
        opened = time.strftime("%H:%M:%S", time.localtime(state.opened))
        mark = "Start" if fresh else "Still open"
        lines = [f"**{mark}: warning {state.incident}** (opened {opened})", ""]
        lines += [f"• {item}" for item in problems]
        lines += ["", *health_stats(age, probe, rss_kb, cpu, cpu_total, memory, players, xmx_kb)]
        await send_alert(
            embed=panel(
                f"Health warning {state.incident}",
                lines,
                COLOR_BAD,
                footer=f"Incident {state.incident} · opened {opened} · repeats every {HEALTH_COOLDOWN}s",
            )
        )
        await say_bot(" | ".join(problems))
    elif state.alerting:
        players = None
        try:
            players = await asyncio.wait_for(get_player_info(), 4)
        except asyncio.TimeoutError:
            pass
        stats = health_stats(None, probe, rss_kb, cpu, cpu_total, memory, players, xmx_kb)
        await close_health_incident(state, "Back to normal.", stats)
        await say_bot("Server health is back to normal.")


async def close_health_incident(state, reason, stats=None):
    """Close the open health warning so the next one is obviously a new incident."""

    if not state.alerting:
        return
    number = state.incident
    opened = state.opened
    elapsed = int(time.time() - opened) if opened else 0
    opened_s = time.strftime("%H:%M:%S", time.localtime(opened)) if opened else "unknown"
    state.last_message = time.monotonic()
    state.alerting = False
    lines = [
        f"**End of warning {number}**",
        f"Opened {opened_s}, lasted {format_uptime(elapsed)}.",
        reason,
    ]
    if stats:
        lines += ["", *stats]
    await send_alert(
        embed=panel(
            f"Health warning {number} ended",
            lines,
            COLOR_OK,
            footer=f"Incident {number} closed · opened {opened_s} · lasted {format_uptime(elapsed)}",
        )
    )


async def health_loop():
    """Background loop that runs health checks."""
    await bot.wait_until_ready()
    while True:
        try:
            await health_tick()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Health check failed")
        await asyncio.sleep(HEALTH_INTERVAL)


# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():
    """Discord on_ready: log in and start background tasks once."""
    log.info("Logged in as %s. MC Server Manager %s is online.", bot.user, VERSION)
    if getattr(bot, "_announced", False):
        return
    bot._announced = True
    spawn(announce_online())


DIRT_BLOCK = (
    "................\n"
    "..##...#..##....\n"
    ".#..#.#..#..#...\n"
    "..##...#..##....\n"
    ".#..#.#..#..#...\n"
    "..##...#..##....\n"
    ".#..#.#..#..#...\n"
    "................"
)

COMMANDS = (
    "/panel  buttons and a menu for logs\n"
    "/status  online, players, uptime\n"
    "/start  launch the server\n"
    "/stop  save, then stop\n"
    "/restart  save, stop, start\n"
    "/save  save the world\n"
    "/health  TPS, RAM, CPU, disk\n"
    "/players  who is online\n"
    "/tps  TPS and MSPT, 5-minute graph\n"
    "/ping  ping an IP or a player\n"
    "/pingall  ping everyone online\n"
    "/backup make  back up now\n"
    "/backup list  list, delete, or keep backups\n"
    "/backup restore  restore a backup\n"
    "/say  send a line to Minecraft chat\n"
    "/log  log one system for 20 minutes\n"
    "/log tps  longer TPS graph\n"
    "/stresstest  4-player load, network, health log\n"
    "/stats  health, hunger, inventory\n"
    "/map  top-down map\n"
    "/console  live console\n"
    "/serveredit  view or change server.properties\n"
    "/rcontest  check RCON\n"
    "/test  test one system\n"
    "/botstop  stop the bot only\n"
    "/botreset  restart the bot"
)


def online_embed():
    """Build the bot-online embed."""
    embed = discord.Embed(
        title=f"Bot online {VERSION}",
        description=f"Version {VERSION}. The bot is up. The Minecraft server was left as it was.",
        color=0x8B5A2B,
    )
    embed.set_footer(text=f"version {VERSION}")
    embed.add_field(name="Commands", value=COMMANDS, inline=False)
    return embed


async def announce_online():
    """Post that the bot has come online."""
    channel_id = ALERT_CHANNEL_ID or LOG_CHANNEL_ID
    if not channel_id:
        log.info("No alert or log channel, so the online message was not posted.")
        return
    try:
        channel = bot.get_channel(channel_id)
        if channel is None:
            channel = await bot.fetch_channel(channel_id)
        await channel.send(embed=online_embed())
    except EDIT_ERRORS as error:
        log.warning("Couldn't post the online message: %s", error)


@bot.event
async def on_app_command_completion(interaction, command):
    """Audit successful slash commands."""
    elapsed = (discord.utils.utcnow() - interaction.created_at).total_seconds()
    cmd_log.info("/%s finished in %.1fs", command.qualified_name, elapsed)


@bot.tree.error
async def on_app_command_error(interaction, error):
    """Log and reply when a slash command fails."""
    original = getattr(error, "original", error)
    log.error(
        "Command %s failed for %s: %r",
        command_label(interaction),
        describe_user(interaction.user),
        original,
        exc_info=original,
    )

    if isinstance(original, AmbiguousServer):
        text = (
            f"[!] More than one matching server process (PIDs {original.pids}). "
            "Refusing to act on either."
        )
    else:
        text = "[!] Something went wrong. Check the bot console."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=False)
        else:
            await interaction.response.send_message(text, ephemeral=False)
    except EDIT_ERRORS:
        pass


# ============================================================
# /STATUS
# ============================================================

COLOR_OK = 0x3E6B4F
COLOR_BAD = 0x7A3E3E
COLOR_WAIT = 0x6E6244
COLOR_INFO = 0x3E5166


def panel(title, lines, color=COLOR_INFO, footer=None):
    """Build a Discord embed panel."""
    embed = discord.Embed(title=title, color=color, timestamp=discord.utils.utcnow())
    body = "\n".join(line for line in lines if line)
    embed.description = body or "\u200b"
    embed.set_footer(text=footer or time.strftime("%H:%M:%S"))
    return embed


@bot.tree.command(name="status", description="Check the Minecraft server status")
async def status(interaction: discord.Interaction):
    """Slash command: show whether the server is running."""
    if not await gate(interaction):
        return
    await interaction.response.defer()

    pid = await find_server_pid()
    if pid is None:
        await followup_embed(interaction, panel("Server", ["Offline"], COLOR_BAD))
        return

    age, info = await asyncio.gather(server_age(pid), get_player_info())
    loading = (
        info is None
        and age is not None
        and age < START_TIMEOUT
        and boot_state() is False
    )
    lines = [format_players(info)]
    if age is not None:
        lines.append(f"Uptime: {format_uptime(age)}")
    if AUTO_BACKUP or BACKUP_COMMAND:
        lines.append(backup_status_line())
    title = "Server starting" if loading else "Server online"
    await followup_embed(
        interaction, panel(title, lines, COLOR_WAIT if loading else COLOR_OK)
    )


# ============================================================
# /START /STOP /RESTART
# ============================================================

@bot.tree.command(name="start", description="Start the Minecraft server")
@managed("start")
async def start(interaction: discord.Interaction):
    """Slash command: start the Minecraft server."""
    msg = await open_status(interaction, "[.] Starting Minecraft server...")

    if await server_running(force=True):
        await msg.set(
            "[+] **Server is already running.** Not launching a second process.",
            force=True,
        )
        return

    await cancel_idle_shutdown("Server is starting.")

    t0 = time.monotonic()
    cursor = LogCursor()
    launch = await launch_or_report(msg)
    clear_controlled_stop()
    if launch is None:
        return

    await wait_for_ready(
        msg, t0, cursor, launch,
        "[.] Starting Minecraft server",
        "[+] **Server is ready. Players can join.**",
        "[!] **Server didn't finish loading.**",
    )


async def run_stop(interaction):
    """Run stop."""
    msg = await open_status(interaction, "[.] Stopping Minecraft server...")

    if not await server_running(force=True):
        await msg.set("[-] **Minecraft server is already offline.**", force=True)
        return

    await cancel_idle_shutdown("Manual shutdown requested.")

    await msg.set("[.] Saving Minecraft world...", force=True)
    if not await save_world():
        await msg.set("[!] **Couldn't save the world.**\nStop aborted.", force=True)
        return

    t0 = time.monotonic()
    if not await send_stop():
        await msg.set(
            "[!] **Couldn't send the stop command.**\n"
            "The process was already gone, or RCON and tmux both failed.",
            force=True,
        )
        return

    # On a timeout the expectation is kept: if the server finishes shutting
    # down later, that is still the stop this command asked for.
    await wait_for_state(
        msg, False, t0,
        "[.] Stopping Minecraft server...",
        "[-] **Minecraft server is offline.**",
        "[!] **Server is still running.**",
    )


async def run_restart(interaction):
    """Run restart."""
    msg = await open_status(interaction, "[.] Restarting Minecraft server...")
    await cancel_idle_shutdown("Server restart requested.")

    if await server_running(force=True):
        await msg.set("[.] Saving Minecraft world...", force=True)
        if not await save_world():
            await msg.set(
                "[!] **Couldn't reach the server console.**\nRestart aborted.",
                force=True,
            )
            return

        t0 = time.monotonic()
        await msg.set("[.] Stopping Minecraft server...", force=True)
        if not await send_stop():
            await msg.set(
                "[!] **Couldn't send stop command.**\nRestart aborted.", force=True
            )
            return

        stopped = await wait_for_state(
            msg, False, t0,
            "[.] Restart: stopping server...",
            "[-] Server stopped. Starting again...",
            "[!] **Restart aborted. Server is still running.**",
        )
        if not stopped:
            return

        await asyncio.sleep(PORT_WAIT)
    else:
        await msg.set("[.] Server was offline. Starting...", force=True)

    clear_controlled_stop()
    t0 = time.monotonic()
    cursor = LogCursor()
    launch = await launch_or_report(msg)
    if launch is None:
        return

    await wait_for_ready(
        msg, t0, cursor, launch,
        "[.] Restart: starting server",
        "[+] **Restart complete. Server is ready.**",
        "[!] **Restart failed.**",
    )


CONFIRM_TIMEOUT = 30


class ConfirmView(discord.ui.View):
    """Yes/Cancel buttons that only the person who ran the command can press."""

    def __init__(self, user, op, runner):
        """Internal: init."""
        super().__init__(timeout=CONFIRM_TIMEOUT)
        self.user = user
        self.op = op
        self.runner = runner
        self.message = None
        self.done = False
        open_confirms.add(self)
        for child in self.children:
            if getattr(child, "label", "") == "Yes, do it":
                child.label = {
                    "stop": "Stop server",
                    "restart": "Restart server",
                    "stresstest": "Start test",
                }.get(op, "Yes, do it")

    async def interaction_check(self, interaction):
        """Interaction check."""
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                f"Only {self.user.display_name} can confirm this.", ephemeral=False
            )
            return False
        return await gate(interaction)

    async def invalidate(self, reason):
        """Invalidate."""
        if self.done:
            return
        self.done = True
        self.stop()
        open_confirms.discard(self)
        if self.message is None:
            return
        try:
            await self.message.edit(
                content=f"Confirmation closed. {reason} `/{self.op}` was not run.",
                view=None,
            )
        except EDIT_ERRORS:
            pass

    @discord.ui.button(label="Yes, do it", style=discord.ButtonStyle.danger)
    async def yes(self, interaction, button):
        """Yes."""
        if self.done:
            await interaction.response.send_message(
                "That confirmation is already closed.", ephemeral=False
            )
            return
        self.done = True
        self.stop()
        open_confirms.discard(self)
        cmd_log.info("/%s confirmed by %s", self.op, describe_user(interaction.user))
        if self.op in ("stop", "restart") and _stress_running:
            await interaction.response.edit_message(
                content="Cannot shut off server during a test.", view=None
            )
            return
        if not try_lock(self.op):
            await interaction.response.edit_message(
                content=f"Busy: `/{current_op}` is still in progress.", view=None
            )
            return
        try:
            await interaction.response.edit_message(
                content=f"/{self.op} confirmed by {interaction.user.display_name}.",
                view=None,
            )
            await self.runner(interaction)
        finally:
            release()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def no(self, interaction, button):
        """No."""
        if self.done:
            await interaction.response.send_message(
                "That confirmation is already closed.", ephemeral=False
            )
            return
        self.done = True
        self.stop()
        open_confirms.discard(self)
        cmd_log.info("/%s cancelled by %s", self.op, describe_user(interaction.user))
        await interaction.response.edit_message(
            content=f"Cancelled. `/{self.op}` was not run.", view=None
        )

    async def on_timeout(self):
        """On timeout."""
        if self.done:
            return
        self.done = True
        open_confirms.discard(self)
        if self.message is not None:
            try:
                await self.message.edit(
                    content=f"Timed out. `/{self.op}` was not run.", view=None
                )
            except EDIT_ERRORS:
                pass


async def ask_confirm(interaction, op, title, runner):
    """Show a confirmation before a disruptive command. Nothing is locked until Yes."""

    if current_op is not None:
        await deny(interaction, f"Busy: `/{current_op}` is still in progress.")
        return

    await interaction.response.defer()
    if not await server_running(force=True):
        if op == "stop":
            await followup_text(interaction, "[-] **Minecraft server is already offline.**")
            return
        # Restarting an offline server just starts it. Nothing to confirm.
        if not try_lock(op):
            await followup_text(interaction, f"Busy: `/{current_op}` is still in progress.")
            return
        try:
            await runner(interaction)
        finally:
            release()
        return

    info = None
    if RCON_PASSWORD:
        try:
            info = await asyncio.wait_for(get_player_info(), 4)
        except asyncio.TimeoutError:
            info = None
    if info is None:
        players = ""
    elif info[0]:
        players = f"\n**{info[0]} player(s)** are online right now."
    else:
        players = "\nNobody is online."

    view = ConfirmView(interaction.user, op, runner)
    view.message = await interaction.followup.send(
        f"{title}{players}\nPress the button within {CONFIRM_TIMEOUT} seconds.",
        view=view,
        wait=True,
    )


@bot.tree.command(name="stop", description="Stop the Minecraft server")
async def stop(interaction: discord.Interaction):
    """Slash command: stop the Minecraft server."""
    if not await gate(interaction):
        return
    if _stress_running:
        await deny(interaction, "Cannot shut off server during a test.")
        return
    await ask_confirm(interaction, "stop", "**Stop the Minecraft server?**", run_stop)


@bot.tree.command(name="restart", description="Restart the Minecraft server")
async def restart(interaction: discord.Interaction):
    """Slash command: restart the Minecraft server."""
    if not await gate(interaction):
        return
    if _stress_running:
        await deny(interaction, "Cannot shut off server during a test.")
        return
    await ask_confirm(
        interaction, "restart", "**Restart the Minecraft server?**", run_restart
    )



# ============================================================
# AUTOMATIC BACKUP (offline only; manual /backup may run live)
# ============================================================

backup_hold_until = 0.0
_backup_state = {
    "uptime": 0.0,
    "playtime": 0.0,
    "last_backup": 0.0,
    "warned": False,
    "last_fail": 0.0,
    "last_pid": None,
    "last_start": None,
    "last_age": None,
    "manual_number": 0,
    "auto_number": 0,
}
_auto_backup_task = None
# The clock is sampled every monitor tick, but the state file (fsync'd) is only
# rewritten when something changed or this many seconds passed.
BACKUP_STATE_SAVE_EVERY = 300
_backup_state_saved_at = -1e9


def backup_intervals_due(seconds, after):
    """How many backup intervals this much uptime or playtime covers."""

    after = int(after)
    if after <= 0:
        return 0
    return int(max(0, seconds) // after)


def backup_should_warn(seconds, after, skips, already_warned):
    """Warn only after `skips` intervals were missed, and only once."""

    return (not already_warned) and backup_intervals_due(seconds, after) >= int(skips)


def backup_should_run(seconds, after, offline, busy, held, failed_recently):
    """Automatic copies run only on a closed server, and not during a restart."""

    return bool(
        offline and not busy and not held and not failed_recently and seconds >= after
    )


def backup_metric_seconds():
    """Backup metric seconds."""
    if AUTO_BACKUP_METRIC == "playtime":
        return float(_backup_state["playtime"])
    return float(_backup_state["uptime"])


def load_backup_state():
    """Load persisted backup counters."""
    try:
        with open(BACKUP_STATE_PATH, encoding="utf-8") as file:
            raw = json.load(file)
    except (OSError, ValueError):
        return
    if not isinstance(raw, dict):
        return
    for key in ("uptime", "playtime", "last_backup", "last_fail"):
        try:
            _backup_state[key] = float(raw.get(key) or 0)
        except (TypeError, ValueError):
            _backup_state[key] = 0.0
    _backup_state["warned"] = bool(raw.get("warned"))
    _backup_state["last_pid"] = raw.get("last_pid")
    _backup_state["last_start"] = raw.get("last_start")
    for key in ("manual_number", "auto_number"):
        try:
            _backup_state[key] = int(raw.get(key) or 0)
        except (TypeError, ValueError):
            _backup_state[key] = 0
    try:
        age = raw.get("last_age")
        _backup_state["last_age"] = None if age is None else float(age)
    except (TypeError, ValueError):
        _backup_state["last_age"] = None


def save_backup_state():
    """Persist backup counters."""
    global _backup_state_saved_at
    _backup_state_saved_at = time.monotonic()
    tmp = BACKUP_STATE_PATH + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as file:
            json.dump(_backup_state, file)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, BACKUP_STATE_PATH)
    except OSError as error:
        log.warning("Couldn't save backup state: %s", error)


async def save_backup_state_async():
    """Persist backup state off the event loop."""
    await asyncio.to_thread(save_backup_state)  # why: fsync can stall the loop for hundreds of ms


def note_backup_success():
    """Record a successful backup."""
    _backup_state["uptime"] = 0.0
    _backup_state["playtime"] = 0.0
    _backup_state["last_backup"] = time.time()
    _backup_state["warned"] = False
    _backup_state["last_fail"] = 0.0
    log.info("Backup counters reset")


def backup_status_line():
    """One-line summary of backup state."""
    seconds = backup_metric_seconds()
    skips = backup_intervals_due(seconds, AUTO_BACKUP_AFTER)
    kind = "playtime" if AUTO_BACKUP_METRIC == "playtime" else "uptime"
    last = _backup_state["last_backup"]
    last_s = (
        "never"
        if not last
        else time.strftime("%Y-%m-%d %H:%M", time.localtime(last))
    )
    auto = "on" if AUTO_BACKUP else "off"
    return (
        f"Since last backup: {format_uptime(seconds)} {kind} "
        f"({skips} x {format_uptime(AUTO_BACKUP_AFTER)}, auto {auto}, last {last_s})"
    )


def backup_folder_name(kind, number, stamp):
    """(auto/manual)backup (Number) date time. stamp is already filename-safe."""

    label = "autobackup" if kind == "auto" else "manualbackup"
    return f"{label} ({int(number)}) {stamp}"


BACKUP_FILES = (
    "server.properties", "bukkit.yml", "spigot.yml", "commands.yml",
    "ops.json", "whitelist.json", "banned-players.json", "banned-ips.json",
    "usercache.json", "permissions.yml",
)
BACKUP_DIRS = ("plugins", "config")
PAPER_DIMS = (("the_nether", "world_nether"), ("the_end", "world_the_end"))


def backup_sources():
    """Everything Paper needs: all worlds, player files, plugins, and config."""

    if BACKUP_SOURCE:
        return [
            os.path.realpath(os.path.expanduser(part.strip()))
            for part in BACKUP_SOURCE.split(",")
            if part.strip()
        ]
    root = SERVER_DIR or os.path.dirname(os.path.dirname(os.path.abspath(LOG_PATH)))
    found = []
    if not os.path.isdir(root):
        return found
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        skip = name.endswith((".old", ".before-restore", ".zip")) or "before-restore" in name
        if skip:
            continue
        if name.startswith("world") and os.path.isdir(path):
            found.append(path)
    for name in BACKUP_DIRS:
        path = os.path.join(root, name)
        if os.path.isdir(path):
            found.append(path)
    for name in BACKUP_FILES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            found.append(path)
    return found


def _copy_into(src, dest_dir, deadline=None):
    """Copy one file or directory into dest_dir. Skips the backup folder itself.

    deadline is a monotonic timestamp. The copy raises TimeoutError once it
    is past, because asyncio.to_thread cannot cancel a stuck copy.
    """

    name = os.path.basename(src.rstrip(os.sep)) or "backup-item"
    target = os.path.join(dest_dir, name)
    skip = {os.path.realpath(BACKUP_DIR)} if BACKUP_DIR else set()

    def ignore(directory, names):
        """Ignore."""
        dropped = []
        for item in names:
            full = os.path.realpath(os.path.join(directory, item))
            if full in skip or any(full.startswith(root + os.sep) for root in skip):
                dropped.append(item)
        return dropped

    def copy_with_deadline(src_path, dst_path, *, follow_symlinks=True):
        # why: to_thread cannot be cancelled, so the copy itself must notice the deadline
        if deadline is not None and time.monotonic() > deadline:
            raise TimeoutError(f"backup copy exceeded {BACKUP_TIMEOUT}s")
        return shutil.copy2(src_path, dst_path, follow_symlinks=follow_symlinks)

    if os.path.isdir(src):
        shutil.copytree(
            src, target, ignore=ignore, dirs_exist_ok=True,
            copy_function=copy_with_deadline,
        )
    elif os.path.isfile(src):
        os.makedirs(dest_dir, exist_ok=True)
        copy_with_deadline(src, os.path.join(dest_dir, name))
    else:
        raise FileNotFoundError(src)
    return target


async def perform_backup(kind):
    """Make backup folder (Number) and copy into it. Optional command runs after.

    Returns (exit_code, output_tail, folder). exit_code is None on timeout.
    """

    if not BACKUP_DIR:
        return 1, b"MC_BACKUP_DIR is not set", ""
    sources = backup_sources()
    if not sources:
        return 1, b"Nothing to back up. Set MC_SERVER_DIR or MC_BACKUP_SOURCE.", ""
    key = "auto_number" if kind == "auto" else "manual_number"
    number = int(_backup_state.get(key) or 0) + 1
    _backup_state[key] = number
    await save_backup_state_async()
    stamp = time.strftime("%Y-%m-%d %H-%M")
    folder = os.path.join(BACKUP_DIR, backup_folder_name(kind, number, stamp))
    deadline = time.monotonic() + BACKUP_TIMEOUT
    try:
        need = await asyncio.to_thread(
            lambda: sum(folder_size(src) if os.path.isdir(src) else os.path.getsize(src) for src in sources)
        )
        free = shutil.disk_usage(os.path.dirname(folder) or ".").free
        if free < need:
            # why: a copy that fills the disk holds the lock and, for manual backups, leaves autosave off
            return 1, f"not enough free disk ({free} free, {need} needed)".encode(), folder
    except OSError as error:
        log.warning("Couldn't check free disk before backup: %s", error)
    try:
        os.makedirs(folder, exist_ok=False)
        for src in sources:
            await asyncio.to_thread(_copy_into, src, folder, deadline)
        manifest = os.path.join(folder, "backup.txt")
        with open(manifest, "w", encoding="utf-8") as file:
            file.write(f"kind={kind}\nnumber={number}\nwhen={stamp}\n")
            file.write("sources\n")
            file.writelines(src + "\n" for src in sources)
    except TimeoutError:
        return None, f"timed out after {BACKUP_TIMEOUT}s".encode(), folder
    except OSError as error:
        return 1, str(error).encode(), folder
    if not BACKUP_COMMAND:
        return 0, f"copied to {folder}".encode(), folder
    env = os.environ.copy()
    env["MC_BACKUP_DEST"] = folder
    env["MC_BACKUP_KIND"] = kind
    env["MC_BACKUP_NUMBER"] = str(number)
    code, tail = await run_shell(BACKUP_COMMAND, BACKUP_TIMEOUT, env=env)
    return code, tail or f"copied to {folder}".encode(), folder


def backup_restart_hold():
    """Backup restart hold."""
    return time.monotonic() < backup_hold_until


def uptime_delta(prev_pid, prev_start, prev_age, pid, start, age):
    """Seconds of this process not already counted. A new pid counts its age once."""

    if pid is None or age is None:
        return 0
    if prev_pid == pid and prev_start == start and prev_age is not None:
        return max(0, int(age) - int(prev_age))
    return max(0, int(age))


async def sample_backup_clock(pid):
    """Add server uptime, and playtime while someone is online, since last backup."""

    if not (AUTO_BACKUP or BACKUP_COMMAND):
        return
    prev_pid = _backup_state["last_pid"]
    prev_warned = _backup_state["warned"]
    age = await server_age(pid) if pid else None
    start = process_start_ticks(pid) if pid else None
    delta = uptime_delta(
        _backup_state["last_pid"],
        _backup_state["last_start"],
        _backup_state["last_age"],
        pid,
        start,
        age,
    )
    observed = (
        _backup_state["last_pid"] == pid
        and _backup_state["last_start"] == start
        and _backup_state["last_age"] is not None
    )
    _backup_state["uptime"] = float(_backup_state["uptime"]) + delta
    # Playtime only counts intervals we actually watched with someone online.
    # Seeding a new pid with its whole age would pretend that was all played.
    if observed and delta and AUTO_BACKUP_METRIC == "playtime":
        info = await get_player_info()
        if info and info[0] > 0:
            _backup_state["playtime"] = float(_backup_state["playtime"]) + delta
    _backup_state["last_pid"] = pid
    _backup_state["last_start"] = start
    _backup_state["last_age"] = None if age is None else float(age)
    if backup_metric_seconds() < AUTO_BACKUP_AFTER:
        _backup_state["warned"] = False
    changed = pid != prev_pid or _backup_state["warned"] != prev_warned
    if changed or time.monotonic() - _backup_state_saved_at >= BACKUP_STATE_SAVE_EVERY:
        await save_backup_state_async()


async def warn_overdue_backup():
    """One warning after two skipped intervals, only while the server stays up."""

    if not AUTO_BACKUP:
        return
    seconds = backup_metric_seconds()
    if not backup_should_warn(
        seconds, AUTO_BACKUP_AFTER, AUTO_BACKUP_SKIPS, _backup_state["warned"]
    ):
        return
    _backup_state["warned"] = True
    await save_backup_state_async()
    skips = backup_intervals_due(seconds, AUTO_BACKUP_AFTER)
    kind = "playtime" if AUTO_BACKUP_METRIC == "playtime" else "uptime"
    extra = (
        "\n`MC_BACKUP_COMMAND` is empty, so nothing will be copied until that is set."
        if not BACKUP_COMMAND
        else ""
    )
    await send_alert(
        "[!] **Automatic backup is overdue.**\n"
        f"The server has {format_uptime(seconds)} of {kind} since the last "
        f"backup, which is {skips} intervals of {format_uptime(AUTO_BACKUP_AFTER)} "
        f"({AUTO_BACKUP_SKIPS} skipped).\n"
        "Automatic backups run only while the server is **offline**, so this "
        "one is waiting for it to close. Stop the server, or run `/backup` "
        "to copy the world now."
        + extra
    )


async def auto_backup_if_due():
    """Copy the world only when it is closed and a full interval has elapsed."""

    global _auto_backup_task
    if not AUTO_BACKUP or not BACKUP_DIR:
        return
    if _auto_backup_task is not None and not _auto_backup_task.done():
        return
    seconds = backup_metric_seconds()
    failed_recently = (
        _backup_state["last_fail"]
        and time.time() - _backup_state["last_fail"] < AUTO_BACKUP_RETRY
    )
    if not backup_should_run(
        seconds,
        AUTO_BACKUP_AFTER,
        offline=True,
        busy=current_op is not None,
        held=backup_restart_hold(),
        failed_recently=failed_recently,
    ):
        return
    if not try_lock("auto-backup"):
        return

    async def run():
        """Run."""
        kind = "playtime" if AUTO_BACKUP_METRIC == "playtime" else "uptime"
        try:
            try:
                running = await server_running(force=True)
            except AmbiguousServer:
                log.warning("Auto-backup skipped: more than one server process")
                return
            if running:
                log.info("Auto-backup skipped: the server is online")
                return
            await send_alert(
                "**Automatic backup starting.** The server is offline and has "
                f"{format_uptime(backup_metric_seconds())} of {kind} since the "
                f"last backup (every {format_uptime(AUTO_BACKUP_AFTER)})."
            )
            try:
                code, tail, folder = await perform_backup("auto")
            except OSError as error:
                _backup_state["last_fail"] = time.time()
                await save_backup_state_async()
                await report_backup_failure("auto", f"could not start: {error}")
                return
            lines = tail.decode(errors="ignore").strip().splitlines()[-4:]
            detail = "\n".join(_clip(line) for line in lines)
            if code == 0:
                note_backup_success()
                await save_backup_state_async()  # why: note_backup_success no longer fsyncs on the loop
                await prune_backups()
                await send_alert(
                    "**Automatic backup finished.** "
                    f"`{folder}`\nCounters reset. The next one waits until the "
                    "server is offline again and another "
                    f"{format_uptime(AUTO_BACKUP_AFTER)} of {kind} has passed."
                )
                return
            elif code is None:
                _backup_state["last_fail"] = time.time()
                await save_backup_state_async()
                reason = f"timed out after {BACKUP_TIMEOUT}s"
            else:
                _backup_state["last_fail"] = time.time()
                await save_backup_state_async()
                reason = f"exit code {code}"
            await report_backup_failure("auto", reason, folder, detail)
        finally:
            release()

    _auto_backup_task = spawn(run())


load_backup_state()

# ============================================================
# /SAVE /BACKUP
# ============================================================

@bot.tree.command(name="save", description="Save the world with save-all flush")
@managed("save")
async def save(interaction: discord.Interaction):
    """Slash command: save the world."""
    if _stress_running:
        await deny(interaction, "Cannot save during a test. Changes are not kept.")
        return
    msg = await open_status(interaction, "Saving world...")

    if not await server_running(force=True):
        await msg.set("[-] **Server offline.**", force=True)
        return

    t0 = time.monotonic()
    if await save_world():
        await msg.set(
            f"**World saved.** ({int(time.monotonic() - t0)}s)", force=True
        )
    else:
        await msg.set(
            "[!] **Couldn't save the world.**\nRCON and tmux both failed.",
            force=True,
        )


async def kill_proc(proc, group=False):
    """Kill a process (and its whole group if we started it in one), then
    reap it so no zombie is left behind."""

    try:
        if group:
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except OSError:
        pass
    try:
        await asyncio.wait_for(proc.wait(), 5)
    except asyncio.TimeoutError:
        pass


async def run_shell(command, timeout, env=None):
    """Run a shell command. Returns (exit_code, output_tail); the code is None
    on timeout. Only the last bytes of output are kept, so a chatty tool
    can't grow memory."""

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,  # own process group, so a timeout kills rclone too
        env=env,
    )
    tail = b""

    async def pump():
        """Pump."""
        nonlocal tail
        while True:
            chunk = await proc.stdout.read(4096)
            if not chunk:
                break
            tail = (tail + chunk)[-2000:]
        await proc.wait()

    try:
        await asyncio.wait_for(pump(), timeout)
    except asyncio.TimeoutError:
        await kill_proc(proc, group=True)
        return None, tail
    return proc.returncode, tail


async def restore_autosave():
    """Turn autosave back on, retrying once. True only if it was accepted."""

    for attempt in (1, 2):
        ok, output = await send_console("save-on")
        if ok and not console_reply_rejected(output):
            clear_autosave_marker()
            return True
        log.warning("save-on attempt %s failed (%r)", attempt, output)
        if attempt == 1:
            await asyncio.sleep(1)
    log.error("save-on FAILED: autosave may still be disabled on the server")
    return False


def mark_autosave_off():
    """Remember that save-off succeeded, in case this process is killed."""

    try:
        with open(AUTOSAVE_MARKER, "w", encoding="utf-8") as file:
            file.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
    except OSError as error:
        log.warning("Couldn't record that autosave is off: %s", error)


def clear_autosave_marker():
    """Remove the autosave-in-progress marker."""
    try:
        os.remove(AUTOSAVE_MARKER)
    except OSError:
        pass


async def recover_interrupted_backup():
    """If the bot died between save-off and save-on, turn autosave back on."""

    await bot.wait_until_ready()
    if not os.path.isfile(AUTOSAVE_MARKER):
        return
    log.warning(
        "A backup was interrupted after save-off (%s). Turning autosave back on.",
        AUTOSAVE_MARKER,
    )
    try:
        running = await server_running()
    except AmbiguousServer:
        running = True
    if not running:
        log.warning(
            "Can't send save-on yet: the server is offline. The marker stays "
            "so the next bot start will try again."
        )
        await send_alert(
            "[!] **Autosave may still be disabled.** The bot stopped during a "
            "backup after `save-off`, and the server is offline so `save-on` "
            "was not sent. Start the server and restart the bot, or run "
            "`save-on` in the console.",
            allow_mentions=bool(ALERT_MENTION),
        )
        return
    if await restore_autosave():
        log.info("Autosave restored after an interrupted backup")
        return
    await send_alert(
        "[!] **Autosave may still be disabled.** The bot stopped during a "
        "backup after `save-off`, and `save-on` failed on startup. Run it in "
        "the server console.",
        allow_mentions=bool(ALERT_MENTION),
    )


def chat_player_message(line):
    """Return (player, message) from a latest.log chat line, or (None, None)."""

    text = strip_colors(relay_clean(line or ""))
    text = re.sub(r"^\[[^\]]+\]\s+\[[^\]]+\]:\s*", "", text)
    text = re.sub(r"^\[Not Secure\]\s*", "", text)
    match = re.match(r"<([^>]{1,32})>\s*(.*)$", text)
    if not match:
        return None, None
    return match.group(1).strip(), match.group(2).strip()


def is_backup_chat(message):
    """True when the chat body is the !backup command, not a mention inside a sentence."""

    return bool(message) and message.split()[0].lower() == "!backup"


def backup_failure_log(kind, reason, folder="", output=""):
    """Append a detailed failure log and return that file path."""

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"{stamp} {kind} backup failed", reason]
    if folder:
        lines.append(f"folder: {folder}")
    if output:
        lines.append("output:")
        lines.extend(output.splitlines()[-20:])
    body = "\n".join(lines).rstrip() + "\n\n"
    path = os.path.join(BOT_LOG_DIR, "backup-failed.log")
    try:
        os.makedirs(BOT_LOG_DIR, exist_ok=True)
        with open(path, "a", encoding="utf-8") as file:
            file.write(body)
    except OSError as error:
        log.warning("Couldn't write %s: %s", path, error)
    if folder:
        try:
            with open(os.path.join(folder, "failed.log"), "w", encoding="utf-8") as file:
                file.write(body)
        except OSError:
            pass
    log.error("Backup failed (%s): %s", kind, one_line(reason))
    return path


async def report_backup_failure(kind, reason, folder="", output=""):
    """Write the failure log and post that reason in the log channel, not the warn channel."""

    log_path = backup_failure_log(kind, reason, folder, output)
    label = "Automatic backup failed" if kind == "auto" else "Manual backup failed"
    excerpt = _clip(reason or "failed", 900)
    embed = panel(
        label,
        [
            excerpt,
            f"Log: `{log_path}`",
            f"Folder: `{folder}`" if folder else "No backup folder was created.",
        ],
        COLOR_BAD,
        footer=log_path,
    )
    if not LOG_CHANNEL_ID:
        log.warning("Backup failure log not posted: MC_LOG_CHANNEL_ID is unset (%s)", log_path)
        return log_path
    try:
        channel = bot.get_channel(LOG_CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(LOG_CHANNEL_ID)
        await channel.send(embed=embed)
    except EDIT_ERRORS as error:
        log.error("Couldn't post backup failure to log channel %s: %s", LOG_CHANNEL_ID, error)
    return log_path


async def run_manual_backup():
    """Freeze if the server is up, copy, then turn autosave back on.

    Caller holds the backup lock. Returns (ok, detail, folder, elapsed).
    detail is a multi-line failure log when ok is False.
    """

    frozen = False
    started = time.monotonic()
    folder = ""
    try:
        if await server_running(force=True):
            frozen, output = await send_console("save-off")
            if frozen and console_reply_rejected(output):
                frozen = False
                log.warning("save-off was rejected: %s", one_line(output))
            if not frozen:
                reply = strip_colors(output or "") or "no console reply"
                return False, f"couldn't turn autosave off\n{reply}", "", time.monotonic() - started
            mark_autosave_off()
            if not await save_world():
                return False, "couldn't save the world: RCON and tmux both failed", "", time.monotonic() - started
        code, tail, folder = await perform_backup("manual")
        elapsed = time.monotonic() - started
        output = tail.decode(errors="ignore").strip()
        if code == 0:
            note_backup_success()
            await save_backup_state_async()  # why: note_backup_success no longer fsyncs on the loop
            await prune_backups()
            return True, "ok", folder, elapsed
        if code is None:
            reason = f"timed out after {BACKUP_TIMEOUT}s"
        else:
            reason = f"copy failed (exit {code})"
        if output:
            reason += "\n" + "\n".join(output.splitlines()[-12:])
        return False, reason, folder, elapsed
    except OSError as error:
        return False, f"{type(error).__name__}: {error}", folder, time.monotonic() - started
    finally:
        if frozen and not await restore_autosave():
            await send_alert(
                "[!] **Autosave may still be disabled** after a backup. "
                "`save-on` failed. Run it in the server console.",
                allow_mentions=bool(ALERT_MENTION),
            )


_chat_backup_last = -1e9  # monotonic time of the last in-game !backup


async def chat_backup_from(player):
    """Manual backup requested by a Minecraft chat message."""

    global _chat_backup_last
    log.info("Chat !backup from %s", player)
    if _stress_running:
        await say_game("backup is blocked during a stress test")
        return
    if not BACKUP_DIR:
        await say_game("backup is not configured")
        return
    wait = CHAT_BACKUP_COOLDOWN - (time.monotonic() - _chat_backup_last)
    if wait > 0:
        await say_game(f"backup was just run, try again in {int(wait) // 60 + 1} min")
        return
    if not try_lock("backup"):
        await say_game("backup already running")
        return
    _chat_backup_last = time.monotonic()
    await say_game("backup initiated")
    try:
        ok, detail, folder, elapsed = await run_manual_backup()
        if ok:
            await say_game(f"backup finished ({format_uptime(elapsed)})")
            await send_alert(
                embed=panel(
                    "Chat backup finished",
                    [f"{player} ran !backup", folder, f"Took {format_uptime(elapsed)}"],
                    COLOR_OK,
                )
            )
        else:
            await report_backup_failure("manual", detail or "failed", folder, detail)
            short = one_line(detail or "failed", 80)
            await say_game(f"backup failed: {short}")
    finally:
        release()


async def run_text_start(who, reply):
    """Start the server from a chat command. reply(text) reports progress."""

    if _stress_running:
        # why: snapshot and restore stop the server; a start then corrupts the world
        await reply("a stress test is running")
        return
    if not try_lock("start"):
        await reply("start already running")
        return
    try:
        if await server_running(force=True):
            await reply("server is already running")
            return
        await reply(f"{who} is starting the server")
        await cancel_idle_shutdown("!start")

        class ReplyStatus:
            """Helper that updates a Discord reply while an operation runs."""
            async def set(self, text, force=False):
                """Set."""
                await reply(text)

        if not await wait_until_fully_stopped(ReplyStatus()):
            await reply("the old server did not finish shutting down")
            return
        clear_controlled_stop()
        await close_wake_listener()
        await asyncio.to_thread(remove_legacy_dimension_folders)
        try:
            mark = os.path.getsize(LOG_PATH)
        except OSError:
            mark = 0
        try:
            await launch_server()
        except OSError as error:
            await reply(f"couldn't start the server: {error}")
            return
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            if await server_running(force=True) and b"Done (" in _log_from(LOG_PATH, mark):
                await reply("server is ready")
                return
            await asyncio.sleep(POLL_INTERVAL)
        await reply("server did not finish starting")
    finally:
        release()


def game_port():
    """Game port from server.properties, or 25565."""

    try:
        _, found, _encoding = props_load()
        raw = props_current(found, "server-port")
        return int(raw) if raw.isdigit() else 25565
    except (OSError, ValueError):
        return 25565


def _varint(value):
    """Internal: varint."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _mc_string(text):
    """Internal: mc string."""
    raw = text.encode("utf-8")
    return _varint(len(raw)) + raw


def _packet(packet_id, payload):
    """Internal: packet."""
    body = bytes([packet_id]) + payload
    return _varint(len(body)) + body


def offline_status_packet(protocol=777, name="26.3"):
    """Answer a server-list refresh without starting anything.

    Prefer the protocol from the client's handshake. A -1 protocol makes the
    client mark the server incompatible and it may never send the login packet.
    """

    body = json.dumps({
        "version": {"name": name, "protocol": protocol},
        "players": {"max": 20, "online": 0, "sample": []},
        "description": {"text": "Offline. Joining will start the server."},
    })
    return _packet(0x00, _mc_string(body))


def login_kick_packet(text):
    """Login disconnect. The client shows this on the join screen."""

    return _packet(0x00, _mc_string(json.dumps({"text": text})))


async def _read_varint(reader):
    """Internal: read varint."""
    value = 0
    for shift in range(0, 35, 7):
        raw = await reader.readexactly(1)
        byte = raw[0]
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value
    raise ValueError("bad varint")


async def handshake_intent(reader):
    """(raw bytes, intent). 1 is a server-list refresh. 2 or 3 is a real join."""

    length = await _read_varint(reader)
    if length < 2 or length > 2048:
        raise ValueError("handshake length")
    data = await reader.readexactly(length)
    raw = _varint(length) + data
    pos = 0

    def take():
        """Take."""
        nonlocal pos
        value = 0
        for shift in range(0, 35, 7):
            byte = data[pos]
            pos += 1
            value |= (byte & 0x7F) << shift
            if not byte & 0x80:
                return value
        raise ValueError("bad varint")

    if take() != 0:
        return raw, None, None
    protocol = take()
    size = take()
    pos += size  # server address
    pos += 2  # port
    return raw, take(), protocol


_wake_server = None
_wake_holds = 0


async def close_wake_listener():
    """Close wake listener."""
    global _wake_server
    server = _wake_server
    _wake_server = None
    if server is not None:
        server.close()
        await server.wait_closed()


async def _pipe(reader, writer):
    """Internal: pipe."""
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except asyncio.CancelledError:
        raise  # why: swallowing cancellation leaves the pipe task running
    except OSError:
        pass
    finally:
        try:
            writer.close()
        except OSError:
            pass


async def handle_wake(reader, writer):
    """Wake the server when a player tries to join while it is off."""
    peer = writer.get_extra_info("peername")
    who = peer[0] if peer else "unknown"
    try:
        raw, intent, protocol = await asyncio.wait_for(handshake_intent(reader), timeout=15)
    except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError, ValueError, IndexError) as error:
        log.warning("Wake: bad handshake from %s: %s", who, error)
        writer.close()
        return
    log.info("Wake: %s sent intent %s", who, intent)
    if intent not in (2, 3):
        try:
            # why: closing with the status request unread can RST the socket, so the MOTD never shows
            await asyncio.wait_for(reader.read(256), timeout=2)
            writer.write(offline_status_packet(protocol or 777))
            await writer.drain()
            ping = await asyncio.wait_for(reader.read(32), timeout=2)
            if ping:
                writer.write(ping)  # echo the ping so the client finishes the status exchange
                await writer.drain()
        except (OSError, asyncio.TimeoutError) as error:
            log.warning("Wake: status reply to %s failed: %s", who, error)
        writer.close()
        return
    log.info("Wake: login from %s, starting the server", who)
    global _wake_holds
    _wake_holds += 1  # why: increment before spawn so wake_on_ping_loop cannot see 0 and rebind
    spawn(hold_join(reader, writer, raw, who))


def _log_from(path, offset):
    """Bytes written after offset. A rotated log is read from the start."""

    try:
        with open(path, "rb") as file:
            file.seek(0, os.SEEK_END)
            if file.tell() < offset:
                offset = 0
            file.seek(offset)
            return file.read()
    except OSError:
        return b""


async def server_accepting(port):
    """Open a connection to the game port, or None if it is not up yet."""

    targets = ["127.0.0.1"]
    try:
        _, found, _encoding = props_load()
        bind = props_current(found, "server-ip").strip()
        if bind and bind not in targets:
            targets.append(bind)
    except OSError:
        pass
    for host in targets:
        try:
            return await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3)
        except (OSError, asyncio.TimeoutError):
            continue
    return None


async def hold_join(reader, writer, raw, who):
    """Keep the client on the connecting screen, then splice it to the real server.

    The client stays proxied through this bot for the session, so the server
    sees 127.0.0.1. An ip-ban on that address would block later wake joins.
    """

    global _wake_holds
    # why: handle_wake already incremented; this task only decrements in finally
    queue = asyncio.Queue()
    queue.put_nowait(raw)
    client_gone = False

    async def soak():
        """Soak."""
        nonlocal client_gone
        try:
            while True:
                data = await reader.read(65536)
                await queue.put(data or None)
                if not data:
                    client_gone = True
                    return
        except OSError:
            client_gone = True
            await queue.put(None)

    soaker = asyncio.create_task(soak())
    upstream = None
    try:
        ready = await wake_start(who)
        if client_gone:
            return
        if not ready:
            writer.write(login_kick_packet("server did not start"))
            await writer.drain()
            return
        port = game_port()
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline and not client_gone:
            upstream = await server_accepting(port)
            if upstream is not None:
                break
            await asyncio.sleep(0.5)
        if upstream is None:
            if not client_gone:
                writer.write(login_kick_packet("server did not open the port in time"))
                await writer.drain()
            return
        up_reader, up_writer = upstream

        async def client_to_server():
            """Client to server."""
            while True:
                item = await queue.get()
                if not item:
                    break
                up_writer.write(item)
                await up_writer.drain()
            up_writer.close()

        await asyncio.gather(
            client_to_server(),
            _pipe(up_reader, writer),
        )
    except (OSError, asyncio.CancelledError):
        pass
    finally:
        _wake_holds = max(0, _wake_holds - 1)
        soaker.cancel()
        try:
            await soaker
        except (asyncio.CancelledError, Exception):
            pass
        if upstream is not None:
            try:
                upstream[1].close()
            except OSError:
                pass
        try:
            writer.close()
        except OSError:
            pass


async def wake_start(who):
    """Free the port, then start. A second join waits for the start already running."""

    await close_wake_listener()
    notes = []

    async def reply(text):
        """Reply."""
        notes.append(text)
        # Do not wait on Discord. A slow or dead link must not stall the held join.
        spawn(send_alert(f"Join from `{who}`: {text}"))

    await run_text_start(f"join from {who}", reply)
    if any("server is ready" in note or "already running" in note for note in notes):
        return True
    if any("start already running" in note for note in notes):
        deadline = time.monotonic() + START_TIMEOUT
        while time.monotonic() < deadline:
            if await server_running(force=True):
                data = _read_tail(LOG_PATH, 64 * 1024) or b""
                if b"Done (" in data:
                    return True
            if current_op != "start" and not await server_running(force=True):
                return False
            await asyncio.sleep(POLL_INTERVAL)
    return False


async def wake_on_ping_loop():
    """Hold the game port while Minecraft is off. A join attempt starts it."""

    global _wake_server
    while True:
        try:
            if await server_running() or _wake_holds or _stress_running:
                # why: a join during snapshot/restore would launch Paper into a half-copied world
                await close_wake_listener()
                await asyncio.sleep(2)
                continue
            if _wake_server is None:
                port = game_port()
                _wake_server = await asyncio.start_server(
                    handle_wake, "0.0.0.0", port, reuse_address=True
                )
                log.info("Listening for a Minecraft join on 0.0.0.0:%s (held until the server is up)", port)
            await asyncio.sleep(2)
        except asyncio.CancelledError:
            await close_wake_listener()
            return
        except OSError as error:
            log.warning("Wake listener could not bind: %s", error)
            await asyncio.sleep(10)
        except Exception as error:
            log.warning("Wake listener error: %s", error)
            await asyncio.sleep(5)


async def chat_start(player):
    """In-game !start."""

    await run_text_start(player, say_game)


@bot.event
async def on_message(message):
    """Handle Discord messages (chat relay and in-game !commands)."""
    if (message.author.bot and message.webhook_id is None) or message.guild is None:
        return
    if GUILD_ID and message.guild.id != GUILD_ID:
        return
    if (message.content or "").strip().lower() != "!start":
        return
    who = message.author.display_name

    async def reply(text):
        """Reply."""
        await message.channel.send(text)

    await run_text_start(who, reply)


async def chat_tps():
    """In-game !tps. Says TPS and MSPT in Minecraft chat."""

    lines = await tps_mspt_lines()
    if all(line.endswith("unavailable") for line in lines):
        await say_game("couldn't read tps")
        return
    await say_game(" | ".join(lines))


async def chat_pingall():
    """In-game !pingall. Says each online player's ping in Minecraft chat."""

    if not try_lock("pingall"):
        await say_game("pingall already running")
        return
    try:
        lines = await player_ping_lines()
        if lines is None:
            await say_game("couldn't read pings")
            return
        await say_ping_lines(lines)
    finally:
        release()


async def chat_backup_loop():
    """Watch latest.log for `<player> !backup` and `!pingall`."""

    await bot.wait_until_ready()
    tail = MinecraftLogTail(LOG_PATH)
    while True:
        try:
            for kind, line in tail.poll():
                if kind != "line":
                    continue
                player, message = chat_player_message(line)
                if player and is_backup_chat(message):
                    spawn(chat_backup_from(player))
                elif player and message.split()[0].lower() == "!pingall":
                    spawn(chat_pingall())
                elif player and message.split()[0].lower() == "!tps":
                    spawn(chat_tps())
                elif player and message.split()[0].lower() == "!start":
                    spawn(chat_start(player))
                if _stress_running and "joined the game" in line:
                    spawn(stress_warn())
        except Exception:
            log.exception("Chat backup watch failed")
        await asyncio.sleep(LOG_TAIL_INTERVAL)


BACKUP_FOLDER_RE = re.compile(r"^(?:auto|manual)backup \((\d+)\) ")


def backup_complete(path):
    """A finished backup has its manifest and no failure log."""

    return os.path.isfile(os.path.join(path, "backup.txt")) and not os.path.exists(
        os.path.join(path, "failed.log")
    )


def prune_old_backups():
    """Blocking. Delete finished backups beyond MC_BACKUP_KEEP, per kind. Returns names."""

    if not BACKUP_DIR or BACKUP_KEEP <= 0 or not os.path.isdir(BACKUP_DIR):
        return []
    groups = {"auto": [], "manual": []}
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        if not BACKUP_FOLDER_RE.match(name) or not os.path.isdir(path):
            continue
        if not backup_complete(path):
            continue  # failed or half-written: leave for /backup list to show
        if os.path.isfile(os.path.join(path, ".keep")):
            continue  # pinned from /backup list
        kind = "auto" if name.startswith("autobackup") else "manual"
        groups[kind].append((os.path.getmtime(path), name, path))
    removed = []
    for items in groups.values():
        items.sort(reverse=True)
        for _mtime, name, path in items[BACKUP_KEEP:]:
            try:
                shutil.rmtree(path)
                removed.append(name)
            except OSError as error:
                log.warning("Couldn't delete old backup %s: %s", name, error)
    return removed


async def prune_backups():
    """Retention after a successful backup. Never lets a prune problem fail the backup."""

    try:
        removed = await asyncio.to_thread(prune_old_backups)
    except Exception:
        log.exception("Backup retention failed")
        return
    for name in removed:
        log.info("Deleted old backup %s (keeping %s per kind)", name, BACKUP_KEEP)


def recent_backups(limit=5, complete_only=True):
    """Newest backup folders, each (serial, number, name, path).

    Half-written or failed backups are left out unless complete_only is False
    (so /backup list can still show them for deleting, but restore never offers them).
    """

    if not BACKUP_DIR or not os.path.isdir(BACKUP_DIR):
        return []
    found = []
    for name in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, name)
        if not os.path.isdir(path) or not BACKUP_FOLDER_RE.match(name):
            continue
        if complete_only and not backup_complete(path):
            continue
        number = int(BACKUP_FOLDER_RE.match(name).group(1))
        found.append((os.path.getmtime(path), number, name, path))
    found.sort(reverse=True)
    return [
        (index, number, name, path)
        for index, (_mtime, number, name, path) in enumerate(found[:limit], start=1)
    ]


# Backed up next to the worlds but never restored: a restore must not roll back
# plugins, configs or server.properties (RCON settings live there).
RESTORE_SKIP = frozenset(BACKUP_DIRS) | frozenset(BACKUP_FILES) | {"backup.txt", "failed.log"}
LEGACY_DIM_FOLDERS = frozenset({"world_nether", "world_the_end"})


def backup_uses_nested_dims(folder):
    """True if this backup stores Nether/End inside world/dimensions."""

    nested = os.path.join(folder, "world", "dimensions", "minecraft")
    return (
        os.path.isdir(os.path.join(nested, "the_nether"))
        or os.path.isdir(os.path.join(nested, "the_end"))
    )


def restore_backup_folder(folder):
    """Replace the live worlds with one backup. Caller must stop the server first.

    Only world folders are restored. Each live folder is renamed aside first
    (`*.before-restore`, or with a timestamp if that name is taken), and if
    anything fails the renames are undone, so a failed restore leaves the old
    worlds in place instead of a half-restored mix.
    """

    root = server_root()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    skip = set(RESTORE_SKIP)
    if backup_uses_nested_dims(folder):
        # why: nested backup already has nether/end inside world/; restoring world_nether would duplicate. Old layout must restore them or the dimensions stay at the live state.
        skip |= LEGACY_DIM_FOLDERS
    names = [
        name
        for name in sorted(os.listdir(folder))
        if name not in skip and os.path.isdir(os.path.join(folder, name))
    ]
    if not names:
        raise OSError("this backup contains no world folders")

    moved = []    # (live path, where the old copy was put)
    created = []  # live paths filled from the backup
    try:
        for name in names:
            dest = os.path.join(root, name)
            if os.path.lexists(dest):
                aside = dest + ".before-restore"
                suffix = 0
                while os.path.lexists(aside):
                    suffix += 1
                    aside = f"{dest}.before-restore-{stamp}-{suffix}"
                os.rename(dest, aside)
                moved.append((dest, aside))
            created.append(dest)
            shutil.copytree(os.path.join(folder, name), dest)
        # Copy succeeded. Keep the *.before-restore asides as a safety net.
        # Do not delete them here.
    except Exception:
        for path in reversed(created):
            shutil.rmtree(path, ignore_errors=True)
        for dest, aside in reversed(moved):
            try:
                os.rename(aside, dest)
            except OSError:
                log.error("Restore rollback: couldn't move %s back to %s", aside, dest)
        raise
    # Cleanup of leftover .old / .old-layout folders happens after a successful
    # restore, outside the try, so a late failure cannot destroy both copies.
    try:
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if is_stale_world_name(name) and os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                log.info("Removed leftover world folder %s", name)
        remove_legacy_dimension_folders()
    except Exception:
        log.exception("Post-restore cleanup failed (worlds were still restored)")
    return list(names)


class RestoreView(discord.ui.View):
    """Discord view for choosing a backup to restore."""
    def __init__(self, user_id, choices):
        """Internal: init."""
        super().__init__(timeout=120)
        self.user_id = user_id
        self.choices = {str(serial): (name, path) for serial, _number, name, path in choices}
        options = [
            discord.SelectOption(
                label=f"{serial}. {name}"[:100],
                value=str(serial),
                description=f"backup number {number}"[:100],
            )
            for serial, number, name, _path in choices
        ]
        self.add_item(RestoreSelect(options))

    async def interaction_check(self, interaction):
        """Interaction check."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the person who ran /backup can choose.", ephemeral=False
            )
            return False
        return await gate(interaction, admin=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, row=2)
    async def close(self, interaction, button):
        """Close."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the person who ran /backup can close this.", ephemeral=False
            )
            return
        self.stop()
        await interaction.response.edit_message(content="Backup list closed.", embed=None, view=None)


class RestoreSelect(discord.ui.Select):
    """Select menu of available backups for restore."""
    def __init__(self, options):
        """Internal: init."""
        super().__init__(placeholder="Choose a backup to restore", options=options)

    async def callback(self, interaction):
        """Callback."""
        serial = self.values[0]
        name, path = self.view.choices[serial]
        if await server_running():
            await interaction.response.send_message(
                "[!] Stop the server with `/stop` before restoring. Nothing was changed.",
                ephemeral=False,
            )
            return
        if not try_lock("restore"):
            await interaction.response.send_message(
                f"Busy: `/{current_op}` is still in progress.", ephemeral=False
            )
            return
        try:
            await interaction.response.defer()
            copied = await asyncio.to_thread(restore_backup_folder, path)
        except OSError as error:
            await interaction.followup.send(f"[!] Restore failed: `{error}`")
            return
        finally:
            release()
        self.view.stop()
        await interaction.edit_original_response(
            content=(
                f"**Restored backup {serial}.** `{name}`\n"
                f"Replaced: {', '.join(copied) or 'nothing'}\n"
                "Old worlds were renamed `*.before-restore` (with a timestamp if that "
                "name was taken). Plugins and config were not touched. Start the server when ready."
            ),
            embed=None,
            view=None,
        )


class DeleteView(discord.ui.View):
    """Discord view for choosing a backup to delete."""
    def __init__(self, user_id, choices):
        """Internal: init."""
        super().__init__(timeout=120)
        self.user_id = user_id
        self.choices = {str(serial): (name, path) for serial, _number, name, path in choices}
        options = [
            discord.SelectOption(
                label=f"{serial}. {name}"[:100],
                value=str(serial),
                description="delete this backup"[:100],
            )
            for serial, _number, name, _path in choices
        ]
        self.add_item(DeleteSelect(options))

    async def interaction_check(self, interaction):
        """Interaction check."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the person who ran /backup can delete.", ephemeral=False
            )
            return False
        return await gate(interaction, admin=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, row=2)
    async def close(self, interaction, button):
        """Close."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the person who ran /backup can close this.", ephemeral=False
            )
            return
        self.stop()
        await interaction.response.edit_message(content="Backup list closed.", embed=None, view=None)


class KeepSelect(discord.ui.Select):
    """Select menu to mark a backup as kept (skip auto-delete)."""
    def __init__(self, options):
        """Internal: init."""
        super().__init__(placeholder="Keep a backup from auto-delete", options=options)

    async def callback(self, interaction):
        """Callback."""
        serial = self.values[0]
        name, path = self.view.choices[serial]
        marker = os.path.join(path, ".keep")
        try:
            if os.path.isfile(marker):
                os.remove(marker)
                state = "will be auto-deleted again"
            else:
                with open(marker, "w", encoding="utf-8") as file:
                    file.write("kept\n")
                state = "excluded from auto-delete"
        except OSError as error:
            await interaction.response.send_message(
                f"[!] Couldn't update `{name}`: `{error}`", ephemeral=False
            )
            return
        self.view.stop()
        await interaction.response.edit_message(
            content=f"**Backup {serial}** `{name}` {state}.",
            embed=None,
            view=None,
        )


class DeleteSelect(discord.ui.Select):
    """Select menu of backups that can be deleted."""
    def __init__(self, options):
        """Internal: init."""
        super().__init__(placeholder="Delete a backup", options=options)

    async def callback(self, interaction):
        """Callback."""
        serial = self.values[0]
        name, path = self.view.choices[serial]
        if not try_lock("backup-delete"):
            await interaction.response.send_message(
                f"Busy: `/{current_op}` is still in progress.", ephemeral=False
            )
            return
        try:
            await interaction.response.defer()
            await asyncio.to_thread(shutil.rmtree, path)
        except OSError as error:
            await interaction.followup.send(f"[!] Couldn't delete `{name}`: `{error}`")
            return
        finally:
            release()
        self.view.stop()
        await interaction.edit_original_response(
            content=f"**Deleted backup {serial}.** `{name}`",
            embed=None,
            view=None,
        )



@bot.tree.command(name="backup", description="Make, list, or restore a world backup")
@app_commands.describe(action="make a new backup, or (admin role) list or restore them")
@app_commands.choices(action=[
    app_commands.Choice(name="make", value="make"),
    app_commands.Choice(name="list", value="list"),
    app_commands.Choice(name="restore", value="restore"),
])
async def backup(interaction: discord.Interaction, action: str):
    """Slash command: make, list, restore, or delete backups."""
    if not await gate(interaction):
        return
    # make is open to members; looking at or restoring backups is admin only.
    if action in ("list", "restore") and not await gate(interaction, admin=True):
        return
    if _stress_running:
        await deny(interaction, "Backup is blocked during a stress test.")
        return
    if not BACKUP_DIR:
        await deny(
            interaction,
            "**Backup isn't configured yet.**\n"
            "Set `MC_BACKUP_DIR` to the folder that should hold backups.",
        )
        return

    if action == "list":
        rows = recent_backups(15, complete_only=False)
        if not rows:
            await deny(interaction, "No backups yet.")
            return
        lines = []
        for serial, _number, name, path in rows:
            flags = []
            if not backup_complete(path):
                flags.append("incomplete")
            if os.path.isfile(os.path.join(path, ".keep")):
                flags.append("kept")
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"{serial}. `{name}`{suffix}  {format_bytes(folder_size(path))}")
        view = DeleteView(interaction.user.id, rows)
        view.add_item(KeepSelect([
            discord.SelectOption(
                label=f"{serial}. {name}"[:100],
                value=str(serial),
                description="exclude from auto-delete"[:100],
            )
            for serial, _number, name, _path in rows
        ]))
        await interaction.response.send_message(
            embed=panel("Backups", lines, COLOR_INFO),
            view=view,
        )
        return

    if action == "restore":
        rows = recent_backups(5)
        if not rows:
            await deny(interaction, "No backups to restore.")
            return
        if await server_running():
            await deny(interaction, "[!] Stop the server with `/stop` before restoring.")
            return
        lines = [f"{serial}. `{name}`" for serial, _number, name, _path in rows]
        view = RestoreView(interaction.user.id, rows)
        await interaction.response.send_message(
            embed=panel("Restore a backup", lines, COLOR_WAIT),
            view=view,
        )
        return

    if not await begin(interaction, "backup"):
        return
    msg = None
    final_text = ""
    try:
        msg = await open_status(interaction, "Saving the world, then copying the backup...")
        ok, detail, folder, elapsed = await run_manual_backup()
        if ok:
            size = await asyncio.to_thread(folder_size, folder) if folder else 0
            final_text = (
                "**Backup finished.** "
                f"`{folder}`\nSize: {format_bytes(size)}. Took {format_uptime(elapsed)}. "
                "The uptime and playtime counters were reset."
            )
        else:
            log_path = await report_backup_failure("manual", detail or "failed", folder, detail)
            final_text = (
                "[!] **Backup failed.** Posted in the log channel.\n"
                f"Log: `{log_path}`\n"
                f"```\n{_clip(detail or 'failed', 900)}\n```"
            )
        await msg.set(final_text, force=True)
    finally:
        release()



# ============================================================
# /MAP  (on demand only; nothing stays loaded)
# ============================================================
#
# Reads the overworld's region files (.mca) directly: no plugin, no extra
# packages. Per chunk it takes the top block that stops movement or holds fluid
# (the MOTION_BLOCKING heightmap, so grass and flowers are looked through),
# colours it, darkens water by depth, and shades land by comparing each column's
# height with the one to its north, like the vanilla map item. Biome tints are
# not applied, so all grass is the same green.

MAP_MAX = 512
MAP_DEFAULT = 256
NO_DATA = (24, 24, 24)  # chunk not generated, unfinished or unreadable
_map_running = False


def _read_payload(data, kind, pos):
    """Internal: read payload."""
    if kind == 1:
        return int.from_bytes(data[pos:pos + 1], "big", signed=True), pos + 1
    if kind == 2:
        return int.from_bytes(data[pos:pos + 2], "big", signed=True), pos + 2
    if kind == 3:
        return int.from_bytes(data[pos:pos + 4], "big", signed=True), pos + 4
    if kind == 4:
        return int.from_bytes(data[pos:pos + 8], "big", signed=True), pos + 8
    if kind == 5:
        return data[pos:pos + 4], pos + 4
    if kind == 6:
        return data[pos:pos + 8], pos + 8
    if kind == 7:
        n = int.from_bytes(data[pos:pos + 4], "big")
        return data[pos + 4:pos + 4 + n], pos + 4 + n
    if kind == 8:
        n = int.from_bytes(data[pos:pos + 2], "big")
        return data[pos + 2:pos + 2 + n].decode("utf-8", "replace"), pos + 2 + n
    if kind == 9:
        inner = data[pos]
        n = int.from_bytes(data[pos + 1:pos + 5], "big")
        pos += 5
        items = []
        for _ in range(n):
            value, pos = _read_payload(data, inner, pos)
            items.append(value)
        return items, pos
    if kind == 10:
        out = {}
        while data[pos] != 0:
            child_kind = data[pos]
            name_len = int.from_bytes(data[pos + 1:pos + 3], "big")
            name = data[pos + 3:pos + 3 + name_len].decode("utf-8", "replace")
            value, pos = _read_payload(data, child_kind, pos + 3 + name_len)
            out[name] = value
        return out, pos + 1
    if kind == 11:
        n = int.from_bytes(data[pos:pos + 4], "big")
        pos += 4
        return [int.from_bytes(data[pos + i * 4:pos + i * 4 + 4], "big", signed=True) for i in range(n)], pos + n * 4
    if kind == 12:
        n = int.from_bytes(data[pos:pos + 4], "big")
        pos += 4
        return [int.from_bytes(data[pos + i * 8:pos + i * 8 + 8], "big", signed=True) for i in range(n)], pos + n * 8
    raise ValueError(f"bad nbt type {kind}")


def read_nbt(data):
    """Read an NBT compound."""
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    kind = data[0]
    name_len = int.from_bytes(data[1:3], "big")
    value, _pos = _read_payload(data, kind, 3 + name_len)
    return value


def world_spawn(level_dat):
    """(x, z) of world spawn. Newer levels keep a `spawn` compound, older ones SpawnX/SpawnZ."""

    with open(level_dat, "rb") as file:
        data = read_nbt(file.read())
    body = data.get("Data", data)
    spawn = body.get("spawn")
    if isinstance(spawn, dict):
        pos = spawn.get("pos")
        if isinstance(pos, list) and len(pos) >= 3:
            return int(pos[0]), int(pos[2])
    return int(body.get("SpawnX", 0)), int(body.get("SpawnZ", 0))


def default_center():
    """Return the default map center (spawn)."""
    return world_spawn(os.path.join(world_dir(), "level.dat"))


def overworld_region_dir():
    """(region folder, world folder). The folder is None if no .mca files exist."""

    base = world_dir()
    for candidate in (
        os.path.join(base, "dimensions", "minecraft", "overworld", "region"),
        os.path.join(base, "region"),
    ):
        if os.path.isdir(candidate) and any(n.endswith(".mca") for n in os.listdir(candidate)):
            return candidate, base
    return None, base


def _unpack(longs, count, bits):
    """`count` values of `bits` bits. Since 1.16 a value never straddles two longs."""

    per_long = 64 // bits
    mask = (1 << bits) - 1
    out = []
    for index in range(count):
        word = index // per_long
        if word >= len(longs):
            out.append(0)
        else:
            out.append((longs[word] >> (index % per_long * bits)) & mask)
    return out


def _heightmap(longs):
    """256 column heights (relative to the world bottom), or None if there are none."""

    if not longs:
        return None
    for bits in range(4, 12):
        if -(-256 // (64 // bits)) == len(longs):
            return _unpack(longs, 256, bits)
    raise ValueError(f"unrecognised heightmap size {len(longs)}")


def read_chunk(file, index):
    """Chunk NBT from an open region file, or None if that chunk was never generated."""

    file.seek(index * 4)
    entry = int.from_bytes(file.read(4), "big")
    if entry == 0:
        return None
    file.seek((entry >> 8) * 4096)
    length = int.from_bytes(file.read(4), "big")
    method = file.read(1)[0]
    blob = file.read(max(0, length - 1))
    if method == 2:
        blob = zlib.decompress(blob)
    elif method == 1:
        blob = gzip.decompress(blob)
    elif method != 3:
        raise ValueError(f"unsupported chunk compression {method}")
    return read_nbt(blob)


WATER = (40, 90, 180)
WATER_BLOCKS = frozenset({
    "minecraft:water", "minecraft:bubble_column", "minecraft:seagrass",
    "minecraft:tall_seagrass", "minecraft:kelp", "minecraft:kelp_plant",
})
# Blocks the map looks through if a heightmap happened to land on them.
SEE_THROUGH = frozenset({
    "minecraft:air", "minecraft:cave_air", "minecraft:void_air", "minecraft:short_grass",
    "minecraft:grass", "minecraft:tall_grass", "minecraft:fern", "minecraft:large_fern",
    "minecraft:dead_bush", "minecraft:vine", "minecraft:poppy", "minecraft:dandelion",
    "minecraft:torch", "minecraft:light",
})
BLOCK_COLORS = {
    "minecraft:grass_block": (90, 160, 60),
    "minecraft:dirt": (134, 96, 67),
    "minecraft:coarse_dirt": (120, 85, 58),
    "minecraft:rooted_dirt": (125, 90, 62),
    "minecraft:stone": (125, 125, 125),
    "minecraft:cobblestone": (110, 110, 110),
    "minecraft:mossy_cobblestone": (90, 115, 80),
    "minecraft:oak_leaves": (50, 120, 40),
    "minecraft:spruce_leaves": (40, 90, 40),
    "minecraft:birch_leaves": (120, 160, 70),
    "minecraft:jungle_leaves": (40, 130, 30),
    "minecraft:acacia_leaves": (90, 140, 40),
    "minecraft:dark_oak_leaves": (35, 80, 25),
    "minecraft:cherry_leaves": (230, 160, 180),
    "minecraft:mangrove_leaves": (70, 130, 50),
    "minecraft:azalea_leaves": (70, 140, 55),
    "minecraft:snow": (240, 245, 250),
    "minecraft:snow_block": (240, 245, 250),
    "minecraft:sand": (220, 210, 160),
    "minecraft:red_sand": (190, 100, 50),
    "minecraft:gravel": (140, 140, 140),
    "minecraft:lava": (200, 70, 20),
    "minecraft:oak_log": (150, 120, 70),
    "minecraft:spruce_log": (90, 70, 45),
    "minecraft:birch_log": (210, 200, 170),
    "minecraft:jungle_log": (140, 100, 55),
    "minecraft:acacia_log": (170, 90, 50),
    "minecraft:dark_oak_log": (70, 50, 30),
    "minecraft:cherry_log": (210, 160, 150),
    "minecraft:mangrove_log": (110, 60, 50),
    "minecraft:gold_ore": (220, 180, 50),
    "minecraft:iron_ore": (180, 150, 130),
    "minecraft:diamond_ore": (80, 220, 210),
    "minecraft:emerald_ore": (40, 180, 80),
    "minecraft:coal_ore": (60, 60, 60),
    "minecraft:redstone_ore": (160, 40, 40),
    "minecraft:lapis_ore": (40, 70, 170),
    "minecraft:copper_ore": (190, 110, 80),
    "minecraft:amethyst_block": (160, 100, 200),
    "minecraft:obsidian": (20, 15, 30),
    "minecraft:bedrock": (40, 40, 40),
    "minecraft:netherrack": (110, 50, 50),
    "minecraft:end_stone": (220, 220, 170),
    "minecraft:prismarine": (90, 160, 150),
    "minecraft:sea_lantern": (180, 220, 210),
    "minecraft:honey_block": (230, 170, 30),
    "minecraft:slime_block": (120, 200, 80),
    "minecraft:moss_block": (90, 140, 50),
    "minecraft:mycelium": (110, 95, 110),
    "minecraft:podzol": (100, 70, 40),
    "minecraft:mud": (60, 50, 45),
    "minecraft:clay": (160, 165, 175),
    "minecraft:path": (150, 120, 80),
    "minecraft:farmland": (110, 75, 50),
    "minecraft:deepslate": (80, 80, 85),
    "minecraft:tuff": (108, 109, 102),
    "minecraft:calcite": (223, 224, 220),
    "minecraft:dripstone_block": (134, 107, 92),
    "minecraft:moss_carpet": (90, 140, 50),
    "minecraft:mud_bricks": (140, 105, 80),
    "minecraft:bamboo_block": (130, 145, 55),
    "minecraft:copper_block": (190, 105, 75),
    "minecraft:exposed_copper": (160, 125, 100),
    "minecraft:oxidized_copper": (90, 150, 120),
}
# Checked in order against the name without "minecraft:"; first match wins.
BLOCK_KEYWORDS = (
    ("red_sand", (190, 100, 50)), ("sand", (220, 210, 160)),
    ("snow", (240, 245, 250)), ("ice", (160, 200, 230)),
    ("leaves", (55, 125, 45)), ("moss", (90, 110, 50)), ("grass", (90, 160, 60)),
    ("podzol", (100, 70, 40)), ("mycelium", (110, 95, 110)), ("mud", (90, 70, 60)),
    ("dirt", (134, 96, 67)), ("farmland", (110, 75, 50)),
    ("gravel", (140, 140, 140)), ("clay", (160, 165, 175)), ("terracotta", (160, 100, 70)),
    ("planks", (160, 130, 80)), ("log", (100, 80, 50)), ("wood", (100, 80, 50)),
    ("glass", (170, 200, 210)), ("brick", (150, 90, 80)),
    ("netherrack", (110, 50, 50)), ("crimson", (130, 40, 50)), ("warped", (40, 110, 110)),
    ("basalt", (70, 70, 75)), ("blackstone", (45, 40, 50)), ("obsidian", (20, 15, 30)),
    ("end_stone", (220, 220, 170)), ("deepslate", (80, 80, 85)),
    ("granite", (150, 105, 90)), ("tuff", (100, 100, 90)), ("calcite", (225, 225, 220)),
    ("stone", (125, 125, 125)), ("andesite", (135, 135, 135)), ("diorite", (190, 190, 190)),
    ("ore", (125, 125, 125)), ("copper", (190, 110, 80)),
    ("water", WATER), ("lava", (200, 70, 20)), ("magma", (150, 60, 20)),
)
DYE_COLORS = {
    "white": (230, 230, 230), "orange": (220, 120, 30), "magenta": (190, 70, 180),
    "light_blue": (80, 150, 210), "yellow": (230, 200, 50), "lime": (110, 190, 40),
    "pink": (230, 140, 170), "gray": (70, 70, 75), "light_gray": (150, 150, 145),
    "cyan": (30, 130, 140), "purple": (130, 50, 170), "blue": (50, 60, 160),
    "brown": (110, 70, 40), "green": (80, 110, 40), "red": (170, 45, 40), "black": (25, 25, 30),
}
DYED_SUFFIXES = (
    "_concrete_powder", "_concrete", "_glazed_terracotta", "_terracotta", "_wool",
    "_carpet", "_stained_glass_pane", "_stained_glass",
)


def block_color(name):
    """RGB for a block name, or None if the map should look through it. Unknown blocks are grey."""

    if name in SEE_THROUGH or name.endswith(("_air", "_sapling", "_tulip")):
        return None
    if name in BLOCK_COLORS:
        return BLOCK_COLORS[name]
    short = name.split(":", 1)[-1]
    for suffix in DYED_SUFFIXES:
        if short.endswith(suffix) and short[: -len(suffix)] in DYE_COLORS:
            return DYE_COLORS[short[: -len(suffix)]]
    for word, color in BLOCK_KEYWORDS:
        if word in short:
            return color
    value = sum(ord(ch) for ch in short)
    return (80 + value % 140, 80 + (value // 3) % 140, 80 + (value // 7) % 140)


# Java grass colors from the Minecraft wiki. First matching word wins, so
# dark_forest is before forest and snow is before taiga.
GRASS_COLORS = (
    ("dark_forest", (0x50, 0x7A, 0x32)),
    ("swamp", (0x6A, 0x70, 0x39)),
    ("mangrove", (0x6A, 0x70, 0x39)),
    ("badlands", (0x90, 0x81, 0x4D)),
    ("wooded_badlands", (0x90, 0x81, 0x4D)),
    ("desert", (0xBF, 0xB7, 0x55)),
    ("savanna", (0xBF, 0xB7, 0x55)),
    ("sparse_jungle", (0x64, 0xC7, 0x3F)),
    ("jungle", (0x59, 0xC9, 0x3C)),
    ("cherry", (0xB6, 0xDB, 0x61)),
    ("snow", (0x80, 0xB4, 0x97)),
    ("frozen", (0x80, 0xB4, 0x97)),
    ("ice_spikes", (0x80, 0xB4, 0x97)),
    ("taiga", (0x86, 0xB7, 0x83)),
    ("old_growth_pine", (0x86, 0xB7, 0x83)),
    ("old_growth_spruce", (0x86, 0xB7, 0x83)),
    ("forest", (0x79, 0xC0, 0x5A)),
    ("flower_forest", (0x79, 0xC0, 0x5A)),
    ("birch", (0x88, 0xBB, 0x67)),
    ("meadow", (0x83, 0xBB, 0x6D)),
    ("mushroom", (0x55, 0xC9, 0x3F)),
    ("stony_peaks", (0x9A, 0xBE, 0x4B)),
    ("plains", (0x91, 0xBD, 0x59)),
    ("sunflower", (0x91, 0xBD, 0x59)),
    ("beach", (0x91, 0xBD, 0x59)),
    ("river", (0x91, 0xBD, 0x59)),
    ("ocean", (0x8E, 0xB9, 0x71)),
)
FOLIAGE_COLORS = (
    ("dark_forest", (0x3A, 0x5A, 0x24)),
    ("swamp", (0x6A, 0x70, 0x39)),
    ("mangrove", (0x6A, 0x70, 0x39)),
    ("jungle", (0x30, 0xBB, 0x0B)),
    ("sparse_jungle", (0x3E, 0xB8, 0x0F)),
    ("savanna", (0xAE, 0xA4, 0x2A)),
    ("badlands", (0x9E, 0x81, 0x42)),
    ("desert", (0xAE, 0xA4, 0x2A)),
    ("snow", (0x60, 0xA1, 0x7B)),
    ("frozen", (0x60, 0xA1, 0x7B)),
    ("taiga", (0x68, 0xA4, 0x64)),
    ("forest", (0x59, 0xAE, 0x30)),
    ("plains", (0x77, 0xAB, 0x2F)),
)
WATER_COLORS = (
    ("swamp", (0x61, 0x7B, 0x64)),
    ("mangrove", (0x61, 0x7B, 0x64)),
    ("warm_ocean", (0x43, 0xD5, 0xEE)),
    ("lukewarm", (0x45, 0xAD, 0xF2)),
    ("frozen", (0x39, 0x38, 0xC9)),
    ("cold", (0x3D, 0x57, 0xD6)),
    ("ocean", (0x3F, 0x76, 0xE4)),
    ("river", (0x3F, 0x76, 0xE4)),
)
FIXED_LEAVES = ("birch", "spruce", "cherry", "azalea")
MAP_STYLE = 5


def _biome_pick(table, key, default):
    """Internal: biome pick."""
    for word, color in table:
        if word in key:
            return color
    return default


def tint(color, biome, name):
    """Vanilla biome colors for grass, tinted leaves, and water."""

    if not biome:
        return color
    key = biome.split(":")[-1]
    short = name.split(":")[-1]
    if "water" in short or short in ("seagrass", "tall_seagrass", "kelp", "kelp_plant", "bubble_column"):
        return _biome_pick(WATER_COLORS, key, WATER)
    if "grass" in short:
        return _biome_pick(GRASS_COLORS, key, color)
    if "leaves" in short and not any(word in short for word in FIXED_LEAVES):
        return _biome_pick(FOLIAGE_COLORS, key, color)
    return color


def palette_name(entry):
    """Block id from a palette entry. 26.x stores default states as plain strings."""

    if isinstance(entry, str) and entry:
        return entry
    if isinstance(entry, dict):
        return entry.get("Name") or entry.get("") or entry.get("id") or "minecraft:air"
    return "minecraft:air"


def chunk_columns(root, dimension="overworld"):
    """(colors, heights, water) for the 256 columns of a finished chunk, else None.

    Raises ValueError for a finished chunk with no usable heightmap (counted as unreadable).
    """

    status = str(root.get("Status") or root.get("status") or "full")
    if not status.endswith("full") and not (root.get("sections") or root.get("Sections")):
        return None
    maps = root.get("Heightmaps") or root.get("heightmaps") or {}
    top = _heightmap(maps.get("MOTION_BLOCKING") or maps.get("WORLD_SURFACE") or [])
    if top is None and dimension != "nether":
        raise ValueError("chunk has no heightmap")
    floor = _heightmap(maps.get("OCEAN_FLOOR") or [])
    # yPos is the lowest section index (-4), except when a version stores the block Y.
    raw_y = int(root.get("yPos", root.get("ypos", -4)))
    min_y = raw_y * 16 if -16 < raw_y < 16 else raw_y

    sections, biomes = {}, {}
    for section in root.get("sections") or root.get("Sections") or []:
        if not isinstance(section, dict) or "Y" not in section:
            continue
        states = section.get("block_states") or {}
        names = [palette_name(entry) for entry in states.get("palette") or []]
        sections[section["Y"]] = (names, states.get("data") or [])
        raw = section.get("biomes") or {}
        palette = raw.get("palette") or []
        bnames = []
        for entry in palette:
            if isinstance(entry, str):
                bnames.append(entry)
            elif isinstance(entry, dict):
                bnames.append(entry.get("Name") or "minecraft:plains")
        biomes[section["Y"]] = (bnames, raw.get("data") or [])

    def block_at(local, y):
        """Block at."""
        names, data = sections.get(y >> 4, ((), ()))
        if not names:
            return "minecraft:air"
        if len(names) == 1 or not data:
            return names[0]
        bits = max(4, (len(names) - 1).bit_length())
        per_long = 64 // bits
        index = ((y & 15) << 8) | local
        word = index // per_long
        if word >= len(data):
            return names[0]
        value = (data[word] >> (index % per_long * bits)) & ((1 << bits) - 1)
        return names[value] if value < len(names) else names[0]

    def biome_at(local, y):
        """Biome at."""
        names, data = biomes.get(y >> 4, ((), ()))
        if not names:
            return ""
        if len(names) == 1 or not data:
            return names[0]
        bits = max(1, (len(names) - 1).bit_length())
        per_long = 64 // bits
        index = ((y & 15) >> 2) * 16 + ((local >> 4) >> 2) * 4 + ((local & 15) >> 2)
        word = index // per_long
        if word >= len(data):
            return names[0]
        value = (data[word] >> (index % per_long * bits)) & ((1 << bits) - 1)
        return names[value] if value < len(names) else names[0]

    colors, heights, water = [], [], bytearray(256)
    for local in range(256):
        if dimension == "nether":
            y = 120
            color = None
            while y > 0:
                name = block_at(local, y)
                if name in ("minecraft:bedrock",) or name in SEE_THROUGH:
                    y -= 1
                    continue
                color = block_color(name)
                if color is not None:
                    break
                y -= 1
            colors.append(color or NO_DATA)
            heights.append(y)
            continue
        y = min_y + top[local] - 1
        color = None
        name = "minecraft:air"
        starts = [y]
        if sections:
            starts.append(max(sections) * 16 + 15)
        for start in starts:
            y = start
            found = False
            for _ in range(64):
                name = block_at(local, y)
                if name in WATER_BLOCKS:
                    depth = max(1, (top[local] - floor[local]) if floor else 6)
                    floor_color = None
                    look = y - 1
                    for _down in range(min(48, depth + 4)):
                        below = block_at(local, look)
                        if below not in WATER_BLOCKS:
                            floor_color = block_color(below)
                            if floor_color is not None:
                                break
                        look -= 1
                    water_color = tint(WATER, biome_at(local, y), name)
                    if floor_color is None:
                        floor_color = water_color
                    mix = min(0.9, 0.35 + depth * 0.05)
                    color = tuple(
                        int(w * mix + f * (1 - mix)) for w, f in zip(water_color, floor_color)
                    )
                    water[local] = 1
                    found = True
                    break
                color = block_color(name)
                if color is not None:
                    found = True
                    break
                y -= 1
            if found:
                break
        if color is not None and dimension == "overworld" and name not in WATER_BLOCKS:
            color = tint(color, biome_at(local, y), name)
        colors.append(color or NO_DATA)
        heights.append(y)
    return colors, heights, water


def png_bytes(width, height, rgb):
    """Encode raw RGB pixels as PNG bytes."""
    def chunk(tag, payload):
        """Chunk."""
        crc = zlib.crc32(tag + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", crc)

    stride = width * 3
    raw = b"".join(b"\x00" + bytes(rgb[y * stride:(y + 1) * stride]) for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def region_dir_for(dimension):
    """Return the region directory for a dimension, or None."""
    base = world_dir()
    folders = {
        "overworld": (
            os.path.join(base, "dimensions", "minecraft", "overworld", "region"),
            os.path.join(base, "region"),
        ),
        "nether": (
            os.path.join(base, "dimensions", "minecraft", "the_nether", "region"),
            os.path.join(base, "DIM-1", "region"),
        ),
        "end": (
            os.path.join(base, "dimensions", "minecraft", "the_end", "region"),
            os.path.join(base, "DIM1", "region"),
        ),
    }
    for candidate in folders.get(dimension, folders["overworld"]):
        if os.path.isdir(candidate) and any(n.endswith(".mca") for n in os.listdir(candidate)):
            return candidate, base
    return None, base


def _dot(pixels, size, x, y, color, span=2):
    """Internal: dot."""
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            px, py = x + dx, y + dy
            if 0 <= px < size and 0 <= py < size:
                pos = (py * size + px) * 3
                pixels[pos:pos + 3] = bytes(color)


def _compass(pixels, size):
    """Internal: compass."""
    cx = size // 2
    for y, row in enumerate((
        (0, 1, 0, 1, 0),
        (1, 0, 0, 0, 1),
        (1, 0, 0, 0, 1),
        (1, 0, 0, 0, 1),
    )):
        for x, on in enumerate(row):
            if on:
                _dot(pixels, size, cx - 2 + x, 4 + y, (255, 255, 255), 0)


_map_cache = {}
_map_logged = set()
_map_cooldown = {}
MAP_COOLDOWN = 20
PLAYER_DOTS = ((255, 60, 60), (60, 140, 255), (255, 210, 60), (180, 80, 255), (60, 220, 140))


def render_map(center_x, center_z, radius, dimension="overworld", zoom=1, markers=(), spawn=None):
    """PNG bytes around the centre, plus chunk counts. zoom 2 or 4 covers more ground."""

    region_dir, base = region_dir_for(dimension)
    if region_dir is None:
        raise FileNotFoundError(f"no {dimension} region files found under {base}")
    step = zoom if zoom in (1, 2, 4) else 1
    size = radius * 2
    cover = radius * step
    west, north = center_x - cover, center_z - cover
    east, south = west + cover * 2, north + cover * 2
    signature = []
    for rz in range(north >> 9, ((south - 1) >> 9) + 1):
        for rx in range(west >> 9, ((east - 1) >> 9) + 1):
            path = os.path.join(region_dir, f"r.{rx}.{rz}.mca")
            signature.append((path, _mtime(path)))
    key = (MAP_STYLE, dimension, center_x, center_z, radius, step, tuple(signature), tuple(markers), spawn)
    cached = _map_cache.get(key)
    if cached is not None:
        return cached

    pixels = bytearray(bytes(NO_DATA) * (size * size))
    heights = [0] * (size * size)
    water = bytearray(size * size)
    known = bytearray(size * size)
    drawn = bad = 0
    logged = False

    for rz in range(north >> 9, ((south - 1) >> 9) + 1):
        for rx in range(west >> 9, ((east - 1) >> 9) + 1):
            path = os.path.join(region_dir, f"r.{rx}.{rz}.mca")
            if not os.path.isfile(path):
                continue
            with open(path, "rb") as file:
                for cz in range(max(north >> 4, rz * 32), min((south - 1) >> 4, rz * 32 + 31) + 1):
                    for cx in range(max(west >> 4, rx * 32), min((east - 1) >> 4, rx * 32 + 31) + 1):
                        try:
                            root = read_chunk(file, (cx & 31) + (cz & 31) * 32)
                            columns = chunk_columns(root, dimension) if root is not None else None
                        except Exception as error:
                            bad += 1
                            if not logged:
                                log.warning("map chunk unreadable in %s: %s", path, error)
                                logged = True
                            continue
                        if columns is None:
                            continue
                        drawn += 1
                        colors, chunk_heights, chunk_water = columns
                        for lz in range(0, 16, step):
                            wz = cz * 16 + lz
                            if not north <= wz < south:
                                continue
                            py = (wz - north) // step
                            for lx in range(0, 16, step):
                                wx = cx * 16 + lx
                                if not west <= wx < east:
                                    continue
                                px = (wx - west) // step
                                src = lz * 16 + lx
                                dst = py * size + px
                                pixels[dst * 3:dst * 3 + 3] = bytes(colors[src])
                                heights[dst] = chunk_heights[src]
                                water[dst] = chunk_water[src]
                                known[dst] = 1

    for dz in range(1, size):
        row = dz * size
        for dx in range(size):
            i = row + dx
            if not known[i]:
                continue
            if water[i]:
                north_h = heights[i - size] if known[i - size] else heights[i]
                west_h = heights[i - 1] if dx and known[i - 1] else heights[i]
                delta = heights[i] - (north_h + west_h) / 2
                if abs(delta) < 1:
                    continue
                factor = 1 + max(-3, min(3, delta)) * 0.06
                p = i * 3
                for channel in (p, p + 1, p + 2):
                    pixels[channel] = min(255, int(pixels[channel] * factor))
                continue
            north_h = heights[i - size] if known[i - size] else heights[i]
            west_h = heights[i - 1] if dx and known[i - 1] else heights[i]
            delta = heights[i] - (north_h + west_h) / 2
            slope = 1 + max(-5, min(5, delta)) * 0.1
            # Higher ground is a little brighter, like Overviewer and TMCMR.
            altitude = 0.84 + max(0.0, min(1.0, (heights[i] + 64) / 320)) * 0.22
            factor = slope * altitude
            if abs(delta) >= 3:
                factor *= 0.82
            p = i * 3
            for channel in (p, p + 1, p + 2):
                pixels[channel] = min(255, int(pixels[channel] * factor))

    gap = max(1, 256 // step)
    for pos in range(0, size, gap):
        for i in range(size):
            for channel in range(3):
                pixels[(pos * size + i) * 3 + channel] = min(255, pixels[(pos * size + i) * 3 + channel] + 18)
                pixels[(i * size + pos) * 3 + channel] = min(255, pixels[(i * size + pos) * 3 + channel] + 18)
    if spawn:
        sx, sz = spawn
        if west <= sx < east and north <= sz < south:
            _dot(pixels, size, (sx - west) // step, (sz - north) // step, (255, 40, 40), 3)
    for index, (_name, mx, mz) in enumerate(markers):
        if west <= mx < east and north <= mz < south:
            _dot(pixels, size, (mx - west) // step, (mz - north) // step, PLAYER_DOTS[index % len(PLAYER_DOTS)], 2)
    _compass(pixels, size)
    result = png_bytes(size, size, pixels), drawn, bad
    if len(_map_cache) > 8:
        _map_cache.clear()
    _map_cache[key] = result
    return result


def parse_pos(text):
    """Parse an entity Pos NBT string into coordinates."""
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text or "")
    if len(numbers) < 3:
        return None
    return int(float(numbers[0])), int(float(numbers[2]))


@bot.tree.command(name="map", description="Top-down map (only runs when you ask)")
@app_commands.describe(
    radius="Blocks from the centre. Default 256, max 512",
    x="Centre X",
    z="Centre Z",
    player="Centre on this online player",
    dimension="overworld, nether, or end",
    zoom="1, 2, or 4. Higher covers more ground at the same image size",
)
@app_commands.choices(
    dimension=[
        app_commands.Choice(name="overworld", value="overworld"),
        app_commands.Choice(name="nether", value="nether"),
        app_commands.Choice(name="end", value="end"),
    ],
    zoom=[
        app_commands.Choice(name="1", value=1),
        app_commands.Choice(name="2", value=2),
        app_commands.Choice(name="4", value=4),
    ],
)
async def world_map(
    interaction: discord.Interaction,
    radius: typing.Optional[int] = None,
    x: typing.Optional[int] = None,
    z: typing.Optional[int] = None,
    player: typing.Optional[str] = None,
    dimension: typing.Optional[app_commands.Choice[str]] = None,
    zoom: typing.Optional[app_commands.Choice[int]] = None,
):
    """Render a top-down map image."""
    global _map_running
    if not await gate(interaction):
        return
    now = time.monotonic()
    last = _map_cooldown.get(interaction.user.id, 0)
    if now - last < MAP_COOLDOWN:
        await deny(interaction, f"Wait {int(MAP_COOLDOWN - (now - last))}s before another map.")
        return
    radius = MAP_DEFAULT if radius is None else max(32, min(MAP_MAX, radius))
    dim = dimension.value if dimension else "overworld"
    step = zoom.value if zoom else 1
    if _map_running:
        await deny(interaction, "A map is already rendering.")
        return
    _map_running = True
    _map_cooldown[interaction.user.id] = now
    try:
        await interaction.response.defer()
        markers = []
        try:
            names = await online_player_names() or []
        except Exception:
            names = []
        for name in names[:8]:
            try:
                pos = parse_pos(await entity_data(name, "Pos") or "")
            except Exception:
                pos = None
            if pos:
                markers.append((name, pos[0], pos[1]))
        if player:
            match = next((item for item in markers if item[0].lower() == player.lower()), None)
            if match is None:
                await followup_text(interaction, f"[!] `{player}` is not online, so I can't centre on them.")
                return
            x, z = match[1], match[2]
        if x is None or z is None:
            spawn_x, spawn_z = await asyncio.to_thread(default_center)
            x = spawn_x if x is None else x
            z = spawn_z if z is None else z
        spawn = await asyncio.to_thread(default_center) if dim == "overworld" else None
        png, drawn, bad = await asyncio.to_thread(
            render_map, x, z, radius, dim, step, tuple(markers), spawn
        )
        if not drawn:
            await followup_text(interaction, f"[!] No generated chunks around {x}, {z}.")
            return
        note = f" {bad} unreadable chunks skipped." if bad else ""
        listed = ", ".join(f"{name}: {mx}, {mz}" for name, mx, mz in markers) or "none online"
        await interaction.followup.send(
            f"{dim}, {radius * 2}x{radius * 2} px, zoom {step}, centred on {x}, {z}.{note}\nPlayers: {listed}",
            file=discord.File(io.BytesIO(png), filename="map.png"),
        )
    except Exception as error:
        log.exception("/map failed")
        await followup_text(interaction, f"[!] Couldn't render the map: `{error}`")
    finally:
        _map_running = False



# ============================================================
# TPS HISTORY + GRAPH
# ============================================================

TPS_HISTORY = collections.deque(maxlen=1440)  # 6 hours at 15s
_tps_graph_running = False


async def tps_sample_loop():
    """Tps sample loop."""
    while True:
        try:
            result = await get_tps()
            value = None
            if result:
                labels, values = result
                names = [part.strip() for part in labels.split(",")]
                nums = [part.strip() for part in values.split(",")]
                def tps_number(raw):
                    """Tps number."""
                    # Paper prefixes a bad reading with *, so "*19.5" must still parse.
                    match = re.search(r"[0-9]+(?:\.[0-9]+)?", raw or "")
                    return float(match.group(0)) if match else None

                for name, raw in zip(names, nums):
                    if name.strip() in ("1m", "1"):
                        value = tps_number(raw)
                        break
                if value is None and nums:
                    value = tps_number(nums[0])
            TPS_HISTORY.append((time.time(), value))
        except Exception:
            TPS_HISTORY.append((time.time(), None))
        await asyncio.sleep(15)


async def tps_graph_follow(message, seconds):
    """Tps graph follow."""
    global _tps_graph_running
    deadline = time.monotonic() + seconds
    try:
        while time.monotonic() < deadline:
            await asyncio.sleep(30)
            try:
                lines = await tps_mspt_lines()
                chart = tps_chart(seconds, "TPS")
                left = max(0, int(deadline - time.monotonic()))
                await message.edit(
                    embed=panel(f"TPS, {left // 60}m {left % 60}s left", lines, COLOR_INFO),
                    attachments=[discord.File(io.BytesIO(chart), filename="tps.png")],
                )
            except EDIT_ERRORS:
                return
        try:
            lines = await tps_mspt_lines()
            await message.edit(
                embed=panel("TPS, 5 minutes", lines, COLOR_OK),
                attachments=[discord.File(io.BytesIO(tps_chart(seconds, "TPS")), filename="tps.png")],
            )
        except EDIT_ERRORS:
            pass
    finally:
        _tps_graph_running = False


def tps_chart(window, title):
    """PNG of 1-minute TPS over the last `window` seconds."""

    cutoff = time.time() - window
    points = [(stamp, value) for stamp, value in TPS_HISTORY if stamp >= cutoff and value is not None]
    width, height = 640, 240
    pixels = bytearray([18, 22, 28]) * (width * height)

    def put(x, y, color):
        """Put."""
        if 0 <= x < width and 0 <= y < height:
            pos = (y * width + x) * 3
            pixels[pos:pos + 3] = bytes(color)

    left, right, top, bottom = 36, width - 8, 16, height - 28
    for y in range(top, bottom):
        put(left, y, (60, 70, 80))
    for x in range(left, right):
        put(x, bottom, (60, 70, 80))
    for mark in (0, 10, 20):
        y = bottom - int((mark / 20) * (bottom - top))
        for x in range(left, right, 4):
            put(x, y, (40, 48, 58))
    if len(points) >= 2:
        span = max(1, points[-1][0] - points[0][0])
        prev = None
        for stamp, value in points:
            x = left + int((stamp - points[0][0]) / span * (right - left - 1))
            y = bottom - int(max(0, min(20, value)) / 20 * (bottom - top))
            color = (80, 200, 120) if value >= 18 else (220, 160, 60) if value >= 15 else (220, 80, 80)
            if prev:
                x0, y0 = prev
                steps = max(abs(x - x0), abs(y - y0), 1)
                for step in range(steps + 1):
                    put(x0 + (x - x0) * step // steps, y0 + (y - y0) * step // steps, color)
            put(x, y, color)
            prev = (x, y)
    return png_bytes(width, height, pixels)


# ============================================================
# /STRESSTEST
# ============================================================

_stress_running = False
async def ping_once(host):
    """ICMP time from ping itself, not the time spent starting the process."""

    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "1", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
        match = re.search(r"time[=<]([0-9.]+)", out.decode(errors="replace"))
        return float(match.group(1)) if match else None
    except Exception:
        return None


async def tailscale_peers():
    """Other Tailscale nodes. Pinging our own 100.x address does not test the path."""

    try:
        proc = await asyncio.create_subprocess_exec(
            "tailscale", "status", "--json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=4)
        data = json.loads(out.decode() or "{}")
    except Exception:
        return []
    peers = []
    for peer in (data.get("Peer") or {}).values():
        if not peer.get("Online"):
            continue
        ips = peer.get("TailscaleIPs") or []
        if ips:
            peers.append((peer.get("HostName") or ips[0], ips[0]))
    return peers


async def tailscale_ip():
    """Return this machine's Tailscale IPv4, or None."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "tailscale", "ip", "-4",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
        text = out.decode().strip().split()
        return text[0] if text else None
    except Exception:
        return None


async def network_burst():
    """Parallel pings. Tailscale is measured to a peer, not to ourselves."""

    targets = [("local", "127.0.0.1"), ("public", "1.1.1.1")]
    peers = await tailscale_peers()
    if peers:
        name, ip = peers[0]
        targets.append((f"tailscale {name}", ip))
    else:
        targets.append(("tailscale", None))
    async def sample(label, host):
        """Sample."""
        if not host:
            return f"{label}: no peer online"
        results = await asyncio.gather(*(ping_once(host) for _ in range(12)))
        values = [item for item in results if item is not None]
        if not values:
            return f"{label}: no reply"
        return (
            f"{label}: avg {sum(values)/len(values):.0f} ms, "
            f"min {min(values):.0f}, max {max(values):.0f}, "
            f"{len(values)}/12 ok"
        )
    return await asyncio.gather(*(sample(label, host) for label, host in targets))


async def health_snapshot():
    """Collect a one-line health summary for the stress log."""
    pid = await find_server_pid()
    if pid is None:
        return ["server offline"]
    age, info, tps_result, (rss_kb, cpu), cmdline = await asyncio.gather(
        server_age(pid), get_player_info(), get_tps(), process_usage(pid),
        asyncio.to_thread(process_cmdline, pid),
    )
    xmx_kb = heap_limit_kb(cmdline)
    lines = [time.strftime("%H:%M:%S")]
    lines.append("TPS: unavailable" if tps_result is None else f"TPS: {fmt_tps(*tps_result)}")
    lines.append(format_players(info))
    if age is not None:
        lines.append(f"Server uptime: {format_uptime(age)}")
    lines.append(f"RAM: {format_ram(rss_kb)}" + (f" (max heap {format_ram(xmx_kb)})" if xmx_kb else ""))
    lines.append("CPU: unavailable" if cpu is None else f"CPU: {cpu:.0f}% (100% = 1 core)")
    lines.extend(host_power_lines())
    lines.append(disk_usage_text())
    return lines


class StressView(discord.ui.View):
    """Persistent Stop button. custom_id keeps it alive past 15 minutes."""

    def __init__(self, stop_event):
        """Internal: init."""
        super().__init__(timeout=None)
        self.stop_event = stop_event

    @discord.ui.button(
        label="Stop test",
        style=discord.ButtonStyle.danger,
        custom_id="stresstest:stop",
    )
    async def stop_test(self, interaction, button):
        """Stop test."""
        if not member_is_admin(interaction):
            await deny(interaction, "Only an admin can stop the test.")
            return
        self.stop_event.set()
        button.disabled = True
        try:
            await interaction.response.edit_message(
                embed=panel("Stress test", ["Stopping. Restoring blocks."], COLOR_WAIT),
                view=self,
            )
        except EDIT_ERRORS:
            if not interaction.response.is_done():
                await interaction.response.defer()


STRESS_WARN = "Long duration validation test underway. Changes you make will NOT be saved."
STRESS_MAX_MINUTES = 300  # 5 hours
STRESS_DIMS = ("overworld", "nether", "end")
DIM_EXECUTE = {
    "overworld": "minecraft:overworld",
    "nether": "minecraft:the_nether",
    "end": "minecraft:the_end",
}


def dim_cmd(dimension, command):
    """Prefix a console command so it runs in the named dimension."""
    dim = DIM_EXECUTE.get(dimension, "minecraft:overworld")
    return f"execute in {dim} run {command}"


def stress_graph(tps_points, ping_points):
    """One image: TPS on the left scale, ping on the right."""

    width, height = 640, 220
    pixels = bytearray(bytes((16, 18, 22)) * (width * height))

    def put(x, y, color):
        """Put."""
        if 0 <= x < width and 0 <= y < height:
            i = (y * width + x) * 3
            pixels[i:i + 3] = bytes(color)

    left, right, top, bottom = 36, width - 28, 16, height - 24
    for y in range(top, bottom):
        put(left, y, (50, 54, 60))
        put(right, y, (50, 54, 60))
    for x in range(left, right):
        put(x, bottom, (50, 54, 60))
        if (x - left) % 80 == 0:
            put(x, bottom + 2, (80, 84, 90))
    for mark, label_y in ((20, top), (10, (top + bottom) // 2)):
        y = bottom - int(mark / 20 * (bottom - top))
        for x in range(left, right, 6):
            put(x, y, (36, 40, 46))

    def series(points, scale, color):
        """Series."""
        usable = [(stamp, value) for stamp, value in points if value is not None]
        if len(usable) < 2:
            return
        span = max(1.0, usable[-1][0] - usable[0][0])
        prev = None
        for stamp, value in usable:
            x = left + int((stamp - usable[0][0]) / span * (right - left - 1))
            y = bottom - int(max(0, min(scale, value)) / scale * (bottom - top))
            if prev:
                x0, y0 = prev
                steps = max(abs(x - x0), abs(y - y0), 1)
                for step in range(steps + 1):
                    put(x0 + (x - x0) * step // steps, y0 + (y - y0) * step // steps, color)
            put(x, y, color)
            prev = (x, y)

    series(tps_points, 20, (80, 200, 120))
    pings = [value for _stamp, value in ping_points if value is not None]
    ping_scale = max(50, max(pings) if pings else 50)
    series(ping_points, ping_scale, (90, 160, 230))
    return png_bytes(width, height, pixels)


class PanelStatus:
    """Lets wait_for_state update the stress panel."""

    def __init__(self, message, view):
        """Internal: init."""
        self.message = message
        self.view = view

    async def set(self, text, force=False):
        """Set."""
        try:
            await self.message.edit(
                embed=panel("Stress test", [text], COLOR_WAIT),
                view=self.view,
            )
        except EDIT_ERRORS:
            log.info("stress: %s", text)


async def stress_stop_server(status):
    """Stop the server cleanly during a stress test."""
    if not await server_running(force=True):
        return True
    await save_world()
    t0 = time.monotonic()
    if not await send_stop():
        await status.set("Could not send stop.")
        return False
    return await wait_for_state(
        status, False, t0,
        "Stopping the server...",
        "Server stopped.",
        "Server did not stop.",
    )


async def tmux_session_exists():
    """True if the Minecraft tmux session exists."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux", "has-session", "-t", MC_SESSION,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        return await proc.wait() == 0
    except OSError:
        return False


async def kill_tmux_session():
    """Kill the Minecraft tmux session."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "tmux", "kill-session", "-t", MC_SESSION,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except OSError:
        pass


async def wait_until_fully_stopped(status, timeout=90):
    """Paper 26 can spend a minute closing RegionFile and Moonrise pools.

    The start script exits immediately if the tmux session still exists, so a
    start during that window watches the old process die and reports a crash.
    """

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        running = await server_running(force=True)
        session = await tmux_session_exists()
        if not running and not session:
            return True
        if not running and session:
            await status.set("Clearing the leftover tmux session.")
            await kill_tmux_session()
        else:
            await status.set("Waiting for the old server to finish shutting down.")
        await asyncio.sleep(1)
    return False


async def stress_start_server(status):
    """Start the server after a stress-test restore."""
    if not await wait_until_fully_stopped(status):
        await status.set("The old server did not finish shutting down.")
        return False
    # The wake listener owns 25565 while the server is down. Paper cannot bind
    # until that listener is closed.
    await close_wake_listener()
    await asyncio.to_thread(remove_legacy_dimension_folders)
    await asyncio.sleep(PORT_WAIT)
    cursor = LogCursor()
    launch = await launch_server()
    return await wait_for_ready(
        status, time.monotonic(), cursor, launch,
        "Starting the server...",
        "Server is ready.",
        "Server did not finish starting.",
    )


async def stress_snapshot(status):
    """Stop, copy the worlds, start again. Returns the backup folder or None."""

    await status.set("Saving the world before the snapshot.")
    if not await stress_stop_server(status):
        return None
    await status.set("Copying the worlds.")
    code, tail, folder = await perform_backup("manual")
    if code != 0 or not folder:
        await status.set(f"Backup failed: {tail[:200]!r}")
        await stress_start_server(status)
        return None
    if not await stress_start_server(status):
        await status.set("Backup is saved, but the server did not come back. Trying again.")
        if not await stress_start_server(status):
            return None
    return folder


async def stress_restore_world(status, folder):
    """Stop, put the snapshot back, start again."""

    if not await stress_stop_server(status):
        return False
    await status.set("Restoring the pre-test world.")
    try:
        copied = await asyncio.to_thread(restore_backup_folder, folder)
    except Exception as error:
        log.exception("stress restore failed")
        await status.set(f"Restore failed: {error}")
        await stress_start_server(status)
        return False
    log.info("Stress restore replaced: %s", ", ".join(copied))
    return await stress_start_server(status)


async def stress_load_area(x, z, size=32, dimension="overworld"):
    """forceload a square so fill and summon actually run. Both no-op on unloaded chunks."""

    await send_console(
        dim_cmd(dimension, f"forceload add {x} {z} {x + size} {z + size}"),
        timeout=8,
    )
    await asyncio.sleep(0.4)


async def stress_heavy_burst(dimension="overworld"):
    """One destructive burst in a chosen dimension. The world is restored from the snapshot afterwards."""

    # Nether/End have different safe Y ranges; stay above bedrock-ish.
    if dimension == "nether":
        base_x = random.randint(-500, 500)
        base_z = random.randint(-500, 500)
        y = random.randint(40, 80)
    elif dimension == "end":
        base_x = random.randint(-200, 200)
        base_z = random.randint(-200, 200)
        y = random.randint(60, 90)
    else:
        base_x = random.randint(-2000, 2000)
        base_z = random.randint(-2000, 2000)
        y = random.randint(80, 120)
    notes = []
    kind = random.choice(("place", "chunks", "elytra", "explode", "village", "mobs"))
    notes.append(f"[{dimension}]")
    if kind == "place":
        await stress_load_area(base_x, base_z, 96, dimension)
        for n in range(4):
            x = base_x + n * 20
            z = base_z + n * 16
            await send_console(
                dim_cmd(dimension, f"fill {x} {y} {z} {x + 6} {y + 4} {z + 6} minecraft:cobblestone"),
                timeout=6,
            )
            await send_console(
                dim_cmd(dimension, f"fill {x} {y} {z} {x + 6} {y + 4} {z + 6} minecraft:air"),
                timeout=6,
            )
        notes.append(f"4 players placed and broke near {base_x},{base_z}")
    elif kind == "chunks":
        await send_console(
            dim_cmd(dimension, f"forceload add {base_x} {base_z} {base_x + 144} {base_z + 144}"),
            timeout=8,
        )
        await asyncio.sleep(random.uniform(2, 4))
        notes.append(f"loaded a 144 block square at {base_x},{base_z}")
    elif kind == "elytra":
        dx, dz = random.choice(((64, 0), (-64, 0), (0, 64), (0, -64), (48, 48)))
        x, z = base_x, base_z
        for _ in range(random.randint(8, 14)):
            await send_console(dim_cmd(dimension, f"forceload add {x} {z} {x + 31} {z + 31}"), timeout=4)
            x += dx
            z += dz
            await asyncio.sleep(0.35)
        notes.append(f"elytra-style chunk line from {base_x},{base_z}")
    elif kind == "explode":
        await stress_load_area(base_x, base_z, 48, dimension)
        for _n in range(random.randint(6, 12)):
            x = base_x + random.randint(0, 40)
            z = base_z + random.randint(0, 40)
            await send_console(
                dim_cmd(dimension, f"summon minecraft:tnt {x} {y} {z} {{Fuse:{random.randint(15, 40)}}}"),
                timeout=4,
            )
        notes.append(f"explosions at {base_x},{base_z}")
    elif kind == "village":
        await stress_load_area(base_x, base_z, 32, dimension)
        for n in range(random.randint(8, 14)):
            await send_console(
                dim_cmd(dimension, f"summon minecraft:villager {base_x + n} {y} {base_z}"),
                timeout=4,
            )
        await send_console(dim_cmd(dimension, f"summon minecraft:iron_golem {base_x} {y} {base_z}"), timeout=4)
        await send_console(dim_cmd(dimension, f"summon minecraft:zombie {base_x + 6} {y} {base_z}"), timeout=4)
        notes.append(f"villagers and a raid at {base_x},{base_z}")
    else:
        await stress_load_area(base_x, base_z, 32, dimension)
        for _n in range(random.randint(10, 24)):
            x = base_x + random.randint(0, 24)
            z = base_z + random.randint(0, 24)
            mob = random.choice(("zombie", "skeleton", "creeper"))
            await send_console(dim_cmd(dimension, f"summon minecraft:{mob} {x} {y} {z}"), timeout=4)
        notes.append(f"mob horde at {base_x},{base_z}")
    return ", ".join(notes) or kind


async def stress_warn():
    """Red line in Minecraft chat. tellraw, because say cannot colour text."""

    payload = json.dumps({"text": f"[bot] {STRESS_WARN}", "color": "red"})
    await send_console(f"tellraw @a {payload}", timeout=4)


@bot.tree.command(name="stresstest", description="Multi-dimension load test (overworld/nether/end), network, and health log")
@app_commands.describe(minutes="Minutes. Default 20, maximum 300")
async def stresstest(interaction: discord.Interaction, minutes: typing.Optional[int] = 20):
    """Slash command: multi-dimension load test with snapshot/restore."""
    if not await gate(interaction, admin=True):
        return
    if _stress_running:
        await deny(interaction, "A stress test is already running.")
        return
    minutes = 20 if minutes is None else max(1, min(STRESS_MAX_MINUTES, minutes))
    if not await server_running():
        await deny(interaction, "Start the server first.")
        return

    async def runner(confirmed):
        await run_stresstest(confirmed, minutes)

    await ask_confirm(
        interaction,
        "stresstest",
        (
            "**Run a stress test?**\n"
            f"This stops the server (everyone is kicked) and, for {minutes} minutes, "
            "fills, loads chunks, and summons TNT in the overworld, nether, and end.\n"
            "The world is restored from a snapshot at the end. "
            "**Anything players do during the test is erased.**"
        ),
        runner,
    )


async def run_stresstest(interaction, minutes):
    """The confirmed test. ConfirmView holds the lock until this returns."""

    global _stress_running
    _stress_running = True  # why: held with the lock so !start and wake cannot launch Paper mid-copy
    invalidate_confirms("A stress test started.")
    stop_event = asyncio.Event()
    view = StressView(stop_event)
    message = None
    try:
        # A channel message stays editable past 15 minutes. A followup webhook does not.
        message = await interaction.channel.send(
            embed=panel("Stress test", [f"Starting a {minutes} min multi-dimension load (overworld + nether + end)."], COLOR_WAIT),
            view=view,
        )
        bot.add_view(view, message_id=message.id)
        await interaction.followup.send(f"Stress test panel: {message.jump_url}", ephemeral=False)
    except Exception:
        _stress_running = False
        raise
    log_path = os.path.join(BOT_LOG_DIR, "stresstest.log")
    status = PanelStatus(message, view)
    snapshot = await stress_snapshot(status)
    if not snapshot:
        _stress_running = False
        view.stop()
        try:
            await message.edit(
                embed=panel("Stress test aborted", ["The world was not changed."], COLOR_BAD),
                view=None,
            )
        except EDIT_ERRORS:
            pass
        return
    deadline = time.monotonic() + minutes * 60
    next_warn = 0.0
    tps_points, ping_points = [], []
    await stress_warn()
    try:
        while time.monotonic() < deadline and not stop_event.is_set():
            if time.monotonic() >= next_warn:
                await stress_warn()
                next_warn = time.monotonic() + 120
            try:
                # Run several simulations at once across dimensions.
                dims = random.sample(STRESS_DIMS, k=min(3, len(STRESS_DIMS)))
                burst_notes = []
                for dim in dims:
                    note = await stress_heavy_burst(dim)
                    burst_notes.append(note)
                world_note = " | ".join(burst_notes)
                health = await health_snapshot()
                net = list(await network_burst())
            except Exception as error:
                log.warning("stress cycle failed: %s", error)
                health, net, world_note = [f"cycle error: {error}"], [], ""
            tps_value = None
            for line in health:
                if str(line).startswith("TPS:"):
                    match = re.search(r"[0-9]+(?:\.[0-9]+)?", str(line))
                    tps_value = float(match.group(0)) if match else None
            ping_value = None
            for line in net:
                match = re.search(r"avg ([0-9]+)", str(line))
                if match:
                    ping_value = float(match.group(1))
                    break
            now = time.time()
            tps_points.append((now, tps_value))
            ping_points.append((now, ping_value))
            lines = health + ([world_note] if world_note else []) + list(net)
            body = "\n".join(str(line) for line in lines)
            if len(body) > 3500:
                lines = lines[:12] + ["…truncated"]
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as file:
                    file.write(stamp + " | " + " | ".join(str(line) for line in lines) + "\n")
            except OSError:
                pass
            left = max(0, int(deadline - time.monotonic()))
            png = stress_graph(tps_points, ping_points)
            embed = panel(
                "Stress test",
                [f"{left // 60}m {left % 60}s left", "Green is TPS, blue is ping.", *lines],
                COLOR_WAIT,
            )
            embed.set_image(url="attachment://stress.png")
            try:
                await message.edit(
                    embed=embed,
                    attachments=[discord.File(io.BytesIO(png), filename="stress.png")],
                    view=view,
                )
            except EDIT_ERRORS:
                old_message = message
                try:
                    await old_message.edit(view=None)
                except EDIT_ERRORS:
                    pass
                try:
                    message = await interaction.channel.send(
                        embed=embed,
                        file=discord.File(io.BytesIO(png), filename="stress.png"),
                        view=view,
                    )
                    status.message = message
                    bot.add_view(view, message_id=message.id)
                except EDIT_ERRORS:
                    pass
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=random.uniform(4, 8))
            except asyncio.TimeoutError:
                pass
    finally:
        await send_console("forceload remove all", timeout=6)
        for dim in STRESS_DIMS:
            await send_console(dim_cmd(dim, "kill @e[type=tnt]"), timeout=4)
            await send_console(dim_cmd(dim, "kill @e[type=villager]"), timeout=4)
            await send_console(dim_cmd(dim, "kill @e[type=iron_golem]"), timeout=4)
            await send_console(dim_cmd(dim, "kill @e[type=zombie]"), timeout=4)
            await send_console(dim_cmd(dim, "kill @e[type=skeleton]"), timeout=4)
            await send_console(dim_cmd(dim, "kill @e[type=creeper]"), timeout=4)
        restored = await stress_restore_world(status, snapshot)
        _stress_running = False
        view.stop()
        done = [
            f"Snapshot: `{os.path.basename(snapshot)}`",
            "World restored." if restored else "Restore failed. The snapshot is still in the backup folder.",
            f"Log: `{log_path}`",
        ]
        try:
            if message is not None:
                await message.edit(
                    embed=panel(
                        "Stress test finished",
                        done,
                        COLOR_OK if restored else COLOR_BAD,
                    ),
                    view=None,
                )
        except EDIT_ERRORS:
            pass


# ============================================================
# /HEALTH /PLAYERS /TPS
# ============================================================

@bot.tree.command(name="health", description="TPS, players, uptime, RAM, CPU, battery, and power")
async def health(interaction: discord.Interaction):
    """Slash command: show TPS, players, RAM, CPU, and host stats."""
    if not await gate(interaction):
        return
    await interaction.response.defer()

    pid = await find_server_pid()
    if pid is None:
        await followup_text(interaction, "[-] **Server offline**")
        return

    age, info, tps_result, (rss_kb, cpu), cmdline = await asyncio.gather(
        server_age(pid), get_player_info(), get_tps(), process_usage(pid),
        asyncio.to_thread(process_cmdline, pid),
    )
    xmx_kb = heap_limit_kb(cmdline)

    lines = ["Server health"]
    lines.append(
        "TPS: unavailable" if tps_result is None else f"TPS: {fmt_tps(*tps_result)}"
    )
    lines.append(format_players(info))
    if age is not None:
        lines.append(f"Server uptime: {format_uptime(age)}")
    lines.append(
        f"RAM: {format_ram(rss_kb)}"
        + (f" (max heap {format_ram(xmx_kb)})" if xmx_kb else "")
    )
    lines.append(
        "CPU: unavailable" if cpu is None else f"CPU: {cpu:.0f}% (100% = 1 core)"
    )
    lines.extend(host_power_lines())
    lines.append(disk_usage_text())
    await followup_embed(interaction, panel("Server health", lines[1:], COLOR_INFO))


@bot.tree.command(name="players", description="Show who is online")
async def players(interaction: discord.Interaction):
    """Slash command: list online players."""
    if not await gate(interaction):
        return
    if not RCON_PASSWORD:
        await deny(interaction, "[!] RCON isn't configured.")
        return

    await interaction.response.defer()
    try:
        output = await rcon.command("list")
    except RCON_ERRORS as error:
        log.warning("Players command RCON failed: %s", describe_rcon_error(error))
        await followup_text(
            interaction,
            "[!] **Couldn't reach RCON.**\nRun `/rcontest` to see why.",
        )
        return

    output = strip_colors(output).strip() or "No response."
    await followup_embed(
        interaction,
        panel("Players", [discord.utils.escape_markdown(output)], COLOR_INFO),
    )


def fmt_metric(kind, result):
    """Format a TPS or MSPT result."""
    if result is None:
        return f"{kind}: unavailable"
    return f"{kind}: {fmt_tps(*result)}"


async def tps_mspt_lines():
    """Return current TPS and MSPT lines."""
    tps_result, mspt_result = await asyncio.gather(get_tps(), get_mspt())
    return [fmt_metric("TPS", tps_result), fmt_metric("MSPT", mspt_result)]


@bot.tree.command(name="tps", description="Show current server TPS and MSPT")
async def tps(interaction: discord.Interaction):
    """Slash command: show current TPS and MSPT."""
    if not await gate(interaction):
        return
    await interaction.response.defer()

    if not await server_running():
        await followup_text(interaction, "[-] **Server offline**")
        return

    lines = await tps_mspt_lines()
    if all(line.endswith("unavailable") for line in lines):
        await followup_text(interaction, "[!] **Couldn't read TPS or MSPT.**")
        return
    global _tps_graph_running
    if _tps_graph_running:
        await followup_text(interaction, "A TPS graph is already running.")
        return
    _tps_graph_running = True
    chart = tps_chart(300, "TPS")
    message = await interaction.followup.send(
        embed=panel("TPS, collecting 5 minutes", lines, COLOR_INFO),
        file=discord.File(io.BytesIO(chart), filename="tps.png"),
        wait=True,
    )
    spawn(tps_graph_follow(message, 300))


# ============================================================
# /SAY
# ============================================================

def clean_chat(text, limit):
    """Sanitize text before sending it to Minecraft chat."""
    text = text.replace("§", "")  # no formatting-code injection
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)  # CR/LF and other controls
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


@bot.tree.command(name="say", description="Send a message to Minecraft chat")
@app_commands.describe(message="What to say in game")
async def say(interaction: discord.Interaction, message: str):
    """Slash command: send a message into Minecraft chat."""
    if not await gate(interaction):
        return
    if not RCON_PASSWORD:
        await deny(interaction, "[!] RCON isn't configured.")
        return

    name = clean_chat(interaction.user.display_name, 32) or "Discord"
    clean = clean_chat(message, 200)
    if not clean:
        await deny(interaction, "[!] Nothing to say.")
        return

    await interaction.response.defer()
    ok, detail = await say_bot(f"[Discord] {name}: {clean}")
    if not ok:
        await followup_text(
            interaction,
            f"Couldn't reach RCON.\n{detail}\nRun `/rcontest` to see why.",
        )
        return
    await followup_embed(
        interaction, panel("Sent in game", [detail.replace("`", "'")], COLOR_OK)
    )


# ============================================================
# /STATS
# ============================================================

PLAYER_NAME_RE = re.compile(r"^[A-Za-z0-9_]{1,16}$")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
NBT_NUMBER_RE = re.compile(r"(-?\d+(?:\.\d+)?)[a-zA-Z]*")
ITEM_ID_RE = re.compile(r'id:\s*"?(minecraft:[a-z0-9_./-]+)"?', re.IGNORECASE)
ITEM_COUNT_RE = re.compile(r'\bcount:\s*(\d+)', re.IGNORECASE)
STAT_LABELS = {
    "minecraft:play_time": "Play time",
    "minecraft:total_world_time": "World time",
    "minecraft:deaths": "Deaths",
    "minecraft:player_kills": "Player kills",
    "minecraft:mob_kills": "Mob kills",
    "minecraft:damage_dealt": "Damage dealt",
    "minecraft:damage_taken": "Damage taken",
    "minecraft:jump": "Jumps",
    "minecraft:walk_one_cm": "Walked",
    "minecraft:sprint_one_cm": "Sprinted",
    "minecraft:fly_one_cm": "Flown",
    "minecraft:fall_one_cm": "Fallen",
    "minecraft:swim_one_cm": "Swum",
    "minecraft:time_since_death": "Since death",
    "minecraft:time_since_rest": "Since sleep",
    "minecraft:leave_game": "Leaves",
}


def server_root():
    """Return the Minecraft server root directory."""
    return SERVER_DIR or os.path.dirname(os.path.dirname(LOG_PATH))


def safe_level_name(name):
    """Sanitize a level-name so it cannot escape the server root."""
    name = str(name or "").strip()
    if (
        not name
        or name in (".", "..")
        or "/" in name
        or "\\" in name
        or ".." in name
    ):
        return "world"
    return name


def safe_player_uuid(value):
    """Return a lowercase UUID if valid, else None."""
    text = str(value or "")
    return text.lower() if UUID_RE.fullmatch(text) else None


def world_dir():
    """Return the path to the current world directory."""
    level = "world"
    try:
        _, found, _encoding = props_load()
        level = safe_level_name(props_current(found, "level-name"))
    except OSError:
        pass
    return os.path.join(server_root(), level)


def lookup_uuid(name):
    """Look up a player UUID from usercache.json."""
    path = os.path.join(server_root(), "usercache.json")
    try:
        with open(path, "r", encoding="utf-8") as file:
            rows = json.load(file)
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    for row in rows:
        found = safe_player_uuid(row.get("uuid"))
        if str(row.get("name", "")).lower() == name.lower() and found:
            return found
    return None


def nbt_number(text):
    """Extract a number from an NBT value string."""
    match = NBT_NUMBER_RE.search(text or "")
    if not match:
        return None
    number = float(match.group(1))
    return int(number) if number.is_integer() else number


def _top_level_item_fields(compound):
    """Fields of one item, with nested compounds removed.

    why: a shulker's contents are nested items; counting them would double
    the inventory, and id/count order varies by Minecraft version.
    """

    depth = 0
    out = []
    for ch in compound[1:-1]:
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def _item_compounds(text):
    """Each top-level {...} in an inventory list. Nested compounds stay inside."""

    depth = 0
    start = None
    for index, ch in enumerate(text or ""):
        if ch == "{":
            if depth == 0:
                start = index
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
            if depth == 0 and start is not None:
                yield text[start:index + 1]
                start = None


def parse_items(text):
    """Parse an inventory NBT string into item counts."""
    counts = {}
    for compound in _item_compounds(text):
        fields = _top_level_item_fields(compound)
        found = ITEM_ID_RE.search(fields)
        if not found:
            continue
        count_match = ITEM_COUNT_RE.search(fields)
        count = int(count_match.group(1)) if count_match else 1
        name = found.group(1).split(":")[-1].replace("_", " ")
        counts[name] = counts.get(name, 0) + count
    if not counts:
        return "empty"
    rows = [f"{name} x{count}" for name, count in sorted(counts.items())]
    body = ", ".join(rows)
    return body if len(body) <= 900 else body[:899] + "…"


def format_stat(key, value):
    """Format a single stat value for display."""
    if key.endswith("_one_cm"):
        meters = value / 100
        return f"{meters / 1000:.2f} km" if meters >= 1000 else f"{meters:.0f} m"
    if key.endswith("_time") or key.startswith("minecraft:time_"):
        seconds = value // 20
        return format_uptime(seconds)
    return f"{value:,}"


def read_player_stats(uuid):
    """Load a player's stats JSON, or None if missing/invalid."""
    uuid = safe_player_uuid(uuid)
    if not uuid:
        return None
    root = os.path.realpath(world_dir())
    path = os.path.realpath(os.path.join(root, "stats", uuid + ".json"))
    try:
        if os.path.commonpath([root, path]) != root:
            return None
    except ValueError:
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file).get("stats") or {}
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def stat_lines(stats, section, limit=8):
    """Format the top entries of a stats section."""
    block = stats.get(section) or {}
    ranked = sorted(block.items(), key=lambda item: item[1], reverse=True)[:limit]
    if not ranked:
        return "none"
    return "\n".join(
        f"{key.split(':')[-1].replace('_', ' ')}: {value:,}" for key, value in ranked
    )[:1000]


def custom_stat_lines(stats):
    """Format selected custom stats for a player."""
    block = stats.get("minecraft:custom") or {}
    lines = []
    for key, label in STAT_LABELS.items():
        if key in block:
            lines.append(f"{label}: {format_stat(key, block[key])}")
    return "\n".join(lines) or "no custom stats yet"


async def entity_data(player, path):
    """Fetch an entity NBT path via RCON."""
    output = await rcon.command(f"data get entity {player} {path}", timeout=8)
    clean = strip_colors(output).strip()
    lowered = clean.lower()
    if "no entity was found" in lowered:
        return None
    # why: NBT can contain "unknown" in a custom name; only a command error is missing data
    if "has the following entity data" in lowered or (clean[:1] in "{["):
        return clean
    if "unknown" in lowered or "incorrect" in lowered:
        return None
    return clean


def stats_embeds(player, live, stats, online):
    """Build embeds for a player's stats."""
    vitals = discord.Embed(
        title=player,
        color=COLOR_OK if online else COLOR_WAIT,
        description="Online" if online else "Offline. Live health is unavailable; file stats are shown.",
    )
    vitals.add_field(name="Health", value=str(live.get("health", "unavailable")), inline=True)
    vitals.add_field(name="Hunger", value=str(live.get("hunger", "unavailable")), inline=True)
    vitals.add_field(name="Saturation", value=str(live.get("saturation", "unavailable")), inline=True)
    vitals.add_field(name="XP level", value=str(live.get("xp", "unavailable")), inline=True)
    vitals.add_field(name="Dimension", value=str(live.get("dimension", "unavailable"))[:100], inline=True)
    vitals.add_field(name="Position", value=str(live.get("pos", "unavailable"))[:100], inline=True)
    vitals.add_field(name="Held item", value=str(live.get("held", "none"))[:200], inline=False)
    vitals.add_field(name="Ender chest", value=live.get("ender", "unavailable")[:1024], inline=False)
    vitals.add_field(name="Inventory", value=live.get("inventory", "unavailable")[:1024], inline=False)
    vitals.set_footer(text="Live values come from the server. File stats are the lifetime counters.")

    file_embed = discord.Embed(title=f"{player} stats", color=COLOR_INFO)
    if not stats:
        file_embed.description = "No stats file for this player yet."
        return [vitals, file_embed]
    file_embed.add_field(name="General", value=custom_stat_lines(stats)[:1024], inline=False)
    file_embed.add_field(name="Mined", value=stat_lines(stats, "minecraft:mined"), inline=True)
    file_embed.add_field(name="Used", value=stat_lines(stats, "minecraft:used"), inline=True)
    file_embed.add_field(name="Crafted", value=stat_lines(stats, "minecraft:crafted"), inline=True)
    file_embed.add_field(name="Killed", value=stat_lines(stats, "minecraft:killed"), inline=True)
    file_embed.add_field(name="Killed by", value=stat_lines(stats, "minecraft:killed_by"), inline=True)
    file_embed.add_field(name="Picked up", value=stat_lines(stats, "minecraft:picked_up"), inline=True)
    return [vitals, file_embed]


@bot.tree.command(name="stats", description="Health, hunger, ender chest, inventory, and lifetime stats")
@app_commands.describe(player="Exact Minecraft name")
async def stats(interaction: discord.Interaction, player: str):
    """Slash command: show player health, inventory, and stats."""
    if not await gate(interaction):
        return
    if not PLAYER_NAME_RE.fullmatch(player):
        await deny(interaction, "That is not a Minecraft player name.")
        return
    await interaction.response.defer(ephemeral=False)

    live = {
        "health": "offline",
        "hunger": "offline",
        "saturation": "offline",
        "xp": "offline",
        "dimension": "unavailable",
        "pos": "unavailable",
        "held": "none",
        "ender": "offline",
        "inventory": "offline",
    }
    online = False
    if RCON_PASSWORD:
        try:
            health = await entity_data(player, "Health")
            online = health is not None
            if online:
                paths = (
                    "foodLevel",
                    "foodSaturation",
                    "XpLevel",
                    "Dimension",
                    "Pos",
                    "SelectedItem",
                    "EnderItems",
                    "Inventory",
                )
                fetched = []
                for path in paths:
                    fetched.append(await entity_data(player, path))
                fields = dict(zip(paths, fetched))
                live["health"] = nbt_number(health)
                live["hunger"] = nbt_number(fields["foodLevel"])
                live["saturation"] = nbt_number(fields["foodSaturation"])
                live["xp"] = nbt_number(fields["XpLevel"])
                live["dimension"] = (fields["Dimension"] or "unavailable").split(":")[-1]
                live["pos"] = fields["Pos"] or "unavailable"
                live["held"] = parse_items(fields["SelectedItem"]) if fields["SelectedItem"] else "none"
                live["ender"] = parse_items(fields["EnderItems"])
                live["inventory"] = parse_items(fields["Inventory"])
        except RCON_ERRORS as error:
            live["health"] = describe_rcon_error(error)

    uuid = await asyncio.to_thread(lookup_uuid, player)
    file_stats = await asyncio.to_thread(read_player_stats, uuid)
    embeds = stats_embeds(player, live, file_stats, online)
    await interaction.followup.send(embeds=embeds, ephemeral=False)


# ============================================================
# /TEST
# ============================================================

TEST_TARGETS = (
    "all",
    "rcon",
    "process",
    "tps",
    "health",
    "alert",
    "audit",
    "log",
    "say",
    "idle",
    "backup",
    "stats",
)


async def test_one(target, extra):
    """Test one."""
    extra = (extra or "").strip()
    if target == "rcon":
        ok, detail = await rcon_diagnose()
        return ("pass" if ok else "fail"), detail
    if target == "process":
        try:
            pid = await find_server_pid()
        except AmbiguousServer as error:
            return "fail", str(error)
        if pid is None:
            return "fail", "No matching server process."
        age = await server_age(pid)
        return "pass", f"pid {pid}, uptime {format_uptime(age or 0)}"
    if target == "tps":
        seconds = 0
        if extra.isdigit():
            seconds = min(int(extra), 30)
            await asyncio.sleep(seconds)
        result = await get_tps()
        if result is None:
            return "fail", "No TPS reading."
        return "pass", fmt_tps(*result) + (f" after {seconds}s" if seconds else "")
    if target == "health":
        pid = await find_server_pid()
        if pid is None:
            return "fail", "Server offline."
        rss, cpu = await process_usage(pid)
        memory = system_memory()
        pct = server_ram_percent(rss, memory)
        return "pass", f"server RAM {format_ram(rss)}" + (
            f" ({pct:.0f}% of system)" if pct is not None else ""
        ) + (f", CPU {cpu:.0f}%" if cpu is not None else "")
    if target == "alert":
        note = extra or "manual /test alert"
        message = await send_alert(f"Test alert: {note}")
        return ("pass" if message or not ALERT_CHANNEL_ID else "fail"), (
            f"posted to {ALERT_CHANNEL_ID}" if ALERT_CHANNEL_ID else "MC_ALERT_CHANNEL_ID is unset"
        )
    if target == "audit":
        cmd_log.info("test audit %s", extra or "manual")
        if audit.started:
            await audit.flush()
        return ("pass" if AUDIT_CHANNEL_ID else "fail"), (
            f"posted to {AUDIT_CHANNEL_ID}" if AUDIT_CHANNEL_ID else "MC_AUDIT_CHANNEL_ID is unset"
        )
    if target == "log":
        log.info("test log %s", extra or "manual")
        if relay.started:
            await relay.flush()
        return ("pass" if LOG_CHANNEL_ID else "fail"), (
            f"posted to {LOG_CHANNEL_ID}" if LOG_CHANNEL_ID else "MC_LOG_CHANNEL_ID is unset"
        )
    if target == "say":
        ok, detail = await say_bot(extra or "test warning")
        return ("pass" if ok else "fail"), detail
    if target == "idle":
        if not IDLE_ACTIVE:
            return "fail", "Idle shutdown is off or has no channel / RCON."
        if idle.since is None:
            return "pass", f"idle timer not running (limit {IDLE_TIMEOUT}s)"
        return "pass", f"idle timer at {idle.elapsed(time.monotonic())}s of {IDLE_TIMEOUT}s"
    if target == "backup":
        if not BACKUP_DIR:
            return "fail", "MC_BACKUP_DIR is empty. Nothing was copied."
        if extra.lower() != "run":
            nxt = backup_folder_name("manual", int(_backup_state.get("manual_number") or 0) + 1, "date time")
            return "pass", f"next folder under {BACKUP_DIR}: {nxt}"
        if await server_running():
            return (
                "fail",
                "Server is online. /test backup run would copy a live world. Use /backup.",
            )
        code, tail, folder = await perform_backup("manual")
        return ("pass" if code == 0 else "fail"), f"exit {code} {folder}"
    if target == "stats":
        if not extra:
            return "fail", "Pass a player name in extra."
        uuid = await asyncio.to_thread(lookup_uuid, extra)
        stats_file = await asyncio.to_thread(read_player_stats, uuid)
        return ("pass" if uuid else "fail"), (
            f"uuid {uuid}, stats file {'found' if stats_file else 'missing'}"
        )
    return "fail", f"Unknown target `{target}`."


@bot.tree.command(name="test", description="Test one bot system")
@app_commands.describe(
    target="Which system to test",
    extra="Optional seconds, player name, message, or run",
)
@app_commands.choices(target=[
    app_commands.Choice(name=name, value=name) for name in TEST_TARGETS
])
async def test(
    interaction: discord.Interaction,
    target: app_commands.Choice[str],
    extra: typing.Optional[str] = None,
):
    """Slash command: run internal self-tests."""
    if not await gate(interaction):
        return
    target = target.value
    await interaction.response.defer(ephemeral=False)
    names = [name for name in TEST_TARGETS if name != "all"] if target == "all" else [target]
    lines = []
    for name in names:
        if name == "backup" and target == "all":
            lines.append("backup: skipped in all (pass extra `run` on `/test backup`)")
            continue
        if name == "say" and target == "all":
            lines.append("say: skipped in all (it posts in Minecraft chat)")
            continue
        try:
            state, detail = await test_one(name, extra if target != "all" else "")
        except Exception as error:
            state, detail = "fail", repr(error)
        lines.append(f"{name}: {state} — {detail}")
    color = COLOR_BAD if any(line.split(":", 1)[-1].strip().startswith("fail") for line in lines) else COLOR_OK
    await followup_embed(interaction, panel(f"Test {target}", lines, color), ephemeral=False)


# ============================================================
# /PING
# ============================================================

def address_is_public(address):
    """True for a normal public unicast address. Blocks probes of the host's own net."""

    checker = getattr(address, "is_global", None)
    if checker is not None:
        return bool(checker)
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


PLAYER_LOGIN_RE = re.compile(
    r"([A-Za-z0-9_]{1,16})\[/(\[[0-9a-fA-F:]+\]|[0-9.]+):\d+\] logged in"
)


def looks_like_player(target):
    """A player name has letters. An IP does not, so the two cannot be confused."""

    return bool(PLAYER_NAME_RE.fullmatch(target)) and any(ch.isalpha() for ch in target)


def player_login_address(name):
    """Most recent public login address for this player, from latest.log."""

    data = _read_tail(LOG_PATH, 8 * 1024 * 1024)
    if not data:
        return None
    text = data.decode("utf-8", "replace")
    found = None
    for match in PLAYER_LOGIN_RE.finditer(text):
        if match.group(1).lower() == name.lower():
            raw = match.group(2).strip("[]")
            try:
                found = ipaddress.ip_address(raw)
            except ValueError:
                continue
    return found


@bot.tree.command(name="ping", description="Ping a public IP or an online player")
@app_commands.describe(target="Public IP, or a player name such as player123")
async def ping(interaction: discord.Interaction, target: str):
    """Slash command: ping the server or a player."""
    if not await gate(interaction):
        return

    target = target.strip()
    label = target
    try:
        address = ipaddress.ip_address(target)
    except ValueError:
        if not looks_like_player(target):
            await deny(
                interaction,
                "[!] Give a public IP, or a player name like `player123`.",
            )
            return
        await interaction.response.defer()
        ping = await spark_player_ping(target)
        if ping is None:
            await followup_text(interaction, f"[-] No Spark ping for `{target}`. Are they online?")
        else:
            await followup_text(interaction, f"[+] `{target}`: **{ping} ms** (Spark)")
        return

    if not address_is_public(address):
        await deny(
            interaction,
            "[!] That address is not a public IP. Refusing to probe it from the host.",
        )
        return

    await interaction.response.defer()
    result = await icmp_ping(address)
    if result is None:
        await followup_text(interaction, "[!] `ping` isn't available.")
        return
    if result == "timeout":
        await followup_text(interaction, f"[-] Ping to `{label}` timed out.")
        return
    if result.get("avg") is None:
        await followup_text(interaction, f"[-] No reply from `{label}`.")
        return
    await followup_text(
        interaction,
        f"[+] `{label}`: avg **{result['avg']} ms** "
        f"(min {result['min']} / max {result['max']}), {result['loss']} packet loss",
    )


async def icmp_ping(address, count=4, wait=2):
    """ICMP ping. Returns a result dict, 'timeout', or None if ping is missing."""

    wait_flag = "2000" if sys.platform == "darwin" else str(wait)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", str(count), "-W", wait_flag, str(address),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except OSError:
        return None
    try:
        output, _ = await asyncio.wait_for(proc.communicate(), timeout=count * (wait + 2))
    except asyncio.TimeoutError:
        await kill_proc(proc)
        return "timeout"
    text = output.decode(errors="ignore")
    loss = re.search(r"(\d+(?:\.\d+)?)% packet loss", text)
    rtt = re.search(r"= ([\d.]+)/([\d.]+)/([\d.]+)", text)
    if not rtt:
        return {"avg": None, "min": None, "max": None, "loss": "100%"}
    minimum, average, maximum = rtt.groups()
    return {
        "avg": average,
        "min": minimum,
        "max": maximum,
        "loss": f"{loss.group(1)}%" if loss else "?",
    }


async def online_player_names():
    """Names from `list`, or None if the server did not answer."""

    ok, output = await send_console("list")
    if not ok or not output:
        return None
    clean = strip_colors(output)
    if re.search(r"there are\s+0\b", clean, re.IGNORECASE):
        return []
    match = re.search(r"online:\s*(.*)$", clean, re.IGNORECASE)
    if not match or not match.group(1).strip():
        return []
    return [name.strip() for name in match.group(1).split(",") if name.strip()]


async def spark_player_ping(name):
    """Minecraft latency from Spark. None if Spark has no data for that player."""

    safe = re.sub(r"[^A-Za-z0-9_]", "", name)
    if not safe:
        return None
    ok, output = await send_console(f"spark ping --player {safe}")
    if not ok or not output:
        return None
    clean = strip_colors(output)
    match = re.search(r"has\s+([\d.]+)\s*ms", clean, re.IGNORECASE)
    return match.group(1) if match else None


async def player_ping_lines():
    """One line per online player, from Spark. No IPs."""

    names = await online_player_names()
    if names is None:
        return None
    lines = []
    for name in names:
        ping = await spark_player_ping(name)
        lines.append(f"{name}: {ping} ms" if ping is not None else f"{name}: no ping data")
    return lines


async def say_ping_lines(lines):
    """Say the ping list in Minecraft, splitting so a line is not too long."""

    if not lines:
        await say_game("no players online")
        return
    chunk = []
    size = 0
    for line in lines:
        if chunk and size + len(line) + 2 > 160:
            await say_game(", ".join(chunk))
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 2
    if chunk:
        await say_game(", ".join(chunk))


@bot.tree.command(name="pingall", description="Ping every player who is online")
async def pingall(interaction: discord.Interaction):
    """Slash command: ping all online players."""
    if not await gate(interaction):
        return
    await interaction.response.defer()
    lines = await player_ping_lines()
    if lines is None:
        await followup_text(interaction, "[!] Couldn't read the player list or run ping.")
        return
    if not lines:
        await followup_text(interaction, "[-] No players online.")
        return
    await followup_embed(interaction, panel("Player pings", lines, COLOR_INFO))


# ============================================================
# /LOG  (on demand only; /tpslog is this with target tps)
# ============================================================

LOG_TARGETS = ("tps", "health", "rcon", "process", "minecraft", "commands", "alerts")
LOG_DEFAULT_MINUTES = 20
LOG_MAX_MINUTES = 20
LOG_SHOW_LINES = 20
LOG_SAMPLE_SECONDS = {
    "tps": 60,
    "health": 30,
    "rcon": 30,
    "process": 30,
    "minecraft": 15,
    "commands": 5,
    "alerts": 5,
}
log_sessions = {}


def capture_log(target, line):
    """Remember a line only while /log for that target is running."""

    session = log_sessions.get(target)
    if session is None:
        return
    session.add(line)


def append_manual_log(line):
    """/log lines only. Never written into the bot log or latest.log."""

    try:
        os.makedirs(os.path.dirname(MANUAL_LOG_PATH) or ".", exist_ok=True)
        rotate_capped(MANUAL_LOG_PATH, BOT_LOG_MAX_BYTES, LOG_KEEP_HIGH)
        with open(MANUAL_LOG_PATH, "a", encoding="utf-8") as file:
            file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except OSError as error:
        log.warning("Couldn't write manual log %s: %s", MANUAL_LOG_PATH, error)


class DemandLog:
    """A short Discord log. Discord shows the last 20 lines; every line is also
    appended to the manual log file, which rotates at MC_BOT_LOG_MAX_MB."""

    def __init__(self, target, minutes):
        """Internal: init."""
        self.target = target
        self.minutes = minutes
        self.stop = asyncio.Event()
        self.lines = collections.deque(maxlen=LOG_SHOW_LINES)
        self.deadline = time.monotonic() + minutes * 60

    def add(self, line):
        """Add."""
        shown = f"{time.strftime('%H:%M:%S')}  {one_line(redact_ips(line), 160)}"
        self.lines.append(shown)
        append_manual_log(f"[{self.target}] {shown}")

    def render(self, title):
        """Render."""
        body = "\n".join(self.lines) if self.lines else "waiting for a line..."
        return clip_discord(f"{title}\n```\n{body}\n```")


def _log_view(session):
    """Internal: log view."""
    view = discord.ui.View(timeout=session.minutes * 60 + 30)
    button = discord.ui.Button(label="Stop", style=discord.ButtonStyle.danger)

    async def on_click(button_interaction):
        """On click."""
        try:
            if not await gate(button_interaction):
                return
            session.stop.set()
            await button_interaction.response.defer()
        except EDIT_ERRORS:
            pass

    button.callback = on_click
    view.add_item(button)
    return view


async def sample_log(target):
    """Sample recent lines from a log target."""
    if target == "tps":
        result = await get_tps()
        return fmt_tps(*result) if result else "no TPS response"
    if target == "health":
        pid = await find_server_pid()
        if pid is None:
            return "server offline"
        rss, cpu = await process_usage(pid)
        return f"RAM {format_ram(rss)}, CPU {'n/a' if cpu is None else f'{cpu:.0f}%'}"
    if target == "rcon":
        ok, detail = await rcon_diagnose()
        return detail if ok else f"fail: {detail}"
    if target == "process":
        pid = await find_server_pid()
        return "offline" if pid is None else f"pid {pid}"
    if target == "minecraft":
        rows = tail_lines(LOG_PATH, 1)
        return rows[-1] if rows else "no log line"
    return None


async def _safe_message_edit(message, content, **kwargs):
    """Internal: safe message edit."""
    try:
        await message.edit(content=clip_discord(content), **kwargs)
        return True
    except EDIT_ERRORS:
        return False


async def run_demand_log(interaction, session):
    """Stream a log to Discord for a limited time."""
    header = (
        f"Log {session.target} | every {LOG_SAMPLE_SECONDS[session.target]}s | "
        f"{session.minutes} min | last {LOG_SHOW_LINES} lines"
    )
    view = _log_view(session)
    message = None
    # /log is a manual session. It must not share the mc-bot / Minecraft channel.
    append_manual_log(f"--- /log {session.target} started ({session.minutes} min) ---")
    if MANUAL_LOG_CHANNEL_ID:
        try:
            channel = bot.get_channel(MANUAL_LOG_CHANNEL_ID)
            if channel is None:
                channel = await bot.fetch_channel(MANUAL_LOG_CHANNEL_ID)
            message = await channel.send(session.render(header), view=view)
        except EDIT_ERRORS as error:
            log.warning("Demand log couldn't use the manual log channel: %s", error)
            message = None
    if message is None:
        message = await interaction.followup.send(
            session.render(header), view=view, wait=True
        )
        session.deadline = min(session.deadline, time.monotonic() + TOKEN_LIFETIME)
        await interaction.followup.send(
            f"Manual log file: `{MANUAL_LOG_PATH}`"
            + (
                ""
                if MANUAL_LOG_CHANNEL_ID
                else ". Set MC_MANUAL_LOG_CHANNEL_ID to post this away from the bot log."
            ),
            ephemeral=False,
        )
    else:
        await interaction.followup.send(
            f"Logging {session.target} in the manual log channel (not the bot or Minecraft log).",
            ephemeral=False,
        )

    title = header
    try:
        while not session.stop.is_set():
            if session.target == "minecraft":
                for line in tail_lines(LOG_PATH, 3):
                    session.add(line)
            elif session.target not in ("commands", "alerts"):
                try:
                    line = await sample_log(session.target)
                except Exception as error:
                    line = repr(error)
                if line:
                    session.add(line)
            remaining = session.deadline - time.monotonic()
            if remaining <= 0:
                title = f"Log {session.target} finished ({session.minutes} min)"
                break
            if not await _safe_message_edit(message, session.render(header), view=view):
                return
            try:
                await asyncio.wait_for(
                    session.stop.wait(),
                    timeout=min(LOG_SAMPLE_SECONDS[session.target], remaining),
                )
            except asyncio.TimeoutError:
                pass
        else:
            title = f"Log {session.target} stopped"
    finally:
        log_sessions.pop(session.target, None)
        await _safe_message_edit(message, session.render(title), view=None)
        if session.target == "tps":
            try:
                chart = tps_chart(session.minutes * 60, "TPS")
                await message.channel.send(
                    f"TPS graph for the last {session.minutes} minutes.",
                    file=discord.File(io.BytesIO(chart), filename="tps-log.png"),
                )
            except EDIT_ERRORS:
                pass


@bot.tree.command(name="log", description="Start a short log for one system")
@app_commands.describe(
    target="What to log",
    minutes="How long. Default 20, maximum 20",
)
@app_commands.choices(
    target=[
        app_commands.Choice(name="TPS", value="tps"),
        app_commands.Choice(name="Health", value="health"),
        app_commands.Choice(name="RCON", value="rcon"),
        app_commands.Choice(name="Process", value="process"),
        app_commands.Choice(name="Minecraft log", value="minecraft"),
        app_commands.Choice(name="Commands", value="commands"),
        app_commands.Choice(name="Alerts", value="alerts"),
    ],
    minutes=[
        app_commands.Choice(name="5 minutes", value=5),
        app_commands.Choice(name="10 minutes", value=10),
        app_commands.Choice(name="20 minutes", value=20),
    ],
)
async def log_command(
    interaction: discord.Interaction,
    target: app_commands.Choice[str],
    minutes: typing.Optional[app_commands.Choice[int]] = None,
):
    """Slash command: follow a log for a while."""
    if not await gate(interaction):
        return
    target = target.value
    minutes = LOG_DEFAULT_MINUTES if minutes is None else minutes.value
    if target in log_sessions:
        await deny(interaction, f"A {target} log is already running. Press Stop or wait.")
        return

    session = DemandLog(target, minutes)
    log_sessions[target] = session
    try:
        await interaction.response.defer(ephemeral=False)
        await run_demand_log(interaction, session)
    finally:
        log_sessions.pop(target, None)


# ============================================================
# /RCONTEST
# ============================================================

@bot.tree.command(
    name="rcontest",
    description="Test the RCON connection and say what is wrong",
)
async def rcontest(interaction: discord.Interaction):
    """Slash command: diagnose the RCON connection."""
    if not await gate(interaction):
        return

    await interaction.response.defer(ephemeral=False)

    lines = [
        "🔧 **RCON test**",
        f"Target: `{RCON_HOST}:{RCON_PORT}`",
        f"Password in .env: {len(RCON_PASSWORD)} characters"
        if RCON_PASSWORD
        else "Password in .env: **empty**",
    ]
    try:
        running = await server_running()
    except AmbiguousServer:
        running = True
    lines.append(f"Server process: {'running' if running else '**not running**'}")

    ok, detail = await rcon_diagnose()
    log.info("/rcontest result: ok=%s detail=%s", ok, detail)
    if ok:
        lines.append(f"[+] **Works.** Server answered `list`: {detail}")
    else:
        lines.append(f"[-] **Failed:** {detail}")
        if not RCON_PASSWORD:
            lines.append("Set `MC_RCON_PASSWORD` in `.env` and restart the bot.")
        elif not running:
            lines.append("Start the server first, then run this again.")
        elif "refused" in detail or "timed out" in detail:
            lines.append(
                "Check `server.properties`: `enable-rcon=true`, `rcon.port` "
                "equal to `MC_RCON_PORT`, then **restart the Minecraft server** "
                "(RCON settings are only read at startup)."
            )
        elif "password" in detail or "closed the connection" in detail:
            lines.append(
                "`rcon.password` in `server.properties` must match "
                "`MC_RCON_PASSWORD` exactly. Wrap the value in single quotes in "
                "`.env` if it contains `#`, spaces, or quotes, and make sure "
                "`MC_RCON_PORT` is not the game port (25565)."
            )
    await followup_text(interaction, "\n".join(lines), ephemeral=False)


# ============================================================
# /BOTSTOP
# ============================================================

async def _close_bot_soon():
    """Internal: close bot soon."""
    await asyncio.sleep(1)  # let the reply reach Discord first
    log.warning("Stopping the bot (/botstop). The Minecraft server is not touched.")
    await bot.close()


class BotStopView(discord.ui.View):
    """Confirmation view for /botstop."""
    def __init__(self):
        """Internal: init."""
        super().__init__(timeout=30)
        self.message = None

    @discord.ui.button(label="Stop the bot", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        """Confirm."""
        if not await gate(interaction, admin=True):
            return
        cmd_log.warning("/botstop confirmed by %s", describe_user(interaction.user))
        self.stop()
        await interaction.response.edit_message(
            content=(
                "**Stopping the bot...**\n"
                "The Minecraft server keeps running. Start the bot again on "
                "the host to use commands."
            ),
            view=None,
        )
        spawn(_close_bot_soon())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        """Cancel."""
        if not await gate(interaction, admin=True):
            return
        cmd_log.info("/botstop cancelled by %s", describe_user(interaction.user))
        self.stop()
        await interaction.response.edit_message(
            content="Cancelled. The bot keeps running.", view=None
        )

    async def on_timeout(self):
        """On timeout."""
        if self.message is not None:
            try:
                await self.message.edit(content="Timed out. The bot keeps running.", view=None)
            except EDIT_ERRORS:
                pass


async def _reset_bot_soon():
    """Internal: reset bot soon."""
    await asyncio.sleep(1)
    log.warning("Resetting the bot (/botreset). The Minecraft server is not touched.")
    try:
        await bot.close()  # why: os._exit skips shutdown_cleanup (log flush, idle message)
    except Exception as error:
        log.warning("Cleanup before reset failed: %s", error)
    os._exit(1)  # non-zero so systemd Restart=on-failure starts it again


class BotResetView(discord.ui.View):
    """Confirmation view for /botreset."""
    def __init__(self):
        """Internal: init."""
        super().__init__(timeout=30)
        self.message = None

    @discord.ui.button(label="Reset the bot", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction, button):
        """Confirm."""
        if not await gate(interaction, admin=True):
            return
        cmd_log.warning("/botreset confirmed by %s", describe_user(interaction.user))
        self.stop()
        await interaction.response.edit_message(
            content=(
                "**Resetting the bot...**\n"
                "It will be back in a few seconds. The Minecraft server keeps running."
            ),
            view=None,
        )
        spawn(_reset_bot_soon())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction, button):
        """Cancel."""
        if not await gate(interaction, admin=True):
            return
        self.stop()
        await interaction.response.edit_message(
            content="Cancelled. The bot keeps running.", view=None
        )

    async def on_timeout(self):
        """On timeout."""
        if self.message is not None:
            try:
                await self.message.edit(content="Timed out. The bot keeps running.", view=None)
            except EDIT_ERRORS:
                pass


@bot.tree.command(name="botreset", description="Restart this bot (the Minecraft server keeps running)")
async def botreset(interaction: discord.Interaction):
    """Slash command: restart the bot process."""
    if not await gate(interaction, admin=True):
        return
    if _stress_running:
        await deny(interaction, "Cannot reset the bot during a stress test.")
        return
    view = BotResetView()
    note = ""
    if current_op is not None:
        note = f"\n[!] `/{current_op}` is still in progress and will be cut off."
    await interaction.response.send_message(
        "**Reset the bot?**\nIt goes offline, pulls the latest code from GitHub, "
        "then systemd starts it again. The Minecraft server is not stopped." + note,
        view=view,
        ephemeral=False,
    )
    try:
        view.message = await interaction.original_response()
    except EDIT_ERRORS:
        pass


@bot.tree.command(name="botstop", description="Stop this bot (the Minecraft server keeps running)")
async def botstop(interaction: discord.Interaction):
    """Slash command: stop the bot process."""
    if not await gate(interaction, admin=True):
        return
    if _stress_running:
        await deny(interaction, "Cannot stop the bot during a stress test.")
        return

    view = BotStopView()
    note = ""
    if current_op is not None:
        note = f"\n[!] `/{current_op}` is still in progress and will be cut off."
    await interaction.response.send_message(
        "**Stop the bot?**\nThe Minecraft server is not stopped. You will "
        "need to start the bot again on the host." + note,
        view=view,
        ephemeral=False,
    )
    try:
        view.message = await interaction.original_response()
    except EDIT_ERRORS:
        pass


# ============================================================
# /CONSOLE (live console with a command box)
# ============================================================

CONSOLE_INTERVAL = env_int("MC_CONSOLE_INTERVAL", 3, 2)
CONSOLE_MAX_SESSIONS = 3
CONSOLE_TEXT_MAX = 3500     # characters of log shown (an embed holds 4096)
CONSOLE_LINE_MAX = 110
CONSOLE_READ_BYTES = 32 * 1024
CONSOLE_REPLY_MAX = 900
# These would look like a crash to the monitor (and be auto-restarted).
CONSOLE_BLOCKED = {"stop": "/stop", "restart": "/restart"}
CHAT_CONSOLE_COMMANDS = frozenset({
    "say", "tell", "msg", "w", "me", "title", "tellraw", "tm", "teammsg", "whisper",
})


def _console_word(raw):
    """Internal: console word."""
    word = raw.lower()
    if ":" in word:
        word = word.split(":", 1)[1]  # why: spigot:restart / bukkit:stop must not bypass the block
    return word


def blocked_console_command(command):
    """stop/restart as the first word, or after `execute ... run`.

    Chat commands may contain those words. A console stop looks like a crash
    and would be auto-restarted, so it has to go through /stop or /restart.
    Only the first word is matched, so `spark profiler stop` is allowed.
    """

    words = [_console_word(part) for part in command.split()]
    if not words or words[0] in CHAT_CONSOLE_COMMANDS:
        return None
    if words[0] in CONSOLE_BLOCKED:
        return CONSOLE_BLOCKED[words[0]]
    # why: `execute ... run stop` is still a stop even though the first word is execute
    if "run" in words:
        after = words[words.index("run") + 1:]
        if after and after[0] in CONSOLE_BLOCKED:
            return CONSOLE_BLOCKED[after[0]]
    return None


def console_reply_rejected(output):
    """Console reply rejected."""
    return output is not None and re.search(
        r"unknown|incorrect", strip_colors(output), re.IGNORECASE
    ) is not None

console_sessions = set()


def console_tail_text():
    """The newest log lines that fit in one embed, or None if no log file."""

    data = _read_tail(LOG_PATH, CONSOLE_READ_BYTES)
    if data is None:
        return None

    lines = []
    for raw in data.decode("utf-8", "replace").splitlines():
        line = relay_clean(raw).strip()
        if line:
            if len(line) > CONSOLE_LINE_MAX:
                line = line[: CONSOLE_LINE_MAX - 1] + "…"
            lines.append(line)

    if len(data) >= CONSOLE_READ_BYTES and lines:
        lines.pop(0)  # the read started mid-line

    picked, total = [], 0
    for line in reversed(lines):
        total += len(line) + 1
        if total > CONSOLE_TEXT_MAX:
            break
        picked.append(line)
    picked.reverse()
    return "\n".join(picked)


def console_embed(session, text, ended=None):
    """Build the embed for the live console view."""
    if text is None:
        body = f"No log file at {LOG_PATH}\nCheck MC_LOG_PATH in .env."
    else:
        body = text or "(the log is empty)"

    embed = discord.Embed(
        title="Minecraft console",
        description=f"```\n{body}\n```",
        color=0x2ECC71 if session.running else 0xE74C3C,
    )
    if session.last is not None:
        reply = relay_clean(session.last.reply)
        if len(reply) > CONSOLE_REPLY_MAX:
            reply = reply[: CONSOLE_REPLY_MAX - 1] + "…"
        embed.add_field(
            name=clip_discord(f"> {session.last.command}", 250),
            value=f"```\n{reply}\n```",
            inline=False,
        )

    state = "[+] online" if session.running else "[-] offline"
    if ended:
        embed.set_footer(text=f"{state} · {ended}")
    else:
        embed.set_footer(
            text=f"{state} · live, refreshes every {CONSOLE_INTERVAL}s · "
            f"updated {time.strftime('%H:%M:%S')}"
        )
    return embed


async def console_execute(user, command):
    """Send one console command and return the text to show for it."""

    if not command:
        return "Nothing to send."

    blocked = blocked_console_command(command)
    if blocked:
        return (
            f"Use {blocked} instead. A stop from the console looks "
            "like a crash to the bot and would be auto-restarted."
        )

    if current_op in SELF_MANAGED_OPS:
        return f"Busy: /{current_op} is in progress."

    try:
        running = await server_running(force=True)
    except AmbiguousServer:
        return "More than one matching server process. Refusing to send."
    if not running:
        return "The server is offline. Use /start first."

    cmd_log.info("Console command by %s: %s", describe_user(user), one_line(command))
    ok, output = await send_console(command, timeout=10)
    if not ok:
        cmd_log.error("Console command failed to send: %s", one_line(command))
        return "Couldn't send the command (RCON and tmux both failed)."
    if output is None:
        return "Sent through tmux. It returns no reply, look at the console above."

    clean = strip_colors(output).strip()
    cmd_log.info("Console reply: %s", one_line(clean) or "(no output)")
    return clean or "(done, no output)"


class ConsoleSession:
    """One person's live console: an ephemeral message that edits itself."""

    def __init__(self, interaction):
        """Internal: init."""
        self.interaction = interaction
        self.user = interaction.user
        self.stop = asyncio.Event()
        self.wake = asyncio.Event()
        self.deadline = time.monotonic() + TOKEN_LIFETIME
        self.end_reason = "Session ended. Run /console to open it again."
        self.last = None
        self.last_seq = 0
        self.force = True
        self.sig = None
        self.running = False
        self.running_at = -100.0
        self.failures = 0
        self.view = ConsoleView(self)

    def close(self):
        """Close."""
        self.stop.set()
        self.wake.set()

    def poke(self):
        """Poke."""
        self.force = True
        self.wake.set()

    def _signature(self):
        """Internal: signature."""
        try:
            info = os.stat(LOG_PATH)
            file_sig = (info.st_ino, info.st_size, info.st_mtime_ns)
        except OSError:
            file_sig = None
        return (file_sig, self.running, self.last_seq)

    async def _refresh_running(self):
        """Internal: refresh running."""
        now = time.monotonic()
        if now - self.running_at < 10 and not self.force:
            return
        try:
            self.running = await server_running()
        except AmbiguousServer:
            self.running = True
        self.running_at = now

    async def render(self, ended=None):
        """Render."""
        await self._refresh_running()
        sig = self._signature()
        if ended is None and not self.force and sig == self.sig:
            return True  # nothing new: no Discord request at all

        text = await asyncio.to_thread(console_tail_text)
        embed = console_embed(self, text, ended)
        try:
            await self.interaction.edit_original_response(
                content=None, embed=embed, view=None if ended else self.view
            )
        except discord.NotFound:
            self.stop.set()
            return False
        except EDIT_ERRORS as error:
            self.failures += 1
            log.debug("Console edit failed (%s in a row): %r", self.failures, error)
            if self.failures >= 3:
                self.stop.set()
            return False

        self.failures = 0
        self.sig = sig
        self.force = False
        return True

    async def run(self):
        """Run."""
        console_sessions.add(self)
        log.info("Console opened by %s", describe_user(self.user))
        try:
            while not self.stop.is_set():
                await self.render()
                remaining = self.deadline - time.monotonic()
                if remaining <= 0:
                    self.end_reason = "Session expired (Discord limit). Run /console again."
                    break
                try:
                    await asyncio.wait_for(
                        self.wake.wait(), min(CONSOLE_INTERVAL, remaining)
                    )
                except asyncio.TimeoutError:
                    pass
                self.wake.clear()
        finally:
            console_sessions.discard(self)
            log.info(
                "Console closed for %s (%s)", describe_user(self.user), self.end_reason
            )
            try:
                await self.render(ended=self.end_reason)
            except Exception as error:
                log.debug("Final console edit failed: %r", error)


class ConsoleCommandModal(discord.ui.Modal, title="Minecraft console"):
    """Modal that collects a console command to run."""
    command = discord.ui.TextInput(
        label="Command (without the /)",
        placeholder="list    say hello    time set day",
        max_length=200,
    )

    def __init__(self, session):
        """Internal: init."""
        super().__init__()
        self.session = session

    async def on_submit(self, interaction):
        """On submit."""
        if not await gate(interaction, admin=True):
            return
        await interaction.response.defer()

        text = re.sub(r"\s+", " ", str(self.command.value)).strip().lstrip("/").strip()
        reply = await console_execute(interaction.user, text)
        self.session.last = SimpleNamespace(command=text or "(empty)", reply=reply)
        self.session.last_seq += 1
        await asyncio.sleep(0.6)  # let the server write its answer to the log
        self.session.poke()

    async def on_error(self, interaction, error):
        """On error."""
        log.error("Console command box failed: %r", error, exc_info=error)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("[!] Something went wrong.", ephemeral=False)
            else:
                await interaction.response.send_message(
                    "[!] Something went wrong.", ephemeral=False
                )
        except EDIT_ERRORS:
            pass


class ConsoleView(discord.ui.View):
    """Persistent view for the live console session."""
    def __init__(self, session):
        """Internal: init."""
        super().__init__(timeout=None)  # the session decides when it ends
        self.session = session

    async def interaction_check(self, interaction):
        """Interaction check."""
        return await gate(interaction, admin=True)

    @discord.ui.button(label="Command", style=discord.ButtonStyle.primary, row=0)
    async def send(self, interaction, button):
        """Send."""
        await interaction.response.send_modal(ConsoleCommandModal(self.session))

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, row=0)
    async def refresh(self, interaction, button):
        """Refresh."""
        self.session.poke()
        await interaction.response.defer()

    @discord.ui.button(label="Close window", style=discord.ButtonStyle.danger, row=1)
    async def close_console(self, interaction, button):
        """Close console."""
        self.session.end_reason = "Closed."
        self.session.close()
        await interaction.response.defer()


def claim_console_slot(interaction):
    """Reserve a console before the first await so two /console calls cannot both pass."""

    for old in list(console_sessions):
        if old.user.id == interaction.user.id:
            old.end_reason = "Replaced by a newer /console."
            old.close()
    if len([s for s in console_sessions if not s.stop.is_set()]) >= CONSOLE_MAX_SESSIONS:
        return None
    session = ConsoleSession(interaction)
    console_sessions.add(session)
    return session


@bot.tree.command(
    name="console",
    description="Live Minecraft console with a box to type commands",
)
async def console(interaction: discord.Interaction):
    """Slash command: open a live console session."""
    if not await gate(interaction, admin=True):
        return

    session = claim_console_slot(interaction)
    if session is None:
        await deny(
            interaction,
            f"{CONSOLE_MAX_SESSIONS} consoles are already open. Close a window first.",
        )
        return

    try:
        await interaction.response.defer(ephemeral=False)
    except BaseException:
        console_sessions.discard(session)
        raise
    spawn(session.run())


# ============================================================
# /SERVEREDIT (server.properties, only while the server is offline)
# ============================================================

PROPS_PATH = os.path.expanduser(os.getenv("MC_PROPERTIES_PATH", "").strip()) or os.path.join(
    SERVER_DIR or os.path.dirname(os.path.dirname(LOG_PATH)), "server.properties"
)

PROP_KEY_RE = re.compile(r"^([A-Za-z0-9_.\-]+)[ \t]*[=:][ \t]*(.*)$")

PROP_SECRET = frozenset(
    {"rcon.password", "management-server-secret", "management-server-tls-keystore-password"}
)
PROP_ENUMS = {
    "difficulty": ("peaceful", "easy", "normal", "hard"),
    "gamemode": ("survival", "creative", "adventure", "spectator"),
    "region-file-compression": ("deflate", "lz4", "none"),
    "level-type": (
        "minecraft:normal",
        "minecraft:flat",
        "minecraft:large_biomes",
        "minecraft:amplified",
        "minecraft:single_biome_surface",
    ),
}
_INT_MAX = 2**31 - 1
PROP_INTS = {
    "view-distance": (3, 32),
    "simulation-distance": (3, 32),
    "max-players": (0, _INT_MAX),
    "server-port": (1, 65535),
    "rcon.port": (1, 65535),
    "query.port": (1, 65535),
    "spawn-protection": (0, _INT_MAX),
    "max-world-size": (1, 29999984),
    "entity-broadcast-range-percentage": (10, 1000),
    "op-permission-level": (0, 4),
    "function-permission-level": (1, 4),
    "player-idle-timeout": (0, _INT_MAX),
    "max-tick-time": (-1, 2**63 - 1),
    "network-compression-threshold": (-1, _INT_MAX),
    "pause-when-empty-seconds": (-1, _INT_MAX),
    "rate-limit": (0, _INT_MAX),
    "max-chained-neighbor-updates": (-1, _INT_MAX),
    "chat-spam-threshold-seconds": (0, _INT_MAX),
    "command-spam-threshold-seconds": (0, _INT_MAX),
}
PROP_BOOLS = frozenset(
    {
        "allow-flight", "enable-rcon", "enable-query", "enable-status", "online-mode",
        "pvp", "hardcore", "white-list", "enforce-whitelist", "force-gamemode",
        "generate-structures", "spawn-monsters", "spawn-animals", "spawn-npcs",
        "allow-nether", "hide-online-players", "enforce-secure-profile",
        "prevent-proxy-connections", "sync-chunk-writes", "use-native-transport",
        "log-ips", "broadcast-console-to-ops", "broadcast-rcon-to-ops",
        "require-resource-pack", "enable-command-block", "accepts-transfers",
    }
)
# Never treated as a number even when the current value looks like one.
PROP_TEXT = frozenset(
    {
        "level-seed", "level-name", "motd", "generator-settings", "server-ip",
        "resource-pack", "resource-pack-id", "resource-pack-prompt",
        "resource-pack-sha1", "bug-report-link", "initial-enabled-packs",
        "initial-disabled-packs", "text-filtering-config",
        "management-server-allowed-origins", "management-server-host",
    }
)
PROP_KNOWN = frozenset(PROP_INTS) | PROP_BOOLS | frozenset(PROP_ENUMS) | PROP_TEXT

_RCON_NOTE = (
    "Keep `MC_RCON_PORT` / `MC_RCON_PASSWORD` in the bot's `.env` the same, "
    "or the bot loses RCON."
)
PROP_NOTES = {
    "enable-rcon": _RCON_NOTE,
    "rcon.port": _RCON_NOTE,
    "level-name": "A new `level-name` makes the server generate a new world on the next start.",
    "level-seed": "A seed only applies to worlds that are newly generated.",
    "server-port": "Players have to join with the new port.",
    "online-mode": "Turning this off lets anyone join with any name.",
}

_UNESCAPES = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}


def props_unescape(raw):
    """Unescape a server.properties value."""
    def repl(match):
        """Repl."""
        token = match.group(1)
        if token[0] == "u" and len(token) == 5:
            return chr(int(token[1:], 16))
        return _UNESCAPES.get(token, token)

    text = re.sub(r"\\(u[0-9a-fA-F]{4}|.)", repl, raw)
    # \ud83d\ude00 style pairs decode to two surrogates; join them
    try:
        return text.encode("utf-16", "surrogatepass").decode("utf-16")
    except UnicodeError:
        return text


def props_escape(value):
    """Escape a value for server.properties."""
    out = []
    for index, char in enumerate(value):
        if char == "\\":
            out.append("\\\\")
        elif char in ":=#!":
            out.append("\\" + char)
        elif char == " " and index == 0:
            out.append("\\ ")
        elif ord(char) > 126:
            data = char.encode("utf-16-be")
            for pos in range(0, len(data), 2):
                out.append("\\u%04X" % int.from_bytes(data[pos : pos + 2], "big"))
        else:
            out.append(char)
    return "".join(out)


def props_read_text():
    """(text, encoding). A classic ISO-8859-1 file is not rewritten as UTF-8."""

    with open(PROPS_PATH, "rb") as file:
        data = file.read()
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def props_load():
    """(lines, {key: [(line_index, raw_value), ...]}, encoding). Raises OSError."""

    text, encoding = props_read_text()
    lines = re.findall(r"[^\n]*\n|[^\n]+", text)
    found = {}
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped[0] in "#!":
            continue
        match = PROP_KEY_RE.match(stripped)
        if match:
            found.setdefault(match.group(1), []).append((index, match.group(2)))
    return lines, found, encoding


def props_current(found, key):
    """Props current."""
    return props_unescape(found[key][-1][1]) if key in found else ""


def props_display(key, value, width=80):
    """Format a server.properties value for display."""
    if key in PROP_SECRET:
        return "(set, hidden)" if value else "(empty)"
    if value == "":
        return "(empty)"
    return value if len(value) <= width else value[: width - 1] + "…"


def props_kind(key, current):
    """Classify a server.properties key."""
    if key in PROP_ENUMS:
        return "options: " + ", ".join(PROP_ENUMS[key])
    if key in PROP_TEXT:
        return "text"
    if key in PROP_BOOLS or current.lower() in ("true", "false"):
        return "true or false"
    if key in PROP_INTS:
        low, high = PROP_INTS[key]
        return f"number from {low} to {high}" if high < _INT_MAX else f"number, minimum {low}"
    if re.fullmatch(r"-?\d+", current):
        return "number"
    return "text"


def props_validate(key, value, current):
    """(clean value, None) or (None, error message)."""

    value = value.strip()
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None, "The value can't contain line breaks or control characters."
    if len(value) > 500:
        return None, "The value is too long (500 characters max)."
    value = value.replace("\\:", ":").replace("\\=", "=")

    if key in PROP_ENUMS:
        low = value.lower()
        for option in PROP_ENUMS[key]:
            if low in (option.lower(), option.split(":")[-1].lower()):
                return option, None
        return None, f"`{key}` must be one of: " + ", ".join(f"`{o}`" for o in PROP_ENUMS[key])

    if key not in PROP_TEXT:
        if key in PROP_BOOLS or current.lower() in ("true", "false"):
            low = value.lower()
            if low in ("true", "yes", "on", "1"):
                return "true", None
            if low in ("false", "no", "off", "0"):
                return "false", None
            return None, f"`{key}` must be `true` or `false`."

        if key in PROP_INTS or re.fullmatch(r"-?\d+", current):
            if not re.fullmatch(r"-?\d+", value):
                return None, f"`{key}` must be a whole number."
            number = int(value)
            low, high = PROP_INTS.get(key, (-_INT_MAX - 1, _INT_MAX))
            if not low <= number <= high:
                return None, f"`{key}` must be between {low} and {high}."
            return str(number), None

    return value, None


def props_edit(key_input, value_input):
    """Blocking: validate and write one setting. Raises OSError on file problems."""

    key = key_input.strip().lower().replace(" ", "-")
    if key.replace("_", "-") in PROP_KNOWN:
        key = key.replace("_", "-")

    lines, found, encoding = props_load()

    if key in PROP_SECRET:
        return SimpleNamespace(
            ok=False,
            changed=False,
            log=f"{key}: blocked",
            message=f"🔒 `{key}` is a secret. Change it by editing the file on the host.",
        )

    if key not in found and key not in PROP_KNOWN:
        close = difflib.get_close_matches(key, list(found), n=3, cutoff=0.6)
        hint = " Did you mean " + ", ".join(f"`{k}`" for k in close) + "?" if close else ""
        return SimpleNamespace(
            ok=False, changed=False, log=f"{key}: unknown", message=f"Unknown setting `{key}`.{hint}"
        )

    current = props_current(found, key)
    value, error = props_validate(key, value_input, current)
    if error:
        return SimpleNamespace(ok=False, changed=False, log=f"{key}: {error}", message=f"[!] {error}")

    if key in found and value == current:
        return SimpleNamespace(
            ok=True,
            changed=False,
            log=f"{key}: already {value!r}",
            message=f"`{key}` is already `{props_display(key, value)}`. Nothing changed.",
        )

    escaped = props_escape(value)
    out = list(lines)
    crlf = any(line.endswith("\r\n") for line in lines)
    if key in found:
        for index, _ in found[key]:
            line = out[index]
            ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            out[index] = f"{key}={escaped}{ending}"
    else:
        ending = "\r\n" if crlf else "\n"
        if out and not out[-1].endswith("\n"):
            out[-1] += ending
        out.append(f"{key}={escaped}{ending}")

    directory = os.path.dirname(PROPS_PATH) or "."
    backup = PROPS_PATH + ".bot-backup"
    temp = os.path.join(directory, ".server.properties.bot-tmp")
    try:
        shutil.copy2(PROPS_PATH, backup)
        try:
            os.chmod(backup, 0o600)  # why: copy2 keeps 0644, which exposes rcon.password
        except OSError as error:
            log.warning("Couldn't restrict permissions on %s: %s", backup, error)
        with open(temp, "w", encoding=encoding, newline="") as file:
            file.write("".join(out))
            file.flush()
            os.fsync(file.fileno())
        try:
            shutil.copymode(PROPS_PATH, temp)
        except OSError:
            pass
        try:
            os.chmod(temp, 0o600)  # why: the file os.replace puts in place must not be world-readable
        except OSError as error:
            log.warning("Couldn't restrict permissions on %s: %s", temp, error)
        os.replace(temp, PROPS_PATH)
    except OSError as error:
        raise OSError(
            error.errno,
            f"couldn't write temp file next to server.properties ({error.strerror or error})",
        ) from error
    finally:
        if os.path.exists(temp):
            try:
                os.remove(temp)
            except OSError:
                pass

    old_text = props_display(key, current)
    new_text = props_display(key, value)
    message = f"✅ `{key}`: `{old_text}` → `{new_text}`\nTakes effect on the next `/start`."
    if key in PROP_NOTES:
        message += f"\n[!] {PROP_NOTES[key]}"
    return SimpleNamespace(
        ok=True, changed=True, log=f"{key}: {old_text!r} -> {new_text!r}", message=message
    )


def log_props_note():
    """Log props note."""
    if os.path.isfile(PROPS_PATH):
        log.info("/serveredit edits %s", PROPS_PATH)
    else:
        log.warning(
            "server.properties not found at %s. /serveredit won't work until "
            "MC_PROPERTIES_PATH points to it.",
            PROPS_PATH,
        )


def _props_missing_text(error):
    """Internal: props missing text."""
    if isinstance(error, FileNotFoundError):
        return (
            f"[!] Can't find `{PROPS_PATH}`.\nSet `MC_PROPERTIES_PATH` in `.env` "
            "to the real server.properties path and restart the bot."
        )
    return f"[!] Can't use `{PROPS_PATH}`: {error.strerror or error}"


async def serveredit_list(interaction):
    """List editable server.properties keys."""
    try:
        _, found, _encoding = await asyncio.to_thread(props_load)
    except OSError as error:
        await followup_text(interaction, _props_missing_text(error), ephemeral=False)
        return

    rows = [
        f"{key} = {props_display(key, props_current(found, key), 50)}" for key in found
    ]
    chunks, current, size = [], [], 0
    for row in rows:
        if current and size + len(row) + 1 > 1800:
            chunks.append(current)
            current, size = [], 0
        current.append(row)
        size += len(row) + 1
    if current:
        chunks.append(current)

    for number, chunk in enumerate(chunks, 1):
        head = f"⚙️ **server.properties** ({number}/{len(chunks)})\n" if len(chunks) > 1 else "⚙️ **server.properties**\n"
        await followup_text(interaction, head + "```\n" + "\n".join(chunk) + "\n```", ephemeral=False)
    await followup_text(
        interaction,
        "Change one with `/serveredit setting:view-distance value:12` "
        "(the server has to be offline).",
        ephemeral=False,
    )


async def serveredit_show(interaction, setting):
    """Show the current value of a server.properties key."""
    try:
        _, found, _encoding = await asyncio.to_thread(props_load)
    except OSError as error:
        await followup_text(interaction, _props_missing_text(error), ephemeral=False)
        return

    key = setting.strip().lower().replace(" ", "-")
    if key.replace("_", "-") in PROP_KNOWN:
        key = key.replace("_", "-")
    if key not in found:
        close = difflib.get_close_matches(key, list(found), n=3, cutoff=0.6)
        hint = " Did you mean " + ", ".join(f"`{k}`" for k in close) + "?" if close else ""
        await followup_text(interaction, f"Unknown setting `{key}`.{hint}", ephemeral=False)
        return

    current = props_current(found, key)
    await followup_text(
        interaction,
        f"⚙️ `{key}` = `{props_display(key, current, 300)}`\n"
        f"Accepts: {props_kind(key, current)}",
        ephemeral=False,
    )


async def serveredit_apply(interaction, setting, value):
    """Apply a change to server.properties."""
    try:
        running = await server_running(force=True)
    except AmbiguousServer:
        await followup_text(
            interaction,
            "[!] More than one matching server process, so I can't tell the server is off. Not editing.",
            ephemeral=False,
        )
        return
    if running:
        await followup_text(
            interaction,
            "[-] **The server is running.** Settings can only be changed while it's offline.\n"
            "Use `/stop`, edit, then `/start`.",
            ephemeral=False,
        )
        return

    try:
        result = await asyncio.to_thread(props_edit, setting, value)
    except OSError as error:
        log.error("serveredit failed: %r", error)
        await followup_text(interaction, _props_missing_text(error), ephemeral=False)
        return

    log.info("serveredit by %s: %s", describe_user(interaction.user), result.log)
    await followup_text(interaction, result.message, ephemeral=False)


@bot.tree.command(
    name="serveredit",
    description="View or change server.properties (changes need the server offline)",
)
@app_commands.describe(
    setting="Setting name, e.g. view-distance. Leave empty to list every setting",
    value="New value, e.g. 12 or true. Leave empty to just see the current value",
)
async def serveredit(
    interaction: discord.Interaction,
    setting: typing.Optional[str] = None,
    value: typing.Optional[str] = None,
):
    """Slash command: view or edit server.properties."""
    if not await gate(interaction, admin=True):
        return

    setting = (setting or "").strip()
    editing = bool(setting) and value is not None and value.strip() != ""

    if not await begin(interaction, "serveredit" if editing else None, ephemeral=False):
        return
    try:
        if not setting:
            if value:
                await followup_text(
                    interaction, "Pick a `setting` as well as a `value`.", ephemeral=False
                )
            else:
                await serveredit_list(interaction)
        elif not editing:
            await serveredit_show(interaction, setting)
        else:
            await serveredit_apply(interaction, setting, value)
    finally:
        if editing:
            release()


@serveredit.autocomplete("setting")
async def serveredit_setting_choices(interaction: discord.Interaction, current: str):
    """Serveredit setting choices."""
    if guild_problem(interaction) or not member_is_admin(interaction):
        return []
    try:
        _, found, _encoding = await asyncio.to_thread(props_load)
    except OSError:
        return []

    needle = current.strip().lower().replace("_", "-").replace(" ", "-")
    keys = [key for key in found if needle in key]
    keys += [key for key in sorted(PROP_KNOWN) if key not in found and needle in key]
    keys.sort(key=lambda key: (not key.startswith(needle), key))

    choices = []
    for key in keys[:25]:
        label = f"{key} = {props_display(key, props_current(found, key), 40)}" if key in found else key
        choices.append(app_commands.Choice(name=label[:100], value=key))
    return choices


@serveredit.autocomplete("value")
async def serveredit_value_choices(interaction: discord.Interaction, current: str):
    """Serveredit value choices."""
    if guild_problem(interaction) or not member_is_admin(interaction):
        return []
    key = (getattr(interaction.namespace, "setting", None) or "").strip().lower()
    if key in PROP_SECRET:
        return []

    options = []
    if key in PROP_ENUMS:
        options = [o.split(":")[-1] if key != "level-type" else o for o in PROP_ENUMS[key]]
    else:
        try:
            _, found, _encoding = await asyncio.to_thread(props_load)
        except OSError:
            return []
        value_now = props_current(found, key)
        if key not in PROP_TEXT and (key in PROP_BOOLS or value_now.lower() in ("true", "false")):
            options = ["true", "false"]
        elif value_now:
            options = [value_now]

    needle = current.strip().lower()
    return [
        app_commands.Choice(name=option[:100], value=option)
        for option in options
        if needle in option.lower()
    ][:25]


# ============================================================
# /PANEL
# ============================================================

class PanelView(discord.ui.View):
    """The everyday controls. Choices are a menu, actions are buttons."""

    def __init__(self):
        """Internal: init."""
        super().__init__(timeout=600)
        self.message = None
        self.handed_off = False
        self.add_item(LogSelect())

    async def interaction_check(self, interaction):
        """Interaction check."""
        return await gate(interaction)

    async def on_timeout(self):
        """On timeout."""
        if self.handed_off:
            return  # why: console owns this message and can still be live past 10 minutes
        for child in self.children:
            child.disabled = True
        if self.message is None:
            return
        try:
            await self.message.edit(content="Panel expired. Run /panel again.", view=self)
        except EDIT_ERRORS:
            pass

    @discord.ui.button(label="Status", style=discord.ButtonStyle.secondary, row=0)
    async def status_button(self, interaction, button):
        """Status button."""
        await status.callback(interaction)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.success, row=0)
    async def start_button(self, interaction, button):
        """Start button."""
        await start.callback(interaction)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.secondary, row=0)
    async def save_button(self, interaction, button):
        """Save button."""
        await save.callback(interaction)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, row=1)
    async def stop_button(self, interaction, button):
        """Stop button."""
        await stop.callback(interaction)

    @discord.ui.button(label="Restart", style=discord.ButtonStyle.danger, row=1)
    async def restart_button(self, interaction, button):
        """Restart button."""
        await restart.callback(interaction)

    @discord.ui.button(label="Console", style=discord.ButtonStyle.primary, row=1)
    async def console_button(self, interaction, button):
        """Console button."""
        session = claim_console_slot(interaction)
        if session is None:
            await deny(
                interaction,
                f"{CONSOLE_MAX_SESSIONS} consoles are already open. Close a window first.",
            )
            return
        self.handed_off = True  # why: console reuses this message; panel timeout must not overwrite it
        self.stop()
        try:
            await interaction.response.defer(ephemeral=False)
        except BaseException:
            console_sessions.discard(session)
            self.handed_off = False
            raise
        spawn(session.run())

    @discord.ui.button(label="Close panel", style=discord.ButtonStyle.secondary, row=3)
    async def close_panel(self, interaction, button):
        """Close panel."""
        await interaction.response.edit_message(content="Panel closed.", embed=None, view=None)
        self.stop()


class LogSelect(discord.ui.Select):
    """Select menu for choosing a log target."""
    def __init__(self):
        """Internal: init."""
        super().__init__(
            placeholder="Log a system for 20 minutes",
            min_values=1,
            max_values=1,
            row=2,
            options=[
                discord.SelectOption(label="TPS", value="tps"),
                discord.SelectOption(label="Health", value="health"),
                discord.SelectOption(label="RCON", value="rcon"),
                discord.SelectOption(label="Process", value="process"),
                discord.SelectOption(label="Minecraft log", value="minecraft"),
                discord.SelectOption(label="Commands", value="commands"),
                discord.SelectOption(label="Alerts", value="alerts"),
            ],
        )

    async def callback(self, interaction):
        """Callback."""
        if not await gate(interaction):
            return
        target = self.values[0]
        if target in log_sessions:
            await deny(interaction, f"A {target} log is already running. Press Stop on it.")
            return
        session = DemandLog(target, LOG_DEFAULT_MINUTES)
        log_sessions[target] = session
        try:
            await interaction.response.defer(ephemeral=False)
            await run_demand_log(interaction, session)
        finally:
            log_sessions.pop(target, None)


async def panel_embed():
    """Build the control-panel embed."""
    pid = await find_server_pid()
    if pid is None:
        return panel("Server", ["Offline", "Use Start, or open the console after it is up."], COLOR_BAD)
    age, info = await asyncio.gather(server_age(pid), get_player_info())
    lines = [format_players(info)]
    if age is not None:
        lines.append(f"Uptime: {format_uptime(age)}")
    lines.append("Stop and Restart ask for confirmation. Console has its own close button.")
    return panel("Server", lines, COLOR_OK)


@bot.tree.command(name="panel", description="Server controls: buttons for actions, a menu for logs")
async def panel_command(interaction: discord.Interaction):
    """Slash command: show the control panel."""
    if not await gate(interaction):
        return
    await interaction.response.defer()
    view = PanelView()
    view.message = await interaction.followup.send(
        embed=await panel_embed(), view=view, wait=True
    )


# ============================================================
# START
# ============================================================

def acquire_instance_lock():
    """Refuse to run twice: two bots would double every alert and restart."""

    try:
        import fcntl
    except ImportError:  # not available on Windows
        return None

    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    handle = open(LOCK_PATH, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit("Another instance of this bot is already running.")
    return handle  # keep a reference so the lock lives as long as the process


def discord_reachable():
    """True when discord.com resolves. A route with no DNS still counts as down."""

    try:
        socket.getaddrinfo("discord.com", 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def network_signature():
    """Changes when the route, DNS config, or Discord reachability changes."""

    chunks = []
    try:
        chunks.append(
            subprocess.check_output(
                ["ip", "-4", "route", "show", "default"], text=True, timeout=3
            ).strip()
        )
    except (OSError, subprocess.SubprocessError):
        chunks.append("no-route")
    try:
        chunks.append(open("/etc/resolv.conf", encoding="utf-8").read())
    except OSError:
        chunks.append("no-resolv")
    chunks.append("dns-ok" if discord_reachable() else "dns-fail")
    return "\n".join(chunks)


async def run_bot_forever():
    """Stay up without internet.

    Try Discord once a minute for 5 minutes. If that fails, wait until the
    network changes, then do the same 5 tries again. /botstop still exits.
    """

    last_signature = None
    while True:
        if last_signature is not None:
            log.warning("Discord failed 5 times. Waiting for the network to change.")
            while await asyncio.to_thread(network_signature) == last_signature:
                await asyncio.sleep(5)
        for attempt in range(1, 6):
            if not await asyncio.to_thread(discord_reachable):
                log.warning("Discord is unreachable (try %s/5). Next try in 60s.", attempt)
                await asyncio.sleep(60)
                continue
            try:
                await bot.start(TOKEN)
                log.info("Bot stopped cleanly.")
                return
            except (KeyboardInterrupt, asyncio.CancelledError):
                return
            except discord.LoginFailure:
                log.error("Discord rejected the token. Not retrying.")
                raise
            except discord.PrivilegedIntentsRequired:
                log.error("Privileged intents are not enabled. Not retrying.")
                raise
            except Exception as error:
                if bot.is_closed():
                    # /botstop, SIGTERM or a fatal close: shutdown_cleanup already ran
                    # and discord.py can't reconnect a closed client.
                    log.warning("Discord client is closed (%s). Not retrying.", error)
                    return
                # Don't close() the shared client here. That runs shutdown_cleanup
                # (monitor, relay and RCON torn down for good) and makes the next
                # start() return immediately.
                log.warning("Discord connection failed (%s). Try %s/5.", error, attempt)
                await asyncio.sleep(60)
        last_signature = await asyncio.to_thread(network_signature)


UPDATE_LOG = os.path.join(BOT_LOG_DIR, "update.log")
GIT_TIMEOUT = 45
COMPILE_TIMEOUT = 20


def update_log(message):
    """Print and append. This runs before the normal logger exists."""

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{stamp} {message}"
    print(line, flush=True)
    try:
        os.makedirs(BOT_LOG_DIR, exist_ok=True)
        with open(UPDATE_LOG, "a", encoding="utf-8") as file:
            file.write(line + "\n")
    except OSError as error:
        print(f"{stamp} could not write {UPDATE_LOG}: {error}", flush=True)


def _git(args, timeout=GIT_TIMEOUT):
    """Run a git command and return its output."""
    return subprocess.run(
        ["git", *args], cwd=BASE_DIR, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def update_from_github():
    """Check GitHub, download if newer, verify, then restart onto the new file.

    1. fetch origin and compare HEAD to origin/main
    2. if newer, pull it onto this checkout
    3. confirm the local commit is origin/main and the file compiles
    4. exit so systemd starts the new code
    """

    if not os.path.isdir(os.path.join(BASE_DIR, ".git")):
        update_log("Not a git checkout. Skipping GitHub update.")
        return
    try:
        fetched = _git(["fetch", "origin", "main"], timeout=GIT_TIMEOUT)
        local = _git(["rev-parse", "HEAD"], timeout=10)
        remote = _git(["rev-parse", "origin/main"], timeout=10)
    except subprocess.TimeoutExpired as error:
        update_log(f"GitHub check timed out after {error.timeout}s ({error.cmd})")
        return
    except OSError as error:
        update_log(f"GitHub check failed: {error}")
        return
    if fetched.returncode != 0 or local.returncode != 0 or remote.returncode != 0:
        update_log(
            "GitHub check failed "
            f"(fetch={fetched.returncode}, local={local.returncode}, remote={remote.returncode})\n"
            f"{fetched.stdout}{local.stdout}{remote.stdout}".rstrip()
        )
        return
    if local.stdout.strip() == remote.stdout.strip():
        update_log(f"GitHub is current ({local.stdout.strip()[:8]}).")
        return
    previous = local.stdout.strip()
    update_log(f"Update found ({previous[:8]} -> {remote.stdout.strip()[:8]}). Downloading.")
    try:
        pulled = _git(["pull", "--ff-only", "origin", "main"], timeout=GIT_TIMEOUT)
        now = _git(["rev-parse", "HEAD"], timeout=10)
    except subprocess.TimeoutExpired as error:
        update_log(f"Download timed out after {error.timeout}s. Not restarting.")
        return
    except OSError as error:
        update_log(f"Download failed: {error}")
        return
    if pulled.returncode != 0 or now.stdout.strip() != remote.stdout.strip():
        update_log(
            "Download did not match origin/main. Not restarting. "
            f"pull={pulled.returncode} head={now.stdout.strip()[:8]} "
            f"wanted={remote.stdout.strip()[:8]}\n{pulled.stdout}".rstrip()
        )
        return
    try:
        try:
            src_name = os.path.basename(os.path.abspath(__file__))
        except NameError:
            src_name = "botgrok.py"
            log.warning("No __file__; update compile check falling back to botgrok.py")
        # why: the running file may not be named botgrok.py; a missing path fails compile and rolls back forever
        check = subprocess.run(
            [sys.executable, "-m", "py_compile", os.path.join(BASE_DIR, src_name)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=COMPILE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        update_log(f"Compile check timed out after {COMPILE_TIMEOUT}s. Not restarting.")
        return
    except OSError as error:
        update_log(f"Compile check failed: {error}")
        return
    if check.returncode != 0:
        update_log(f"Downloaded file does not compile. Rolling back.\n{check.stdout}".rstrip())
        rolled = _git(["reset", "--hard", previous], timeout=20)
        update_log(
            "Rolled back." if rolled.returncode == 0
            else f"Rollback failed.\n{rolled.stdout}".rstrip()
        )
        return
    update_log(f"Download verified ({now.stdout.strip()[:8]}). Restarting onto the new code.")
    os._exit(1)


def main():
    """Entry point: lock, update check, and run the bot."""
    if not TOKEN:
        raise SystemExit(
            f"DISCORD_TOKEN is missing from {os.path.join(BASE_DIR, '.env')}"
        )
    update_from_github()
    _lock = acquire_instance_lock()  # noqa: F841
    try:
        asyncio.run(run_bot_forever())
    except KeyboardInterrupt:
        log.info("Interrupted, shutting down")


if __name__ == "__main__":
    main()

