r"""
graphene_auth.py

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

BitShares ECDSA for Login, Buy, Sell, Cancel, Transfer, Issue, Reserve

"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=bad-continuation, broad-except, too-many-locals, too-many-statements
# pylint: disable=too-many-branches
#
# STANDARD PYTHON MODULES
import time  # hexidecimal to binary text
from decimal import Decimal as decimal
from multiprocessing import Process, Value  # convert back to PY variable


# GRAPHENE SIGNING MODULES
from .config import (
    ATTEMPTS,
    JOIN,
    PROCESS_TIMEOUT,
    NODES,
)
from .graphene_signing import (
    PrivateKey,
    serialize_transaction,
    sign_transaction,
    verify_transaction,
)
from .rpc import (
    rpc_broadcast_transaction,
    rpc_key_reference,
    wss_handshake,
)
from .utilities import it, trace
from .build_transaction import build_transaction

# ISO8601 timeformat; 'graphene time'
ISO8601 = "%Y-%m-%dT%H:%M:%S%Z"


# Order creation helpers


def prototype_order(info, nodes=None):
    """
    each order will require a cached nodes list
    and a cached header with account and asset metadata
    """
    if nodes is None:
        nodes = NODES
    header = {
        "asset_id": info["asset_id"],
        "asset_precision": info["asset_precision"],
        "currency_id": info.get("currency_id", 0),
        "currency_precision": info.get("currency_precision", 0),
        "account_id": info["issuer_id"],
        "account_name": info["issuer_public"],
        "wif": info["issuer_private"],
    }
    order = {
        "header": header,
        "nodes": nodes,
    }
    return order


def issue(info, amount, account_id):
    """
    Put UIA.XYZ in user's BitShares wallet.
    """
    order = prototype_order(info)
    order["edicts"] = [{"op": "issue", "amount": amount, "account_id": account_id}]
    print(order["header"]["account_name"], order["header"]["asset_id"], order["edicts"])
    broker(order)


def reserve(info, amount):
    """
    Put UIA.XYZ into the reserve pool.
    """
    order = prototype_order(info)
    order["edicts"] = [{"op": "reserve", "amount": amount}]
    print(order["header"]["account_name"], order["header"]["asset_id"], order["edicts"])
    broker(order)


# Main process
def broker(order):
    """
    "broker(order) --> execute(signal, order)"
    # insistent timed multiprocess wrapper for authorized ops
    # covers all incoming buy/sell/cancel authenticated requests
    # if command does not execute in time: terminate and respawn
    # serves to force disconnect websockets if hung
    "up to ATTEMPTS chances; each PROCESS_TIMEOUT long: else abort"
    # signal is switched to 0 after execution to end the process
    """
    signal = Value("i", 0)
    auth = Value("i", 0)
    iteration = 0
    while (iteration < ATTEMPTS) and not signal.value:
        iteration += 1
        print("\nmanualSIGNING authentication attempt:", iteration, time.ctime(), "\n")
        child = Process(target=execute, args=(signal, auth, order))
        child.daemon = False
        child.start()
        if JOIN:  # means main script will not continue till child done
            child.join(PROCESS_TIMEOUT)

    return bool(auth.value)


def execute(signal, auth, order):
    """
    #
    """

    def transact(rpc, order, auth):
        trx = build_transaction(rpc, order)
        # if there are any orders, perform ecdsa on serialized transaction
        if trx == -1:
            msg = it("red", "CURRENCY NOT PROVIDED")
        elif trx["operations"]:
            trx, message = serialize_transaction(rpc, trx)
            signed_tx = sign_transaction(trx, message, wif)
            if signed_tx is None:
                msg = it("red", "FAILED TO AUTHENTICATE ORDER")
                return msg
            signed_tx = verify_transaction(signed_tx, wif)
            # don't actaully broadcast login op, signing it is enough
            if order["edicts"][0]["op"] != "login":
                print(rpc_broadcast_transaction(rpc, signed_tx, order["header"]["client_order_id"]))
            auth.value = 1
            msg = it("green", "EXECUTED ORDER")
        else:
            msg = it("red", "REJECTED ORDER")
        return msg
    rpc = wss_handshake()

    wif = order["header"]["wif"]
    start = time.time()
    # if this is just an authentication test, then there is no serialization / signing
    # just check that the private key references to the account id in question
    if order["edicts"][0]["op"] == "login":
        msg = it("red", "LOGIN FAILED")
        try:
            # instantitate a PrivateKey object
            private_key = PrivateKey(wif)
            # which contains an Address object
            address = private_key.address
            # which contains str(PREFIX) and a Base58(pubkey)
            # from these two, build a human terms "public key"
            public_key = address.prefix + str(address.pubkey)
            # get a key reference from that public key to 1.2.x account id
            key_reference_id = rpc_key_reference(rpc, public_key)[0][0]
            # extract the account id in the metanode
            account_id = order["header"]["account_id"]
            print("wif account id", key_reference_id)
            print("order account id", account_id)
            # if they match we're authenticated
            if account_id == key_reference_id:
                auth.value = 1
                msg = it("green", "AUTHENTICATED")
        except Exception:
            pass
    else:
        try:
            if (  # cancel all
                order["edicts"][0]["op"] == "cancel" and "1.7.X" in order["edicts"][0]["ids"]
            ):
                msg = it("red", "NO OPEN ORDERS")
                open_orders = True
                while open_orders:
                    metanode = peerplays_trustless_client()
                    open_orders = metanode["orders"]
                    ids = order["edicts"][0]["ids"] = [
                        order["orderNumber"] for order in open_orders
                    ]
                    if ids:
                        msg = transact(rpc, order, auth)
                    time.sleep(5)
            elif (  # cancel some
                order["edicts"][0]["op"] == "cancel" and "1.7.X" not in order["edicts"][0]["ids"]
            ):
                msg = it("red", "NO OPEN ORDERS")
                open_orders = True
                while open_orders:
                    metanode = peerplays_trustless_client()
                    open_orders = metanode["orders"]
                    ids = order["edicts"][0]["ids"] = [
                        order["orderNumber"]
                        for order in open_orders
                        if order in order["edicts"][0]["ids"]
                    ]
                    if ids:
                        msg = transact(rpc, order, auth)
                    time.sleep(5)

            else:  # all other order types
                msg = transact(rpc, order, auth)

        except Exception as error:
            trace(error)
    stars = it("yellow", "*" * (len(msg) + 17))
    msg = "manualSIGNING " + msg
    print("\n")
    print(stars + "\n    " + msg + "\n" + stars)
    print("\n")
    print("process elapsed: %.3f sec" % (time.time() - start), "\n\n")
    signal.value = 1
