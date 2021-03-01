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
# pylint: disable=broad-except, invalid-name, bad-continuation, too-many-statements

# STANDARD PYTHON MODULES
import os
import time
import traceback
from json import dumps as json_dumps
from json import loads as json_loads
from random import randint
from statistics import StatisticsError, mode
from threading import Thread
from multiprocessing import Process

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, gateway_assets, offerings
from decoder_ring import ovaltine
from listener_boilerplate import listener_boilerplate
from parachain_eosio import verify_eosio_account
from parachain_ltcbtc import verify_ltcbtc_account
from parachain_ripple import verify_ripple_account
from nodes import bitshares_nodes
from signing_eosio import eos_transfer
from signing_ltcbtc import ltcbtc_transfer
from signing_ripple import xrp_transfer
from utilities import (block_ops_logo, chronicle, from_iso_date, it, json_ipc,
                       line_number, milleseconds, raw_operations, timestamp,
                       wss_handshake, wss_query)

# CONSTANTS
BLOCK_MAVENS = min(7, len(bitshares_nodes()))


def create_database():
    """
    initialize an empty text pipe IPC json_ipc
    :return None:
    """
    path = str(os.path.dirname(os.path.abspath(__file__))) + "/"
    os.makedirs(path + "pipe", exist_ok=True)
    for maven_id in range(BLOCK_MAVENS):
        json_ipc(doc=f"block_num_maven_{maven_id}.txt", text=json_dumps([0,]))
    json_ipc(doc=f"block_number.txt", text=json_dumps([0,]))


def print_options(options):
    """
    Print a table of Operation ID options
    :param dict(options) static bitshares operation ids
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


def choice():
    """
    Welcome and user input for stand alone listener app
    :return int(selection): operation id type number
    """
    print("\033c")
    print(it("blue", block_ops_logo()))
    print(
        it(
            "green",
            """
    Enter an Operation ID to stream below
    you can also enter a comma seperated list of ID's
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
        # if the user entered an ID number
        selection = [int(user_select)]
    except Exception:
        pass
    try:
        if "," in user_select:
            # if the user enter a list of numbers, attempt json conversion
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


def spawn_block_num_processes():
    """
    Several threads will concurrently update an array
    with external calls for irreversible block number
    later the statistical mode of the array will be used
    :return None:
    """

    def num_processes():
        """
        spawn, then periodically terminate and respawn so each child lives 10 minutes
        """
        processes = {}
        for maven_id in range(BLOCK_MAVENS):
            processes[maven_id] = Process(target=block_num_maven, args=(maven_id,))
            processes[maven_id].start()
        while True:
            for maven_id in range(BLOCK_MAVENS):
                time.sleep(600 / BLOCK_MAVENS)
                processes[maven_id].terminate()
                processes[maven_id] = Process(target=block_num_maven, args=(maven_id,))
                processes[maven_id].start()

    process = Thread(target=num_processes)
    process.start()


def spawn_block_processes(new_blocks):
    """
    Launch several threads to gather block data
    :param int(start):
    :param int(stop):
    :return None:
    """
    processes = {}
    for maven_id in range(BLOCK_MAVENS):
        processes[maven_id] = Process(target=block_maven, args=(maven_id, new_blocks))
        processes[maven_id].start()
    for maven_id in range(BLOCK_MAVENS):
        processes[maven_id].join(6)
    for maven_id in range(BLOCK_MAVENS):
        processes[maven_id].terminate()


def block_num_maven(maven_id):
    """
    BTS public api maven opinion of last irreversible block number
    :param int(maven_id) used for inter process communication channel identification
    """
    rpc = wss_handshake("")
    while True:
        try:
            # after 100 uses switch nodes
            if not randint(0, 100):
                rpc = wss_handshake(rpc)
            # ensure correct blocktime
            ret = wss_query(rpc, ["database", "get_dynamic_global_properties", []])
            block_time = from_iso_date(ret["time"])
            if time.time() - block_time > 10:
                rpc = wss_handshake(rpc)
                continue
            # get block number
            block_num = int(ret["last_irreversible_block_num"])
            latest = json_ipc(doc="block_number.txt")[0]
            # ensure block number is not wildly out of range
            if latest > 0:
                # switch nodes if height is more than 1200 too high or 5 too low
                if latest + 1200 < block_num < latest - 5:
                    rpc = wss_handshake(rpc)
                    continue
            json_ipc(
                doc=f"block_num_maven_{maven_id}.txt", text=json_dumps([block_num,])
            )
            time.sleep(2)
        except Exception:
            rpc = wss_handshake(rpc)


def block_maven(maven_id, new_blocks):
    """
    BitShares public api consensus of get_block() returns all tx's on a given block
    :param int(maven_id): used for inter process communication channel identification
    :param int(start): beginning block number to get block transaction data
    :param int(stop): latest irreversible block number
    :return None: reports via text file inter process communication
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


def rpc_account_id(rpc, account_name):
    """
    given an account name return an account id
    :param rpc: a BitShares public api websocket instance
    :param str(account_name): BitShares account name to be looked up
    :return str(account_id): a.b.c format
    """
    ret = wss_query(rpc, ["database", "lookup_accounts", [account_name, 1]])
    account_id = ret[0][1]
    return account_id


def rpc_get_objects(rpc, object_id):
    """
    Return data about objects in 1.7.x, 2.4.x, 1.3.x, etc. format
    """
    ret = wss_query(rpc, ["database", "get_objects", [object_id,]])
    return ret


def rpc_balances(rpc, account_name, asset_id):
    """
    no frills bitshares account balance for one asset by ID for testing
    NOTE amounts returned are graphene integers lacking precision
    return int(graphene_amount)
    """
    balance = wss_query(
        rpc, ["database", "get_named_account_balances", [account_name, [asset_id]],]
    )[0]
    return balance


def print_op(comptroller):
    """
    At the end of the main while loop we'll perform some action on every operation
    as a sample, we'll just color some operations and print the op
    :param list(op): op[0] is transaction type number and op[1] is the transaction
    :return None:
    """
    op = comptroller["op"]
    msg = op[1]
    if op[0] == 0:  # transfer
        msg = it("purple", msg)
        print(msg, "\n")
    if op[0] == 1:  # limit order create
        msg = it("green", msg)
        print(msg, "\n")
    if op[0] == 2:  # limit order cancel
        msg = it("red", msg)
        print(msg, "\n")


def withdraw(comptroller):
    """
    in production print_op is replaced with withdraw

        The user has returned some UIA to the issuer!

    upon hearing an on chain UIA transfer to the gateway with memo
    from this definition we trigger a gateway withdrawal event
    release the user's foreign chain funds to the memo
    and burn the returned UIA upon irreversible receipt
    """
    # localize the operation
    op = comptroller["op"]
    # create a list of issuer ids in the current scope of the gateway
    issuer_ids = []
    for network in comptroller["offerings"]:
        issuer_ids.append(gateway_assets()[network]["issuer_id"])
    # if its a transfer to gateway with a memo (within the defined scope)
    tgm = False
    if op[0] == 0:  # transfer
        # extract the uia_id from the op
        uia_id = op[1]["amount"]["asset_id"]
        # assign a nonce and update the comptroller
        nonce = milleseconds()
        comptroller["nonce"] = nonce
        comptroller["uia_id"] = uia_id
        # check if this is a transfer to our issuer
        if op[1]["to"] in issuer_ids:
            print(it("yellow", "gate uia transfer"))
            if "memo" in op[1].keys():
                tgm = True
            else:
                msg = "WARN: transfer to gateway WITHOUT memo"
                chronicle(comptroller, msg)
                print(it("red", msg))
    if tgm:  # transfer to gateway with a memo
        msg = f"withdrawal request: transfer {uia_id} to gateway with memo"
        print(it("red", msg.upper() + "\n\n"), it("yellow", op), "\n")
        line_number()
        timestamp()

        # update the issuer action to reserve and log this event for audit
        comptroller["issuer_action"] = "reserve"
        chronicle(comptroller, msg)

        # EOS specific parameters
        if uia_id == gateway_assets()["eos"]["asset_id"]:
            network = "eos"
            verify = verify_eosio_account
            transfer = eos_transfer
        # XRP specific parameters
        elif uia_id == gateway_assets()["xrp"]["asset_id"]:
            network = "xrp"
            verify = verify_ripple_account
            transfer = xrp_transfer
        # BTC specific parameters
        elif uia_id == gateway_assets()["btc"]["asset_id"]:
            network = "btc"
            verify = verify_ltcbtc_account
            transfer = ltcbtc_transfer
        # LTC specific parameters
        elif uia_id == gateway_assets()["ltc"]["asset_id"]:
            network = "ltc"
            verify = verify_ltcbtc_account
            transfer = ltcbtc_transfer
        else:  # NOTE: unlikely since tgm=True
            msg = "invalid uia_id"
            chronicle(comptroller, msg)
            return

        # build an order dictionary with keys: [public, private, quantity, to]
        order = {}
        # add public and private keys
        order["private"] = foreign_accounts()[network][0]["private"]
        order["public"] = foreign_accounts()[network][0]["public"]
        # convert graphene operation amount to human readable
        asset_precision = gateway_assets()[network]["asset_precision"]
        order["quantity"] = op[1]["amount"]["amount"] / 10 ** asset_precision
        # decode the client's deposit address from  memo using the issuers private key
        memo = op[1]["memo"]  # dict with keys("from", "to", "nonce", "message")
        order["to"] = ovaltine(memo, gateway_assets()[network]["issuer_private"])

        # update the comptroller with audit data; exclude the private key
        comptroller["withdrawal_amount"] = order["quantity"]
        comptroller["gateway_address"] = order["public"]
        comptroller["client_address"] = order["to"]
        comptroller["client_id"] = op[1]["from"]
        comptroller["account_idx"] = 0
        comptroller["network"] = network
        comptroller["order"] = order
        comptroller["memo"] = memo

        print(f"decoded {network} client", order["to"], "\n")
        # confirm we're dealing with a legit client address
        if verify(order["to"]):
            # upon hearing real foreign chain transfer, reserve the uia equal
            listener = Thread(target=listener_boilerplate, args=(comptroller),)
            listener.start()
            msg = f"spawn {network} withdrawal listener to reserve {order['quantity']}"
            print(it("red", msg), "\n")
            chronicle(comptroller, msg)
            # wait for listener thread to initialize then transfer the order
            time.sleep(30)
            timestamp()
            line_number()
            print(transfer(order))
        else:
            msg = f"WARN: memo is NOT a valid {network} account name"
            chronicle(comptroller, msg)
            print(it("red", msg), "\n")


def withdrawal_listener(comptroller, selection=None):
    """
    primary listener event loop
    :param int(selection) or None: user choice for demonstration of listener
    :run forever:
    """
    # get node list from github repo for bitshares ui staging; write to file
    nodes = bitshares_nodes()
    options = raw_operations()
    json_ipc(doc="nodes.txt", text=json_dumps(nodes))
    # create a subfolder for the database; write to file
    create_database()
    # initialize block number
    last_block_num = curr_block_num = 0
    # bypass user input... gateway transfer ops
    act = print_op
    if selection is None:
        selection = 0
        act = withdraw
    # spawn subprocesses for gathering streaming consensus irreversible block number
    spawn_block_num_processes()
    # continually listen for last block["transaction"]["operations"]
    print(it("red", "\nINITIALIZING WITHDRAWAL LISTENER\n"))
    # print(comptroller["offerings"], "\n\n")
    while True:
        try:
            # get the irreversible block number reported by each maven thread
            block_numbers = []
            for maven_id in range(BLOCK_MAVENS):
                block_num = json_ipc(doc=f"block_num_maven_{maven_id}.txt")[0]
                block_numbers.append(block_num)
            # the current block number is the statistical mode of the mavens
            # NOTE: may throw StatisticsError when no mode
            curr_block_num = mode(block_numbers)
            json_ipc(doc=f"block_number.txt", text=json_dumps([curr_block_num,]))
            # if the irreverisble block number has advanced
            if curr_block_num > last_block_num:
                # not on first iter
                if last_block_num:
                    # spawn some new mavens to get prospective block data
                    start = last_block_num + 1
                    stop = curr_block_num + 1
                    new_blocks = [*range(start, stop)]
                    spawn_block_processes(new_blocks)
                    # inititialize blocks as a dict of empty transaction lists
                    blocks = {}
                    for block_num in new_blocks:
                        blocks[block_num] = []
                    # get block transactions from each maven thread
                    for maven_id in range(BLOCK_MAVENS):
                        maven_blocks = json_ipc(doc=f"block_maven_{maven_id}.txt")
                        # for each block that has past since last update
                        for block_num in new_blocks:
                            # get the maven's version of that block from the dictionary
                            # sometimes the maven will not have the block; KeyError
                            try:
                                maven_block = maven_blocks[str(block_num)]
                                # append that version to the list
                                # of maven opinions for that block number
                                blocks[block_num].append(json_dumps(maven_block))
                            except KeyError:
                                pass
                    for _, maven_list in blocks.items():
                        if len(maven_list) < BLOCK_MAVENS - 1:
                            raise ValueError("not enough responding mavens")
                    # get the mode of the mavens for each block in the blocks dict
                    # NOTE: may throw StatisticsError when no mode
                    # for example half the nodes are on the next block number
                    blocks = {k: json_loads(mode(v)) for k, v in blocks.items()}
                    # print the blocks we're checking
                    if len(new_blocks) > 1:
                        print(it(159, new_blocks[:-1]))
                    print(
                        it(45, "BitShares"),
                        it(81, "Irreversible Block"),
                        it("yellow", curr_block_num),
                        it(117, time.ctime()[11:19]),
                        it(159, int(time.time())),
                    )
                    # triple nested:
                    # for each operation, in each transaction, on each block
                    for block_num, transactions in blocks.items():
                        for item, trx in enumerate(transactions):
                            for op in trx["operations"]:
                                # FIXME: this if clause makes the listener only funciton
                                # with transfers; NOTE: dict(options) may periodically
                                # need updated if the clause is removed
                                if op[0] == 0:
                                    # add the block and transaction numbers to the op
                                    op[1]["block"] = block_num
                                    op[1]["trx"] = item + 1
                                    op[1]["operation"] = (op[0], options[op[0]])
                                    comptroller["op"] = op
                                    # spin off withdrawal act so listener can continue
                                    process = Thread(target=act, args=(comptroller,))
                                    process.start()
                last_block_num = curr_block_num
            time.sleep(6)

        # in the event of any errors continue from the top of the loop
        # ============================================================
        # not enough responding mavens
        except ValueError as error:
            print("bitshares listener", it("yellow", error))
            continue
        # equally split no statistical mode
        except StatisticsError as Error:
            print("bitshares listener", it("yellow", error))
            continue
        # in all other cases provide stack trace
        except Exception:
            print("bitshares listener", traceback.format_exc())
            continue


def unit_test():
    """
    perform a unit test of the withdrawal_listener

    use unit_test_client.py to interact with the listener
    """
    print("\033c")
    print(unit_test.__doc__, "\n")
    # initialize financial incident reporting for audits
    comptroller = {}
    comptroller["session_unix"] = int(time.time())
    comptroller["session_date"] = time.ctime()
    comptroller["offerings"] = offerings()
    msg = "initializing gateway main"
    for network in comptroller["offerings"]:
        comptroller["network"] = network
        chronicle(comptroller, msg)
    comptroller["network"] = ""
    print("\nofferings " + it(45, comptroller["offerings"]), "\n")
    withdrawal_listener(comptroller)


if __name__ == "__main__":

    unit_test()
