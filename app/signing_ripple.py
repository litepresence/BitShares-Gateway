r"""
signing_ripple.py
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

Ripple Transfer Operations and Account Balances
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except

# STANDARD PYTHON MODULES
import asyncio
import time
from json import dumps as json_dumps

from requests import get

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, test_accounts
from ipc_utilities import chronicle
from nodes import ripple_node
# THIRD PARTY MODULES
from signing.ripple.aioxrpy.definitions import (RippleTransactionFlags,
                                                RippleTransactionType)
from signing.ripple.aioxrpy.keys import RippleKey
from signing.ripple.aioxrpy.rpc import RippleJsonRpc
from utilities import it, line_number, timestamp


def xrp_balance(account, comptroller):
    """
    given a ripple public key return the xrp balance via request to public api
    """
    data = json_dumps(
        {
            "method": "account_info",
            "params": [
                {
                    "account": account,
                    "strict": True,
                    "ledger_index": "current",
                    "queue": True,
                }
            ],
        }
    )
    ret = get(ripple_node(), data=data).json()
    # print("\n\nreturned data:    ", ret)
    balance = 0
    try:
        # the response is in "ripple drops" we need to convert to xrp
        balance = float(ret["result"]["account_data"]["Balance"]) / 10**6
        # print("\n\nBalance:    ", balance)
    except Exception as error:
        print("\n\nError:   ", error, "\n")
        msg = "failed to fetch balance"
        chronicle(comptroller, msg)
    return balance


async def xrp_transfer_execute(order):
    """
    using ulamlabs/aioxrpy
    given a simplified order dict with keys: [from, to, quantity]
    serialize and sign client side locally
    broadcast the xrp transfer to the ripple public api server
    """
    master = RippleKey(private_key=order["private"])
    rpc = RippleJsonRpc(ripple_node())
    # reserve = await rpc.get_reserve()
    fee = await rpc.fee()

    trx = {
        "Account": master.to_account(),
        "Flags": RippleTransactionFlags.FullyCanonicalSig,
        "TransactionType": RippleTransactionType.Payment,
        "Amount": int(order["quantity"] * 10**6),  # conversion to ripple "drops"
        "Destination": order["to"],
        "Fee": fee.minimum,
    }
    return await rpc.sign_and_submit(trx, master)


def xrp_transfer(order, comptroller):
    """
    pretty wrap the asyncio xrp transfer
    """
    # FIXME carefully consider the SECURITY of this event!
    timestamp()
    line_number()
    print("\nORDER\n\n", {k: v for k, v in order.items() if k != "private"}, "\n")
    event = asyncio.get_event_loop().run_until_complete(xrp_transfer_execute(order))
    comptroller["tx_id"] = event
    comptroller["order"] = order
    msg = it("red", "XRP TRANSFERRED")
    chronicle(comptroller, msg)
    print(msg)
    return event


def unit_test_xrp_transfer():
    """
    UNIT TEST

    given the first two accounts in the configuration file
    send 1 xrp 3 times from first ripple account to second ripple account
    """
    comptroller = {"test": "test"}
    # print the start balances
    print("\033c")
    print(xrp_balance(test_accounts()["xrp"]["public"], comptroller))
    print(xrp_balance(foreign_accounts()["xrp"][1]["public"], comptroller))
    # process an order
    order = {}
    order["public"] = test_accounts()["xrp"]["public"]
    order["private"] = test_accounts()["xrp"]["private"]
    order["to"] = foreign_accounts()["xrp"][1]["public"]
    order["quantity"] = 10
    print(xrp_transfer(order, comptroller), "\n")
    time.sleep(5)
    # print the final balances
    print(xrp_balance(test_accounts()["xrp"]["public"], comptroller))
    print(xrp_balance(foreign_accounts()["xrp"][1]["public"], comptroller))


if __name__ == "__main__":
    unit_test_xrp_transfer()
