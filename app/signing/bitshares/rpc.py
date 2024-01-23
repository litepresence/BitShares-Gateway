r"""
rpc.py

  ____  _ _   ____  _                         
 | __ )(_) |_/ ___|| |__   __ _ _ __ ___  ___ 
 |  _ \| | __\___ \| '_ \ / _` | '__/ _ \/ __|
 | |_) | | |_ ___) | | | | (_| | | |  __/\__ \
 |____/|_|\__|____/|_| |_|\__,_|_|  \___||___/
       ____  _             _                  
      / ___|(_) __ _ _ __ (_)_ __   __ _      
      \___ \| |/ _` | '_ \| | '_ \ / _` |     
       ___) | | (_| | | | | | | | | (_| |     
      |____/|_|\__, |_| |_|_|_| |_|\__, |     
               |___/               |___/      


WTFPL litepresence.com Dec 2021 & squidKid-deluxe Jan 2024

Collection of functions that interact with BitShares nodes using a WebSocket connection.

"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except

# STANDARD PYTHON MODULES
import json
import time
from decimal import Decimal as decimal
from random import shuffle

# THIRD PARTY MODULES
from websocket import create_connection as wss  # handshake to node

# GRAPHENE SIGNING MODULES
from .config import HANDSHAKE_TIMEOUT, NODES
from .utilities import trace


def wss_handshake(rpc=None):
    """
    create a wss handshake in less than X seconds, else try again
    """
    shuffle(NODES)
    handshake = HANDSHAKE_TIMEOUT + 1
    while handshake > HANDSHAKE_TIMEOUT:
        try:
            try:
                if rpc is not None:
                    rpc.close()  # attempt to close open stale connection
            except Exception:
                pass
            start = time.time()
            NODES.append(NODES.pop(0))  # rotate list
            node = NODES[0]
            rpc = wss(node, timeout=HANDSHAKE_TIMEOUT)
            handshake = time.time() - start
        except Exception:
            continue
    return rpc


def wss_query(rpc, params, client_order_id=1):
    """
    this definition will place all remote procedure calls (RPC)
    """

    for _ in range(10):
        try:
            # print(it('purple','RPC ' + params[0])('cyan',params[1]))
            # this is the 4 part format of EVERY rpc request
            # params format is ["location", "object", []]
            query = json.dumps(
                {"method": "call", "params": params, "jsonrpc": "2.0", "id": client_order_id}
            )
            # print(query)
            # rpc is the rpc connection created by wss_handshake()
            # we will use this connection to send query and receive json
            rpc.send(query)
            ret = json.loads(rpc.recv())
            try:
                ret = ret["result"]  # if there is result key take it
            except Exception:
                pass
            # print(ret)
            # print('elapsed %.3f sec' % (time.time() - start))
            return ret
        except Exception as error:
            try:  # attempt to terminate the connection
                rpc.close()
            except Exception:
                pass
            trace(error)  # tell me what happened
            # switch NODES
            rpc = wss_handshake(rpc)
            continue


def rpc_block_number(rpc):
    """
    block number and block prefix
    """
    return wss_query(rpc, ["database", "get_dynamic_global_properties", []])


def rpc_account_id(rpc, account_name):
    """
    given an account name return an account id
    """
    ret = wss_query(rpc, ["database", "lookup_accounts", [account_name, 1]])
    return ret[0][1]


def rpc_get_account(rpc, account_name):
    """
    given an account name return an account id
    """
    ret = wss_query(rpc, ["database", "get_account_by_name", [account_name, 1]])
    return ret


def rpc_tx_fees(rpc, account_id):
    """
    returns fee for limit order create and cancel without 10^precision
    also call orders
    """
    query = [
        "database",
        "get_required_fees",
        [
            [
                ["0", {"from": str(account_id)}],
                ["1", {"from": str(account_id)}],
                ["2", {"from": str(account_id)}],
                ["3", {"from": str(account_id)}],
                ["14", {"from": str(account_id)}],
                ["15", {"from": str(account_id)}],
            ],
            "1.3.0",
        ],
    ]
    ret = wss_query(rpc, query)
    transfer = ret[0]["amount"]
    create = ret[1]["amount"]
    cancel = ret[2]["amount"]
    call = ret[3]["amount"]
    issue = ret[4]["amount"]
    reserve = ret[5]["amount"]

    return {
        "transfer": transfer,
        "create": create,
        "cancel": cancel,
        "call": call,
        "issue": issue,
        "reserve": reserve,
    }


def rpc_balances(rpc, account_name, pair):
    """
    account balances
    """
    balances = wss_query(rpc, 
        [
            "database",
            "get_named_account_balances",
            [account_name, [pair["currency_id"], pair["asset_id"], "1.3.0"]],
        ]
    )

    for balance in balances:
        if balance["asset_id"] == pair["currency_id"]:
            currency = decimal(balance["amount"]) / 10 ** pair["currency_precision"]
        if balance["asset_id"] == pair["asset_id"]:
            assets = decimal(balance["amount"]) / 10 ** pair["asset_precision"]
        if balance["asset_id"] == "1.3.0":
            bitshares = decimal(balance["amount"]) / 10**5

    # print(currency, assets, bitshares)
    return currency, assets, bitshares


def rpc_open_orders(rpc, account_name, pair):
    """
    return a list of open orders, for one account, in one market
    """
    ret = wss_query(rpc, ["database", "get_full_accounts", [[account_name], "false"]])
    try:
        limit_orders = ret[0][1]["limit_orders"]
    except Exception:
        limit_orders = []
    market = [pair["currency_id"], pair["asset_id"]]
    orders = []
    for order in limit_orders:
        base_id = order["sell_price"]["base"]["asset_id"]
        quote_id = order["sell_price"]["quote"]["asset_id"]
        if (base_id in market) and (quote_id in market):
            orders.append(order["id"])
    return orders


def rpc_key_reference(rpc, public_key):
    """
    given public key return account id
    """
    return wss_query(rpc, ["database", "get_key_references", [[public_key]]])


def rpc_get_transaction_hex_without_sig(rpc, trx):
    """
    use this to verify the manually serialized trx buffer
    """
    ret = wss_query(rpc, ["database", "get_transaction_hex_without_sig", [trx]])
    return bytes(ret, "utf-8")


def rpc_get_transaction_hex(rpc, trx):
    """
    use this to verify the manually serialized trx buffer
    """
    ret = wss_query(rpc, ["database", "get_transaction_hex", [trx]])
    return bytes(ret, "utf-8")


def rpc_broadcast_transaction(rpc, trx, client_order_id=1):
    """
    upload the signed transaction to the blockchain
    """
    ret = wss_query(rpc, ["network_broadcast", "broadcast_transaction", [trx]], client_order_id)

    print(json.dumps(ret, indent=4))

    return ret


def unit_test():
    """
    test functionality of select definitions
    """
    rpc = wss_handshake()
    rpc_get_account(rpc, "litepresence1")


if __name__ == "__main__":
    unit_test()
