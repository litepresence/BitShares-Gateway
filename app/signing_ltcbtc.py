r"""
signing_ltcbtc.py
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

Litecoin and Bitcoin Transfer Operations and Account Balances
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except

# STANDARD PYTHON MODULES
import time

# BITSHARES GATEWAY MODULES
from ipc_utilities import chronicle
from utilities import create_access, it, line_number, precisely, timestamp


def ltcbtc_balance(_, comptroller):
    """
    wallet balance operation for litecoin and bitcoin
    NOTE: the account arg will not be used
    """
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration**2)
        try:
            access = create_access(network)
            return float(access.getbalance())
        except Exception as error:
            print(f"ltcbtc_balance {network} access failed {error.args}")
        iteration += 1


def ltcbtc_balances(_, comptroller):
    """
    wallet balances operation for each litecoin or bitcoin address
    NOTE: the account arg will not be used
    """
    # FIXME this RPC might require an empty list as arg (only used in unit testing)
    # review documentation!
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration**2)
        try:
            access = create_access(comptroller["network"])
            return access.listunspent()
        except Exception as error:
            print(f"ltcbtc_balances {network} access failed {error.args}")
        iteration += 1


def ltcbtc_transfer(order, comptroller, pay_fee=True):
    """
    authenticated transfer operation for litecoin and bitcoin
    """
    # FIXME carefully consider the SECURITY of this event!
    timestamp()
    line_number()
    network = comptroller["network"]
    print(
        network,
        "\nORDER\n\n",
        {k: v for k, v in order.items() if k != "private"},
        "\n",
    )
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration**2)
        try:
            access = create_access(comptroller["network"])
            # access.sendtoaddress(address, amount)
            tx_id = access.sendtoaddress(
                order["to"],
                precisely(order["quantity"], 8),
                "",
                "",
                pay_fee,  # True = send amount less fee
            )
            break  # SECURITY: must break!
        except Exception as error:
            print(f"sendtoaddress {network} access failed {error.args}")
        iteration += 1
    comptroller["tx_id"] = tx_id
    comptroller["order"] = order
    msg = it("red", f"{network} transferred".upper())
    chronicle(comptroller, msg)
    print(msg)
    return tx_id


def unit_test_ltcbtc_transfer():
    """
    UNIT TEST

    allow for user input to choose litecoin or bitcoin
    send tokens, watch them move using the definitions in this module
    """
    return ""  # FIXME build a unit test


if __name__ == "__main__":
    unit_test_ltcbtc_transfer()
