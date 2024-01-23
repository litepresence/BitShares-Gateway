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
# STANDARD MODULES
from typing import Any, Dict, Optional

# BITSHARES GATEWAY MODULES
from config import gateway_assets, nil
from ipc_utilities import chronicle
from signing.bitshares.graphene_auth import issue, reserve
from utilities import it, roughly


def issue_or_reserve(comptroller: Dict[str, Any]) -> Dict[str, Any]:
    """
    Issue or reserve UIA upon hearing a transaction in the listener boilerplate.
    Unpacks a considerable number of kwargs from comptroller.

    :param comptroller: Audit dictionary.
    :return: Updated audit dictionary.
    """
    # Localize the comptroller keys
    uia: str = comptroller["uia"]
    nonce: int = comptroller["nonce"]
    uia_id: str = comptroller["uia_id"]
    trx_to: str = comptroller["trx_to"]
    network: str = comptroller["network"]
    trx_from: str = comptroller["trx_from"]
    direction: str = comptroller["direction"]
    client_id: str = comptroller["client_id"]
    trx_amount: float = comptroller["trx_amount"]
    str_amount: str = comptroller["str_amount"]
    memo_check: bool = comptroller["memo_check"]
    listening_to: str = comptroller["listening_to"]
    issuer_action: Optional[str] = comptroller["issuer_action"]
    withdrawal_amount: Optional[float] = comptroller["withdrawal_amount"]

    # If the transaction is to the address we're listening to
    if listening_to == trx_to:
        # If it's a gateway utilizing a single account and the memo is invalid
        if issuer_action == "issue" and not memo_check:
            msg: str = "Received transaction with invalid memo"
            chronicle(comptroller, msg)
            print(msg)

        # Chronicle nil deposits but do not issue or reserve
        if 0 < trx_amount <= nil()[network]:
            msg: str = "Received nil amount"
            chronicle(comptroller, msg)
            print(msg)
            if issuer_action is None:
                print(comptroller)

        # Process deposits greater than nil
        if trx_amount > nil()[network]:
            print(
                f"Nonce {nonce}",
                it("red", f"{direction} {network.upper()}"),
                it("red", "TRANSFER DETECTED\n"),
                f"Amount {trx_amount} {str_amount}\n From {trx_from}\n To {trx_to}\n",
            )

            # Client has deposited foreign tokens, issue an equal amount of UIA
            if issuer_action == "issue" and memo_check:
                msg: str = (
                    f'Nonce {nonce} {it("red", f"ISSUING {trx_amount}")} {client_id}, {uia},'
                    f" {uia_id}, {network}"
                )
                print(msg)
                issue(gateway_assets()[network], trx_amount, client_id)
                # Signal to break the while loop
                comptroller["complete"] = True
                chronicle(comptroller, str(msg))

            # Parent process is sending funds to the client,
            # reserve the UIA upon hearing proof of transfer
            elif issuer_action == "reserve" and roughly(trx_amount, withdrawal_amount):
                msg: str = (
                    f'Nonce {nonce} {it("red", f"RESERVING {trx_amount}")} {client_id}, {uia},'
                    f" {uia_id}, {network}"
                )
                print(msg)
                reserve(gateway_assets()[network], trx_amount)
                # Signal to break the while loop
                comptroller["complete"] = True
                chronicle(comptroller, str(msg))

            # When unit testing, print the comptroller
            elif issuer_action is None:
                msg: str = "Unit test transfer"
                chronicle(comptroller, msg)
                print(msg, "\n", comptroller)
        else:
            msg = "trx_amount less than nil"
            print(it("yellow", msg))
            chronicle(comptroller, msg)

    return comptroller
