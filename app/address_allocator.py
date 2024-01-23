r"""
address_allocator.py
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
WTFPL litepresence.com Jan 2021

Gateway State IPC

binary interprocess communication for address in use
[1,1,1,1,1,1] means there are 6 gateway addresses available
[0,1,0,1,1,1] will mean addresses at index 0 and 2 are in use
allowing for concurrent on_get api server operations
on a finite number of accounts
"""

# STANDARD PYTHON MODULES
import time
from json import dumps as json_dumps
from multiprocessing import Process
from typing import Optional

# BITSHARES GATEWAY MODULES
from config import foreign_accounts
from ipc_utilities import json_ipc


def initialize_addresses(network: str) -> None:
    """
    Initialize the IPC file with a list of ones, i.e., [1, 1, 1,...].
    The addresses are "all available" on startup.

    :param network: Name of the network.

    :return: None
    """
    initial_state = []
    doc = f"{network}_gateway_state.txt"
    for _ in foreign_accounts()[network]:
        initial_state.append(1)
    json_ipc(doc=doc, text=json_dumps(initial_state))


def lock_address(network: str) -> Optional[int]:
    """
    Check the binary state of the gateway addresses.
    If an address is available, switch its state to zero and return its index.
    If no address is available, return None.

    :param network: Name of the network.

    :return: Index of the locked address or None if no address is available.
    """
    doc = f"{network}_gateway_state.txt"
    gateway_idx = None
    gateway_state = json_ipc(doc=doc)
    for idx, state in enumerate(gateway_state):
        if state:
            gateway_idx = idx
            gateway_state[idx] = 0
            break
    json_ipc(doc=doc, text=json_dumps(gateway_state))

    return gateway_idx


def unlock_address_process(network: str, idx: int, delay: float) -> None:
    """
    Check the binary state of the gateway addresses.
    Reset the freed address state to 1 after a delay.

    :param network: Name of the network.
    :param idx: Index of the address to unlock.
    :param delay: Time delay before unlocking.

    :return: None
    """
    time.sleep(delay)
    doc = f"{network}_gateway_state.txt"
    gateway_state = json_ipc(doc=doc)
    gateway_state[idx] = 1
    json_ipc(doc=doc, text=json_dumps(gateway_state))


def unlock_address(network: str, idx: int, delay: float) -> None:
    """
    A process wrapper to delay unlocking an address.

    :param network: Name of the network.
    :param idx: Index of the address to unlock.
    :param delay: Time delay before unlocking.

    :return: None
    """
    unlock = Process(
        target=unlock_address_process,
        args=(
            network,
            idx,
            delay,
        ),
    )
    unlock.daemon = True
    unlock.start()


def unit_test_gateway_state() -> None:
    """
    Initialize the state machine with a list of 1's.
    Claim two gateway addresses for deposit.
    Launch two subprocesses to release the deposit addresses,
    one immediately and another after a delay.
    Check the state, wait, and check the state again.

    :return: None
    """
    print("\033c")
    print("\n\nunit test gateway deposit address state machine\n\n")
    initialize_addresses("xrp")
    print(json_ipc("xrp_gateway_state.txt"))
    print("\n\nlocking an xrp address\n")
    address_idx = lock_address("xrp")
    print("address index", address_idx)
    print(json_ipc("xrp_gateway_state.txt"))
    print("\n\nlocking another xrp address\n")
    address_idx = lock_address("xrp")
    print("address index", address_idx)
    print(json_ipc("xrp_gateway_state.txt"))
    print("\n\nlaunching subprocess unlocking xrp address 0 immediately\n\nAND")
    print("\nlaunching second subprocess unlocking xrp address 1 after 10 seconds\n")
    time.sleep(0.1)
    unlock_address("xrp", 0, 0)
    time.sleep(0.1)
    unlock_address("xrp", 1, 10)
    print(json_ipc("xrp_gateway_state.txt"))
    print("\n\nprimary process waiting 10 seconds\n")
    time.sleep(11)
    print(json_ipc("xrp_gateway_state.txt"))


if __name__ == "__main__":
    unit_test_gateway_state()
