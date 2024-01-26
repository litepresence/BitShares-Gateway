r"""
Gateway.py
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

Graphene Python Gateway

Built in collaboration with bitshares.org

This is the primary script to be launched by the gateway admin, in terminal:

    python3 Gateway.py

Launches several concurrent processes:

    1) WITHDRAW AND RESERVE PROCESS

    listen for incoming uia to gateway address via graphene listener
        confirm the transfer memo is a legit foreign chain address
            initiate withdrawal transfer of foreign chain tokens to client
            listen to foreign chain to confirm transfer
                reserve uia

    2) DEPOSIT AND ISSUE PROCESS

    provide web api for client to request gateway deposit address
        provide a unique address to deposit foreign tokens
            listen for incoming foreign tokens on parachains
                issue uia

    3) INGOT PROCESS

    periodically check foreign chain gateway wallets
        upon finding too many small dust amounts
            consolidate ingots

    4) PARACHAIN PROCESS

    writes apodized blocks of each blockchain in offerings to disk

    5) LOGO PROCESS

    animates the the startup logo allowing a delay for parachains to be built

"""
# STANDARD MODULES
import sys
import time
from multiprocessing import Process
from sys import version as python_version
from typing import Dict

sys.path.append("signing/eosio")
sys.path.append("signing/ripple")
sys.path.append("signing/bitcoin")
# isort: split

# BITSHARES GATEWAY MODULES
from address_allocator import initialize_addresses
from config import gateway_assets, offerings, processes
from ipc_utilities import chronicle, json_ipc
from logo_supreme import run as logo_supreme
from process_deposits import deposit_server
from process_ingots import ingot_casting
from process_parachains import spawn_parachains
from process_withdrawals import withdrawal_listener
from signing.bitshares.rpc import rpc_get_account, wss_handshake
from utilities import it, xterm
from watchdog import watchdog, watchdog_sleep


def withdrawal_process(comptroller: Dict[str, str]) -> None:
    """
    Launch a withdrawal listener subprocess to monitor
    BitShares chain 24/7 for incoming UIA transfers.
    Transfers containing a memo will signal respective foreign chain withdrawals.

    :param comptroller: A dictionary containing gateway session information.

    :returns: None

    psuedocode withdrawal flow

    listener_bitshares() # 24/7
      on_op()
        if transfer_to_me:
            if EOS:
                if verify_eosio_account(op_memo):
                    Process(foreign_chain_listener(amount))
                        on_receipt(op_amount)
                            broker({"op":"reserve", "amount": op_amount})
                    eos_transfer(op_amount)
            if XRP:
                ditto
            etc.
    """
    comptroller["process"] = "withdrawals"
    process = Process(target=withdrawal_listener, args=(comptroller,))
    process.daemon = False
    process.start()


def deposit_process(comptroller: Dict[str, str]) -> None:
    """
    Launch a Falcon API server subprocess.
    Users send a GET request with their BitShares account name and coin they want to deposit.
    The server responds with a foreign chain deposit address from a rotating list.
    The GET request launches a foreign chain listener,
    which transfers funds from a rotating gateway inbound address to outbound
    and issues the UIA to the client. Unused gateway requests timeout after a period.

    :param comptroller: A dictionary containing gateway session information.

    :returns: None

    psuedocode deposit flow upon get request

    address = lock_address()
    subProcess(foreign_chain_listener(address))
        if received:
            transfer_to_hot_wallet()
            broker("op":"issue")
        if received or timeout:
            unlock_address(address)
            break
    resp.body = ("address": address, "timeout": "30 MINUTES", "msg":"")
    """
    comptroller["process"] = "deposits"
    process = Process(target=deposit_server, args=(comptroller,))
    process.daemon = False
    process.start()


def ingot_process(comptroller: Dict[str, str]) -> None:
    """
    Each gateway has several receivable accounts in a list.
    The zero account is also the outbound account.
    Periodically shift all funds to the outbound account.

    :param comptroller: A dictionary containing gateway session information.

    :returns: None
    """
    comptroller["process"] = "ingots"
    process = Process(target=ingot_casting, args=(comptroller,))
    process.daemon = False
    process.start()


def logo_process() -> None:
    """
    Create a subprocess for the initialization logo.

    :returns: None
    """
    process = Process(target=logo_supreme)
    process.daemon = True
    process.start()
    process.join()
    process.terminate()


def parachain_process(comptroller: Dict[str, str]) -> None:
    """
    Launch a subprocess for gathering block data. The data is written to disk via json_ipc.
    Each listener event relies on parachain data instead of external calls.

    :param comptroller: A dictionary containing gateway session information.

    :returns: None
    """
    comptroller["process"] = "parachains"
    process = Process(target=spawn_parachains, args=(comptroller,))
    process.daemon = False
    process.start()


def main() -> None:
    """
    Setting the state of all inbound accounts to available.
    Subprocess automatically send all inbound funds to the outbound account.
    Subprocess deposit API server.
    subprocess BitShares withdrawal listener.

    :returns: None
    """
    json_ipc("watchdog.txt", r"{}")
    watchdog("main")
    print("\033c\n")
    print(it("yellow", "Checking BitShares account for authenticity..."))
    rpc = wss_handshake()
    for network, data in gateway_assets().items():
        if not rpc_get_account(rpc, data["issuer_public"]):
            raise ValueError(
                it(
                    "red",
                    f"Invalid BitShares account name '{data['issuer_public']}'"
                    f" in gateway_assets[{network}] in config.py",
                )
            )
    print("\033c\n")

    # initialize financial incident reporting for audits
    comptroller = {}
    comptroller["session_unix"] = int(time.time())
    comptroller["session_date"] = str(time.ctime())
    comptroller["offerings"] = offerings()
    msg = "initializing gateway main"
    for network in comptroller["offerings"]:
        comptroller["network"] = network
        chronicle(comptroller, msg)
    comptroller["network"] = ""
    parachain_process(comptroller)
    # give half second to ctrl+shift+\ to break program on startup for dev
    time.sleep(0.5)
    logo_process()
    # set state machine to "all incoming accounts available"
    for network in comptroller["offerings"]:
        initialize_addresses(network)
    # confirm parachains are running
    for network in offerings():
        try:
            parachain_cache = json_ipc(f"parachain_{network}.txt")
            # extract the block numbers in the cached parachain
            parachain_nums = sorted([str(i) for i in list(parachain_cache.keys())])
            # determine the maximum block number on record
            latest_block = max(parachain_nums)
            print(it(xterm(), f"{network.upper()} BLOCK {latest_block}"))
        except Exception as error:
            print(it("yellow", f"{network.upper()} PARACHAIN FAILED TO INITIALIZE"))
            raise ChildProcessError() from error
    print("")
    # spawn 3 concurrent gateway subprocesses; passing the comptroller
    if processes()["ingots"]:
        ingot_process(comptroller)
        time.sleep(0.2)
    if processes()["deposits"]:
        deposit_process(comptroller)
        time.sleep(0.2)
    if processes()["withdrawals"]:
        withdrawal_process(comptroller)
    # Alert if child processes become stale.
    while True:
        watchdog_sleep("main", 10)


if __name__ == "__main__":
    # ensure the correct python version
    if float(".".join(python_version.split(".")[:2])) < 3.8:
        raise AssertionError("GRAPHENE PYTHON GATEWAY Requires Python 3.8+")

    main()
