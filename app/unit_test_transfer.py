r"""
unit_test_transfer.py
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

Get balances and transfer xrp and eos
"""

# STANDARD PYTHON MODULES
import time
from pprint import pprint

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, test_accounts
from parachain_ltcbtc import get_received_by
from signing_eosio import eos_balance, eos_transfer
from signing_ltcbtc import ltcbtc_balance, ltcbtc_balances, ltcbtc_transfer
from signing_ripple import xrp_balance, xrp_transfer


def balances(comptroller, order):
    """
    eos and xrp account balance
    """
    network = comptroller["network"]
    if network == "eos":
        print("to", eos_balance(order["to"], comptroller))
        print("from", eos_balance(order["public"], comptroller))

    elif network == "xrp":
        print("to", xrp_balance(order["to"], comptroller))
        print("from", xrp_balance(order["public"], comptroller))

    elif network in ["ltc", "btc"]:
        print("\nbalance\n", ltcbtc_balance(None, comptroller))
        print("\nunspent")
        pprint(ltcbtc_balances(None, comptroller))
        print("received")
        for idx, address in enumerate(foreign_accounts()[network]):
            print(
                f"gate {idx} received",
                address["public"],
                "\n",
                get_received_by(address["public"], comptroller),
            )
        print(
            "test received",
            test_accounts()[network]["public"],
            "\n",
            get_received_by(test_accounts()[network]["public"], comptroller),
        )


def all_balances(comptroller):
    """
    eos and xrp account balance
    """
    network = comptroller["network"]

    accts = foreign_accounts()[network]
    test = test_accounts()[network]

    if network == "eos":
        print("   0:", eos_balance(accts[0]["public"], comptroller))
        print("test:", eos_balance(test["public"], comptroller))

    elif network == "xrp":
        print("   0:", xrp_balance(accts[0]["public"], comptroller))
        print("   1:", xrp_balance(accts[1]["public"], comptroller))
        print("   2:", xrp_balance(accts[2]["public"], comptroller))
        print("test:", xrp_balance(test["public"], comptroller))

    elif network in ["ltc", "btc"]:
        print("\nbalance\n", ltcbtc_balance(None, comptroller))
        print("\nunspent")
        pprint(ltcbtc_balances(None, comptroller))
        print("received")
        for idx, address in enumerate(foreign_accounts()[network]):
            print(
                f"gate {idx} received",
                address["public"],
                "\n",
                get_received_by(address["public"], comptroller),
            )
        print(
            "test received",
            test_accounts()[network]["public"],
            "\n",
            get_received_by(test_accounts()[network]["public"], comptroller),
        )


def unit_test_transfer():
    """
    user input for network, to/from, and quantity
    check balances prior
    send a test transfer
    check balances after
    """
    dispatch = {
        1: "ltc",
        2: "btc",
        3: "xrp",
        4: "eos",
    }
    print("\nUNIT TEST TRANSFER\n")
    for key, val in dispatch.items():
        print("    ", key, ":", val)
    choice = int(input("\nenter choice number:\n\n"))
    network = dispatch[choice]
    dispatch = {
        0: "send from test account to gateway 0",
        1: "send from test account to gateway 1",
        2: "send from test account to gateway 2",
        3: "send from gateway 0 to test account",
        4: "just check balances on test and gates 0,1,2",
    }
    for key, val in dispatch.items():
        print("    ", key, ":", val)
    test_choice = int(input("\nenter choice number:\n\n"))

    comptroller = {"network": network}

    if test_choice == 4:
        all_balances(comptroller)
    else:
        quantity = float(input("\nenter quantity to send:\n\n"))
        order = {}
        order["quantity"] = quantity
        if test_choice == 3:
            order["to"] = test_accounts()[network]["public"]
            order["public"] = foreign_accounts()[network][0]["public"]
            order["private"] = foreign_accounts()[network][0]["private"]

        else:
            order["to"] = foreign_accounts()[network][test_choice]["public"]
            order["public"] = test_accounts()[network]["public"]
            order["private"] = test_accounts()[network]["private"]

        balances(comptroller, order)
        if network == "xrp":
            print(xrp_transfer(order, comptroller))
        elif network == "eos":
            print(eos_transfer(order, comptroller))
        elif network in ["ltc", "btc"]:
            print(ltcbtc_transfer(order, comptroller))
        time.sleep(5)
        balances(comptroller, order)


if __name__ == "__main__":
    unit_test_transfer()
