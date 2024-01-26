r"""
watchdog.py
 ╔═══════════════════════════╗
 ║ ╦═╗╦╔╦╗╔═╗╦ ╦╔═╗╦═╗╔═╗╔═╗ ║
 ║ ╠═╣║ ║ ╚═╗╠═╣╠═╣╠╦╝╠═ ╚═╗ ║
 ║ ╩═╝╩ ╩ ╚═╝╩ ╩╩ ╩╩╚═╚═╝╚═╝ ║
 ║   ╔═╗╔═╗╔╦╗╔═╗╦ ╦╔═╗╦ ╦   ║
 ║   ║ ╦╠═╣ ║ ╠═ ║║║╠═╣╚╦╝   ║
 ║   ╚═╝╩ ╩ ╩ ╚═╝╚╩╝╩ ╩ ╩    ║
 ║╔═╗ _                 _ ┌─┐║
 ║╚═╝  \               /  └─┘║
 ║╔═╗ _ \             / _ ┌─┐║
 ║╚═╝  \  ╔═╗ ---> ┌─┐ /  └─┘║
 ║╔═╗ _/  ╚═╝ <--- └─┘ \_ ┌─┐║
 ║╚═╝   /             \   └─┘║
 ║╔═╗ _/               \_ ┌─┐║
 ║╚═╝                     └─┘║
 ╚═══════════════════════════╝
WTFPL litepresence.com Jan 2024

Ensure all child processes are alive when main is alive and provide alert if they are not.
Ensure all child processes are killed when main is terminated.
"""

# STANDARD MODULES
import json
import sys
import time

# GATEWAY MODULES
from config import processes, timing
from ipc_utilities import json_ipc
from utilities import it


def alert(process: str, stale: int, data: dict):
    """
    Custom alerting function called when a child process is stale.
    FIXME: @dev may wish to implement SMS, email, sound, image or other custom alert

    Args:
    - process (str): The name of the process.
    - stale (int): The time elapsed since the process became stale.
    - data (dict): Timestamps data.

    Returns: None
    """
    print(
        it(
            "red",
            f"WARN: Watchdog detects Gateway {process} stale by {stale} seconds!",
        )
    )
    print(data)


def watchdog(process: str):
    """
    Utilize text pipe inter-process communication
    to ensure all multiprocessing processes are terminated by the main process.
    If any child becomes stale, an alert is triggered.
    Structure of timestamps: {"process": (last_update_time, time_died, is_alive)}

    Args:
    - process (str): The name of the process.

    Returns: None
    """
    now = int(time.time())
    timestamps = json_ipc("watchdog.txt")

    # This is the parent, check that child processes are not stale
    # If we send an alert update the timestamp so we don't send more constantly
    if process == "main":
        # Initialize new Gateway Session watchdog
        if not timestamps:
            print("intializing watchdog...")
            timestamps = {
                "main": [now, now, True],
                "deposits": [now, now, True],
                "withdrawals": [now, now, True],
                "ingots": [now, now, True],
                "parachains": [now, now, True],
            }
        # Look after child processes
        else:
            timestamps["main"] = [now, now, True]
            for child, last in timestamps.items():
                if child != "main" and processes().get(child, True):
                    stale = now - last[0]
                    died = last[1]
                    alive = last[2]
                    if stale > timing()["watchdog_stale"] and (
                        alive or stale > timing()["watchdog_repeat"]
                    ):
                        alert(child, now - died, timestamps)
                        timestamps[child] = [now, died, False]

    # This is a child, check if the main process has terminated, if so kill this child
    # otherwise update its timestamp
    else:
        stale = now - timestamps["main"][0]
        if stale > timing()["watchdog_stale"]:
            print(
                it(
                    "yellow",
                    f"ALERT: Watchdog is killing {process}"
                    + f"because Gateway Main stale by {stale} seconds!",
                )
            )
            sys.exit()
        else:
            timestamps[process] = [now, now, True]

    json_ipc("watchdog.txt", json.dumps(timestamps))


def watchdog_sleep(process: str, pause: int):
    """
    update timestamp IPC every ten seconds until pause elapses
    """
    while pause > 0:
        time.sleep(max(min(pause, 10), 0))
        watchdog(process)
        pause -= 10
