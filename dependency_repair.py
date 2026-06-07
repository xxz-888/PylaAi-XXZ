import os
import subprocess
import sys


DISCORD_RUNTIME_REQUIREMENT = "discord.py==2.4.0"
DISCORD_CONFLICT_PACKAGES = [
    "discord",
    "discord.py",
    "py-cord",
    "nextcord",
    "disnake",
]


def discord_runtime_is_healthy():
    try:
        import discord
        from discord import Webhook, app_commands
    except Exception:
        return False

    return bool(
        getattr(discord, "__version__", None)
        and Webhook is not None
        and app_commands is not None
    )


def repair_discord_runtime(restart=False):
    print("Repairing Discord Python dependency...")
    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", *DISCORD_CONFLICT_PACKAGES],
        check=False,
    )
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "--force-reinstall",
        DISCORD_RUNTIME_REQUIREMENT,
    ])

    if restart:
        os.execv(sys.executable, [sys.executable] + sys.argv)


def repair_discord_runtime_before_import():
    if discord_runtime_is_healthy():
        return

    if os.environ.get("PYLAAI_DISCORD_REPAIR") == "1":
        message = (
            "Discord Python dependency is still broken after repair. Run:\n"
            f'"{sys.executable}" -m pip uninstall -y discord discord.py py-cord nextcord disnake\n'
            f'"{sys.executable}" -m pip install --force-reinstall {DISCORD_RUNTIME_REQUIREMENT}'
        )
        print(message)
        raise RuntimeError(message)

    os.environ["PYLAAI_DISCORD_REPAIR"] = "1"
    repair_discord_runtime(restart=True)
