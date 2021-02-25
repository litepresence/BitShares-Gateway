r"""
utilities.py
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

issue or reserve called by the chain specific listeners
"""

# BITSHARES GATEWAY MODULES
from config import nil
from signing_bitshares import issue, reserve
from utilities import chronicle, it, roughly


def issue_or_reserve(comptroller):
    """
    issue or reserve uia upon hearing a transaction in the listener boilerplate
    unpacks a considerable number of kwargs from comptroller

    :param dict(comptroller) # audit dictionary
    :return dict(comtroller) # updated audit dictionary
    """
    # localize the comptroller keys
    uia = comptroller["uia"]
    nonce = comptroller["nonce"]
    uia_id = comptroller["uia_id"]
    trx_to = comptroller["trx_to"]
    network = comptroller["network"]
    trx_from = comptroller["trx_from"]
    direction = comptroller["direction"]
    client_id = comptroller["client_id"]
    trx_amount = comptroller["trx_amount"]
    str_amount = comptroller["str_amount"]
    memo_check = comptroller["memo_check"]
    listening_to = comptroller["listening_to"]
    issuer_action = comptroller["issuer_action"]
    withdrawal_amount = comptroller["withdrawal_amount"]

    # print(listening_to, trx_to)
    # if the transaction is to the address we're listening to
    if listening_to == trx_to:
        # if its a gateway usilizing a single account and the memo is invalid
        if issuer_action == "issue" and not memo_check:
            msg = "received tx with invalid memo"
            chronicle(comptroller, msg)
            print(msg)
        # chronicle nil deposits, but do not issue or reserve
        if 0 < trx_amount <= nil()[network]:
            msg = "received nil amount"
            chronicle(comptroller, msg)
            print(msg)
            if issuer_action is None:
                print(comptroller)
        # process deposits greater than nil
        if trx_amount > nil()[network]:
            print(
                f"nonce {nonce}",
                it("red", f"{direction} {network}"),
                it("red", "TRANSFER DETECTED\n"),
                f"amount {trx_amount} {str_amount} \n",
                f"from {trx_from}\n",
                f"to {trx_to}\n",
            )
            # client has deposited foreign tokens, issue an equal amount of UIA
            if issuer_action == "issue" and memo_check:
                msg = (
                    f"nonce {nonce}",
                    it("red", f"ISSUING {trx_amount}"),
                    (client_id, uia, uia_id, network),
                )
                issue(network, trx_amount, client_id)
                # signal to break the while loop
                comptroller["complete"] = True
                chronicle(comptroller, msg)
                print(msg)
            # parent process is sending funds to client
            # reserve the UIA upon hearing proof of transfer
            elif issuer_action == "reserve" and roughly(trx_amount, withdrawal_amount):
                msg = (
                    f"nonce {nonce}",
                    it("red", f"RESERVING {trx_amount}"),
                    (client_id, uia, uia_id, network),
                )
                reserve(network, trx_amount)
                # signal to break the while loop
                comptroller["complete"] = True
                chronicle(comptroller, msg)
                print(msg)
            # when unit testing print the comptroller
            elif issuer_action is None:
                msg = "unit test transfer"
                chronicle(comptroller, msg)
                print(msg, "\n", comptroller)
    return comptroller
