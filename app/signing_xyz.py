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

import json
# STANDARD PYTHON MODULES
import time

# BITSHARES GATEWAY MODULES
from ipc_utilities import chronicle, json_ipc
from utilities import it, line_number, timestamp


def xyz_balance(*_) -> float:
    """
    return hardcoded float balance
    """
    return 1000.0


def xyz_transfer(order, comptroller):
    """
    Paper transfer on the XYZ "blockchain"
    actually just prints the order and returns a unique transaction id
    """
    timestamp()
    line_number()
    print("\nORDER\n\n", {k: v for k, v in order.items() if k != "private"}, "\n")
    # unique incrementing transaction id
    event = json_ipc("xyz_trx_id.txt")
    if event is not None:
        event += 1
    else:
        event = 0
    json_ipc("xyz_trx_id.txt", event)

    comptroller["tx_id"] = event
    comptroller["order"] = order
    msg = it("red", "XYZ TRANSFERRED")
    chronicle(comptroller, msg)
    print(msg)
    order["quantity"] = order["quantity"] * 10**5
    json_ipc(
        "xyz_transactions.txt",
        json.dumps([{**order, "type": "transfer", "block_num": int(time.time() / 3) + 5}]),
    )
    return event
