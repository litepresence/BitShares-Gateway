r"""
process_withdrawals.py
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

BitShares Block Operations Listener for Gateway Withdrawals

streaming statistical mode of websocket public api data
prints every operation in every transaction on every block
filtered by user selected operation id numbers

includes on_op definition for gateway withdrawal use upon issuer receipt of uia
may also run independently as a block ops listener for any Operation ID
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-branches, too-many-nested-blocks, too-many-locals
# pylint: disable=broad-except, invalid-name, too-many-statements

# STANDARD PYTHON MODULES
import os
import time
import traceback
from copy import deepcopy
from json import dumps as json_dumps
from json import loads as json_loads
from multiprocessing import Process
from random import randint
from statistics import StatisticsError, mode
from threading import Thread
from typing import List

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, gateway_assets, offerings
from decoder_ring import ovaltine
from ipc_utilities import chronicle, json_ipc
from listener_boilerplate import listener_boilerplate
from nodes import bitshares_nodes
from parachain_eosio import verify_eosio_account
from parachain_ltcbtc import verify_ltcbtc_account
from parachain_ripple import verify_ripple_account
from parachain_xyz import verify_xyz_account
from signing_eosio import eos_transfer
from signing_ltcbtc import ltcbtc_transfer
from signing_ripple import xrp_transfer
from signing_xyz import xyz_transfer
from utilities import (
    block_ops_logo,
    event_id,
    from_iso_date,
    it,
    line_number,
    microseconds,
    raw_operations,
    timestamp,
    wss_handshake,
    wss_query,
)
from watchdog import watchdog_sleep

# CONSTANTS
BLOCK_MAVENS = min(7, len(bitshares_nodes()))


def create_database() -> None:
    """
    Initialize an empty text pipe IPC json_ipc.
    """
    path = str(os.path.dirname(os.path.abspath(__file__))) + "/"
    os.makedirs(path + "pipe", exist_ok=True)
    for maven_id in range(BLOCK_MAVENS):
        json_ipc(
            doc=f"block_num_maven_{maven_id}.txt",
            text=json_dumps(
                [
                    0,
                ]
            ),
        )
    json_ipc(
        doc="block_number.txt",
        text=json_dumps(
            [
                0,
            ]
        ),
    )


def print_options(options: dict) -> None:
    """
    Print a table of Operation ID options.

    :param options: Static BitShares operation IDs.
    """
    print(it("yellow", "\n\n                         Operation ID Numbers\n"))
    msg = ""
    for idx in range(30):
        msg += "    " + str(idx).ljust(4) + str(options[idx]).ljust(30)
        try:
            msg += str(idx + 30).ljust(4) + str(options[idx + 30])
        except Exception:
            pass
        msg += "\n"
    print(it("yellow", msg))
    print(it("green", "\n\n    Enter ID number(s)"))


def choice() -> List[int]:
    """
    Welcome and user input for stand-alone listener app.

    :return: Operation ID type number.
    """
    print("\033c")
    print(it("blue", block_ops_logo()))
    print(
        it(
            "green",
            """
    Enter an Operation ID to stream below
    you can also enter a comma separated list of ID's
    or Enter the letter "A" for All
    or press Enter for demo of Operations 0, 1, and 2
        """,
        )
    )

    operations = raw_operations()
    print_options(operations)
    selection = [0, 1, 2]
    user_select = input("\n\n")
    try:
        # If the user entered an ID number
        selection = [int(user_select)]
    except Exception:
        pass
    try:
        if "," in user_select:
            # If the user enters a list of numbers, attempt json conversion
            selection = json_loads(
                '["' + user_select.replace(",", '","').replace(" ", "") + '"]'
            )
            selection = [int(k) for k in selection]
    except Exception:
        pass
    if user_select.lower() == "a":
        selection = list(operations.keys())

    print("\033c")
    print(it("blue", block_ops_logo()))
    print(
        it(
            "green",
            "\n        BitShares Block Operations Listener\n"
            + "\n        operation(s) selected:    \n",
        )
    )
    print(it("blue", "        " + str(selection) + "\n"))
    for k in selection:
        print("       ", (operations[k]))
    print(it("green", "\n\n        fetching latest irreversible block number...\n"))
    return selection


def spawn_block_num_processes() -> None:
    """
    Several threads will concurrently update an array
    with external calls for irreversible block number
    later the statistical mode of the array will be used.
    """

    def num_processes() -> None:
        """
        Spawn, then periodically terminate and respawn so each child lives 10 minutes.
        """
        processes = {}
        for maven_id in range(BLOCK_MAVENS):
            processes[maven_id] = Process(
                target=block_num_maven, args=(maven_id,), daemon=True
            )
            processes[maven_id].start()
        while True:
            for maven_id in range(BLOCK_MAVENS):
                time.sleep(600 / BLOCK_MAVENS)
                processes[maven_id].terminate()
                processes[maven_id] = Process(
                    target=block_num_maven, args=(maven_id,), daemon=True
                )
                processes[maven_id].start()

    process = Thread(target=num_processes)
    process.start()


def spawn_block_processes(new_blocks: List[int]) -> None:
    """
    Launch several threads to gather block data.

    :param new_blocks: List of new block numbers.
    """
    processes = {}
    for maven_id in range(BLOCK_MAVENS):
        processes[maven_id] = Process(
            target=block_maven, args=(maven_id, new_blocks), daemon=True
        )
        processes[maven_id].start()
    for maven_id in range(BLOCK_MAVENS):
        processes[maven_id].join(6)
    for maven_id in range(BLOCK_MAVENS):
        processes[maven_id].terminate()


def block_num_maven(maven_id: int) -> None:
    """
    BTS public api maven opinion of last irreversible block number.

    :param maven_id: Used for inter-process communication channel identification.
    """
    rpc = wss_handshake("")
    while True:
        try:
            # After 100 uses switch nodes
            if not randint(0, 100):
                rpc = wss_handshake(rpc)
            # Ensure correct blocktime
            ret = wss_query(rpc, ["database", "get_dynamic_global_properties", []])
            block_time = from_iso_date(ret["time"])
            if time.time() - block_time > 10:
                rpc = wss_handshake(rpc)
                continue
            # Get block number
            block_num = int(ret["last_irreversible_block_num"])
            latest = json_ipc(doc="block_number.txt")[0]
            # Ensure block number is not wildly out of range
            if latest > 0:
                # Switch nodes if height is more than 1200 too high or 5 too low
                if latest + 1200 < block_num < latest - 5:
                    rpc = wss_handshake(rpc)
                    continue
            json_ipc(
                doc=f"block_num_maven_{maven_id}.txt",
                text=json_dumps(
                    [
                        block_num,
                    ]
                ),
            )
            time.sleep(2)
        except Exception:
            rpc = wss_handshake(rpc)


def block_maven(maven_id: int, new_blocks: List[int]) -> None:
    """
    BitShares public api consensus of get_block() returns all tx's on a given block.

    :param maven_id: Used for inter-process communication channel identification.
    :param new_blocks: List of block numbers to get block transaction data.
    :return: None, reports via text file inter-process communication.
    """
    blocks = {}
    rpc = wss_handshake("")
    doc = f"block_maven_{maven_id}.txt"
    while True:
        try:
            for block_num in new_blocks:
                query = ["database", "get_block", [block_num]]
                ret = wss_query(rpc, query)["transactions"]
                assert isinstance(ret, list)
                blocks[block_num] = ret
            json_ipc(doc=doc, text=json_dumps(blocks))
            break
        except Exception:
            rpc = wss_handshake(rpc)
    # print(maven_id, new_blocks)


def rpc_account_id(rpc: str, account_name: str) -> str:
    """
    Given an account name, return an account id.

    :param rpc: A BitShares public api websocket instance.
    :param account_name: BitShares account name to be looked up.
    :return: Account ID in a.b.c format.
    """
    ret = wss_query(rpc, ["database", "lookup_accounts", [account_name, 1]])
    account_id = ret[0][1]
    return account_id


def rpc_get_objects(rpc: str, object_id: str) -> dict:
    """
    Return data about objects in 1.7.x, 2.4.x, 1.3.x, etc. format.

    :param rpc: A BitShares public api websocket instance.
    :param object_id: Object ID to query.
    :return: Object data.
    """
    ret = wss_query(rpc, ["database", "get_objects", [object_id]])
    return ret


def rpc_balances(rpc: str, account_name: str, asset_id: str) -> int:
    """
    No-frills BitShares account balance for one asset by ID for testing.
    Note: Amounts returned are graphene integers lacking precision.

    :param rpc: A BitShares public api websocket instance.
    :param account_name: BitShares account name.
    :param asset_id: Asset ID.
    :return: Balance amount.
    """
    balance = wss_query(
        rpc,
        [
            "database",
            "get_named_account_balances",
            [account_name, [asset_id]],
        ],
    )[0]
    return balance


def print_op(_, comptroller: dict) -> None:
    """
    At the end of the main while loop, perform some action on every operation.
    As a sample, color some operations and print the op.

    :param op: Op[0] is the transaction type number and Op[1] is the transaction.
    :param comptroller: Dictionary containing operation details.
    :return: None.
    """
    op = comptroller["op"]
    msg = op[1]
    if op[0] == 0:  # Transfer
        msg = it("purple", msg)
        print(msg, "\n")
    if op[0] == 1:  # Limit order create
        msg = it("green", msg)
        print(msg, "\n")
    if op[0] == 2:  # Limit order cancel
        msg = it("red", msg)
        print(msg, "\n")


def withdraw(withdrawal_id: int, comptroller: dict) -> None:
    """
    In production, print_op is replaced with withdraw.

    The user has returned some UIA to the issuer!

    Upon hearing an on-chain UIA transfer to the gateway with memo
    from this definition, we trigger a gateway withdrawal event,
    release the user's foreign chain funds to the memo,
    and burn the returned UIA upon irreversible receipt.

    :param withdrawal_id: Identifier for the withdrawal.
    :param comptroller: Dictionary containing operation details.
    :return: None.
    """
    # Localize the operation
    op = comptroller["op"]

    # Create a list of issuer ids in the current scope of the gateway
    issuer_ids = [
        gateway_assets()[network]["issuer_id"] for network in comptroller["offerings"]
    ]

    # If it's a transfer to gateway with a memo (within the defined scope)
    tgm = False
    if op[0] == 0:  # Transfer
        # Extract the UIA_id from the op
        uia_id = op[1]["amount"]["asset_id"]

        # Assign a nonce and update the comptroller
        nonce = microseconds()
        comptroller["nonce"] = nonce
        comptroller["uia_id"] = uia_id

        # Check if this is a transfer to our issuer
        if op[1]["to"] in issuer_ids:
            print(it("yellow", "Gate UIA transfer"))
            if "memo" in op[1].keys():
                tgm = True
            else:
                msg = "WARN: Transfer to gateway WITHOUT memo"
                chronicle(comptroller, msg)
                print(it("red", msg))

    if tgm:  # Transfer to gateway with a memo
        # Increment the event id
        # NOTE withdrawal_id inherits from withdrawal_listener() local space
        withdrawal_id += 1
        comptroller["event_id"] = event_id("W", withdrawal_id)

        msg = f"Withdrawal request: Transfer {uia_id} to gateway with memo"
        print(it("red", msg.upper() + "\n\n"), it("yellow", op), "\n")
        line_number()
        timestamp()

        # Update the issuer action to reserve and log this event for audit
        comptroller["issuer_action"] = "reserve"
        chronicle(comptroller, msg)

        # Define dictionary to map uia_id to network, verify function, and transfer function
        network_dict = {
            gateway_assets()["eos"]["asset_id"]: (
                "eos",
                verify_eosio_account,
                eos_transfer,
            ),
            gateway_assets()["xyz"]["asset_id"]: (
                "xyz",
                verify_xyz_account,
                xyz_transfer,
            ),
            gateway_assets()["xrp"]["asset_id"]: (
                "xrp",
                verify_ripple_account,
                xrp_transfer,
            ),
            gateway_assets()["btc"]["asset_id"]: (
                "btc",
                verify_ltcbtc_account,
                ltcbtc_transfer,
            ),
            gateway_assets()["ltc"]["asset_id"]: (
                "ltc",
                verify_ltcbtc_account,
                ltcbtc_transfer,
            ),
        }

        if uia_id in network_dict:
            network, verify, transfer = network_dict[uia_id]
        else:  # NOTE: Unlikely since tgm=True
            msg = "Invalid UIA_id"
            chronicle(comptroller, msg)
            return

        # Build an order dictionary with keys: [public, private, quantity, to]
        order = {
            "private": foreign_accounts()[network][0]["private"],
            "public": foreign_accounts()[network][0]["public"],
            "quantity": (
                op[1]["amount"]["amount"]
                / 10 ** gateway_assets()[network]["asset_precision"]
            ),
            "to": (
                ovaltine(op[1]["memo"], gateway_assets()[network]["issuer_private"])
                if network != "xyz"
                else op[1]["memo"]
            ),
        }
        if network == "xyz":
            print("bypassing ovaltine for unit test memo")

        # Update the comptroller with audit data; exclude the private key
        comptroller.update(
            {
                "withdrawal_amount": order["quantity"],
                "gateway_address": order["public"],
                "client_address": order["to"],
                "client_id": op[1]["from"],
                "account_idx": 0,
                "network": network,
                "order": order,
                "memo": op[1]["memo"],
            }
        )

        print(f"Decoded {network} client", order["to"], "\n")

        # Confirm we're dealing with a legit client address
        if verify(order["to"], comptroller):
            # Upon hearing real foreign chain transfer, reserve the UIA equal
            # FIXME: Do we need to deep copy here? Perhaps not... for good measure:
            listener = Thread(
                target=listener_boilerplate, args=(deepcopy(comptroller),)
            )
            listener.start()
            msg = f"Spawn {network} withdrawal listener to reserve {order['quantity']}"
            print(it("red", msg), "\n")
            chronicle(comptroller, msg)

            # Wait for the listener thread to initialize then transfer the order
            time.sleep(30)
            timestamp()
            line_number()
            print(transfer(order, comptroller))
        else:
            msg = f"WARN: Memo is NOT a valid {network} account name"
            chronicle(comptroller, msg)
            print(it("red", msg), "\n")


def withdrawal_listener(comptroller: dict, selection: int = None) -> None:
    """
    Primary listener event loop.

    :param comptroller: Dictionary containing operation details.
    :param selection: User choice for demonstration of the listener.
    :run forever:
    """
    # Get node list from GitHub repo for BitShares UI staging; write to file
    nodes = bitshares_nodes()
    options = raw_operations()
    json_ipc(doc="nodes.txt", text=json_dumps(nodes))

    # Create a subfolder for the database; write to file
    create_database()

    # Initialize last block number, current block number, and withdrawal id
    last_block_num = 0
    curr_block_num = 0
    withdrawal_id = 0

    # Bypass user input... gateway transfer ops
    act = print_op
    if selection is None:
        selection = 0
        act = withdraw
    json_ipc("withdrawal_id.txt", json_dumps(1))

    # Spawn subprocesses for gathering streaming consensus irreversible block number
    spawn_block_num_processes()

    # Continually listen for last block["transaction"]["operations"]
    print(it("red", "\nINITIALIZING WITHDRAWAL LISTENER\n"))

    while True:
        try:
            # Get the irreversible block number reported by each maven thread
            block_numbers = [
                json_ipc(doc=f"block_num_maven_{maven_id}.txt")[0]
                for maven_id in range(BLOCK_MAVENS)
            ]

            # The current block number is the statistical mode of the mavens
            # NOTE: May throw StatisticsError when no mode
            curr_block_num = mode(block_numbers)
            json_ipc(
                doc="block_number.txt",
                text=json_dumps(
                    [
                        curr_block_num,
                    ]
                ),
            )
            # if the irreverisble block number has advanced
            if curr_block_num > last_block_num:
                # Not on the first iteration
                if last_block_num:
                    # Spawn some new mavens to get prospective block data
                    start = last_block_num + 1
                    stop = curr_block_num + 1
                    new_blocks = [*range(start, stop)]
                    spawn_block_processes(new_blocks)

                    # Initialize blocks as a dict of empty transaction lists
                    blocks = {block_num: [] for block_num in new_blocks}

                    # Get block transactions from each maven thread
                    for maven_id in range(BLOCK_MAVENS):
                        maven_blocks = json_ipc(doc=f"block_maven_{maven_id}.txt")

                        # For each block that has passed since the last update
                        for block_num in new_blocks:
                            # Get the maven's version of that block from the dictionary
                            # Sometimes the maven will not have the block; KeyError
                            try:
                                maven_block = maven_blocks[str(block_num)]
                                # Append that version to the list
                                # of maven opinions for that block number
                                blocks[block_num].append(json_dumps(maven_block))
                            except KeyError:
                                pass

                    for _, maven_list in blocks.items():
                        if len(maven_list) < BLOCK_MAVENS - 1:
                            raise ValueError("Not enough responding mavens")

                    # Get the mode of the mavens for each block in the blocks dict
                    # NOTE: May throw StatisticsError when no mode
                    # For example, half the nodes are on the next block number
                    blocks = {k: json_loads(mode(v)) for k, v in blocks.items()}

                    # Print the blocks we're checking
                    str_also = ""
                    if len(new_blocks) > 1:
                        min_new = str(min(new_blocks[:-1]))
                        max_new = str(max(new_blocks[:-1]))
                        str_also = "[" + min_new + " ... " + max_new + "]"

                    print(
                        it(45, "BitShares"),
                        it(81, "Irreversible Block"),
                        it("yellow", curr_block_num),
                        it(117, time.ctime()[11:19]),
                        it(159, int(time.time())),
                        it(45, str_also),
                    )

                    # Triple nested:
                    # For each operation, in each transaction, on each block
                    for block_num, transactions in blocks.items():
                        for item, trx in enumerate(transactions):
                            for op in trx["operations"]:
                                if op[0] == 0:
                                    # Add the block and transaction numbers to the op
                                    op[1]["block"] = block_num
                                    op[1]["trx"] = item + 1
                                    op[1]["operation"] = (op[0], options[op[0]])
                                    comptroller["op"] = op
                                    # spin off withdrawal act so listener can continue
                                    process = Thread(
                                        target=act,
                                        args=(withdrawal_id, deepcopy(comptroller)),
                                    )
                                    process.start()
                    # unit testing trigger
                    if unit_test_op := json_ipc("unit_test_withdrawal.txt"):
                        # Add the block and transaction numbers to the op
                        unit_test_op[1]["block"] = curr_block_num
                        unit_test_op[1]["trx"] = -1
                        unit_test_op[1]["operation"] = (0, "transfer")
                        comptroller["op"] = unit_test_op
                        # spin off withdrawal act so listener can continue
                        process = Thread(
                            target=act,
                            args=(withdrawal_id, deepcopy(comptroller)),
                        )
                        process.start()
                        json_ipc("unit_test_withdrawal.txt", "[]")

                last_block_num = curr_block_num
            watchdog_sleep("withdrawals", 6)  # 2 blocks = 6 seconds

        # In the event of any errors, continue from the top of the loop
        # ============================================================
        # Not enough responding mavens
        except (StatisticsError, ValueError) as error:
            print("BitShares listener", it("yellow", error))
            continue
        # In all other cases, provide a stack trace
        except Exception:
            print("BitShares listener", traceback.format_exc())
            continue


def unit_test() -> None:
    """
    Perform a unit test of the withdrawal_listener.

    Use unit_test_client.py to interact with the listener.
    """
    print("\033c")
    print(unit_test.__doc__, "\n")

    # Initialize financial incident reporting for audits
    comptroller = {
        "session_unix": int(time.time()),
        "session_date": time.ctime(),
        "offerings": offerings(),
    }

    msg = "Initializing gateway main"

    for network in comptroller["offerings"]:
        comptroller["network"] = network
        chronicle(comptroller, msg)

    comptroller["network"] = ""
    print("\nOfferings " + it(45, comptroller["offerings"]), "\n")

    withdrawal_listener(comptroller)


if __name__ == "__main__":
    unit_test()
