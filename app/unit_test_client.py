r"""
unit_test_client.py
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

Client Side Unit Tests for Gateway
"""

# STARDARD PYTHON MODULES
import time
from json import dumps as json_dumps
from pprint import pprint

# THIRD PARTY MODULES
from requests import get

# BITSHARES GATEWAY MODULES
from config import (foreign_accounts, gateway_assets, server_config,
                    test_accounts)
from process_withdrawals import rpc_balances, rpc_get_objects
from signing_eosio import eos_balance, eos_transfer
from signing_ltcbtc import ltcbtc_balance, ltcbtc_transfer, ltcbtc_balances
from signing_ripple import xrp_balance, xrp_transfer
from utilities import wss_handshake

# FIXME currently only tested local network, single client request
# FIXME should be unit tested on two vpn machines to simulate www request
# FIXME should be unit tested by multiprocess to simulate multiple users
# SERVER_URL = "http://127.0.0.1:8000/gateway"

# GLOBALS
URL = server_config()["url"]
PORT = server_config()["port"]
ROUTE = server_config()["route"]
# NOTE: no trailing forward slash!
SERVER_URL = f"http://{URL}:{PORT}/{ROUTE}"


def gate_balances(network, get_balance):
    """
    check gateway xrp balances
    """
    for gate in foreign_accounts()[network]:
        comptroller = {"network":network}
        print(
            f"Gateway {network} balance for".ljust(30),
            gate["public"],
            get_balance(gate["public"], comptroller),
        )


def full_balances(network, get_balance):
    """
    check gateway foreign chain balances
    check client foreign chain balance
    check client uia balance
    """

    comptroller = {"network": network}
    print(network, type(network), comptroller, type(comptroller))
    # check gateway foreign chain balances
    if network in ["ltc", "btc"]:
        ltcbtc_balances(None, comptroller)
    else:
        gate_balances(network, get_balance)
    # check client foreign chain balance
    print(
        f"\nClient {network} balance for".ljust(31),
        test_accounts()[network]["public"],
        get_balance(test_accounts()[network]["public"], comptroller),
    )
    # check client bts uia balance
    rpc = wss_handshake("")
    """
    print(
        "\nClient UIA balance of".ljust(31),
        gateway_assets()[network]["asset_name"],
        gateway_assets()[network]["asset_id"],
        "                  ",
        float(
            rpc_balances(
                rpc,
                test_accounts()["bts"]["public"],
                gateway_assets()[network]["asset_id"],
            )["amount"]
        )
        / 10 ** gateway_assets()[network]["asset_precision"],
        "\n\n",
    )
    """


def uia_supply():
    """
    print the global supply of the gateway user issued assets
    """
    rpc = wss_handshake("")
    print("EOS UIA NAME AND CURRENT SUPPLY")
    eos_objects = rpc_get_objects(rpc, [gateway_assets()["eos"]["asset_id"]])
    print(eos_objects[0]["symbol"])
    print(
        float(
            rpc_get_objects(rpc, [gateway_assets()["eos"]["dynamic_id"]])[0][
                "current_supply"
            ]
        )
        / 10 ** eos_objects[0]["precision"]
    )
    print("\nXRP UIA NAME AND CURRENT SUPPLY")
    xrp_objects = rpc_get_objects(rpc, [gateway_assets()["xrp"]["asset_id"]])
    print(xrp_objects[0]["symbol"])
    print(
        float(
            rpc_get_objects(rpc, [gateway_assets()["xrp"]["dynamic_id"]])[0][
                "current_supply"
            ]
        )
        / 10 ** xrp_objects[0]["precision"]
    )


def test_deposit(network, get_balance):
    """
    check gateway foreign chain balances
    check client foreign chain balance
    check client bts uia balance
    get request for foreign chain deposit address
    deposit foreign chain to gateway
    server should auto issue uia.foreign chain to client
    check gateway foreign chain balances
    check client foreign chain balance
    check client bts uia balance
    """
    # start balance
    print("\n\nbe sure to run block_explorers.py to watch the withdrawal\n\n")
    input("press Enter to get starting balances...")
    full_balances(network, get_balance)
    uia_supply()
    # make a GET request for a foreign chain deposit address
    client_id = test_accounts()["bts"]["id"]
    uia_name = gateway_assets()[network]["asset_name"]
    params = {
        "client_id": client_id,  # bitshares account id 1.2.X
        "uia_name": uia_name,
    }
    print(SERVER_URL + f"?client_id={client_id}&uia_name={uia_name}")
    input("\npress Enter to make request for gateway deposit address\n")
    data = get(url=SERVER_URL, params=params).json()
    print("Server Response:")
    pprint(data)
    print("\nwaiting 10 seconds to make deposit\n")
    time.sleep(10)
    print()
    # auto deposit foreign chain to gateway
    order = {}
    order["quantity"] = 1
    order["to"] = data["deposit_address"]
    order["public"] = test_accounts()[network]["public"]  # pass the sender PUBLIC key
    order["private"] = test_accounts()[network][
        "private"
    ]  # pass the sender PRIVATE key
    if network == "xrp":
        print(xrp_transfer(order, {"test": "test"}))
    elif network == "eos":
        print(eos_transfer(order, {"test": "test"}))
    elif network == "ltc":
        print(ltcbtc_transfer(order, {"network": network, "test": "test"}))
    elif network == "btc":
        print(ltcbtc_transfer(order, {"network": network, "test": "test"}))

    while 1:  # end balance
        input("\n\nwait a few minutes then press Enter to get full balances again\n")
        full_balances(network, get_balance)
        uia_supply()
        print(f"\n\nconfirm gateway received real {network} crypto currency")
        print(f"and issued a test {network} uia of equal amount to cover it")


def test_withdrawal(network, get_balance):
    """
    check balances
    send uia test token to uia issuer with client foreign chain address as memo
    bts listener should:
        send foreign currency
        reserve uia
    check balances again
    """
    # start balance
    print("\n\nbe sure to run block_explorers.py to watch the withdrawal\n\n")
    input("press Enter to get starting balances...")
    full_balances(network, get_balance)
    uia_supply()
    # prompt user to withdraw
    print(
        "\n\nusing the Reference UI, signed in as:\n\n",
        test_accounts()["bts"]["public"],
        "\n\nmake a transfer of test asset:\n\n",
        gateway_assets()[network]["asset_name"],
        "\n\nof exact quantity:\n\n",
        1,
        "\n\nto:\n\n",
        gateway_assets()[network]["issuer_public"],
        f"\n\nyou MUST include a memo with your {network} address:\n\n",
        test_accounts()[network]["public"],
    )
    while 1:  # end balance
        input("\n\nwait a few minutes then press Enter to get full balances again\n")
        full_balances(network, get_balance)
        uia_supply()
        print(f"\n\nconfirm gateway received uia {network} crypto currency")
        print(f"and reserved a test {network} uia of equal amount to cover it")


def test_recycler(network, get_balance, do_transfer):
    """
    check gateway xrp balances
    send funds to xrp acct[1] and acct[2]
    check gateway xrp balances again to confirm funds automatically move to acct[0]
    """
    gate_balances(network, get_balance)
    # deposit to gateway
    order = {}
    order["public"] = foreign_accounts()[network][0][
        "public"
    ]  # pass the sender PUBLIC key
    order["private"] = foreign_accounts()[network][0][
        "private"
    ]  # pass the sender PRIVATE key
    order["to"] = foreign_accounts()[network][1]["public"]
    order["quantity"] = 1
    do_transfer(order)
    gate_balances(network, get_balance)
    print("\n\nwaiting 1 minute for recycler to move funds")
    time.sleep(60)
    print("Done waiting.")
    print("\n\n")
    gate_balances(network, get_balance)


def main():
    """
    user enters first choice to unit test eos or xrp
    user enters second choice to choose test type
    main then dispatches the choice to the appropriate test
    """
    # user input
    print("\033c")
    input("\n\nInitialize your Gateway in another terminal then press Enter\n\n")
    choices = {1: "withdraw", 2: "deposit", 3: "recycle", 4: "balances"}
    network = input("Enter LTC,BTC, XRP or EOS to test gateway\n\n   ").lower()
    print("\ntest options:\n\n", json_dumps(choices))
    selection = int(input("\nchoice: "))
    print(f"\n\nTesting {network} {choices[selection]} ({selection})\n\n")
    # dispatch network choice
    if network == "eos":
        get_balance = eos_balance
        do_transfer = eos_transfer
    elif network == "xrp":
        get_balance = xrp_balance
        do_transfer = xrp_transfer
    elif network == "ltc":
        get_balance = ltcbtc_balance
        do_transfer = ltcbtc_transfer
    elif network == "btc":
        get_balance = ltcbtc_balance
        do_transfer = ltcbtc_transfer
    # dispatch test choice
    if selection == 1:
        test_withdrawal(network, get_balance)
    elif selection == 2:
        test_deposit(network, get_balance)
    elif selection == 3:
        test_recycler(network, get_balance, do_transfer)
    elif selection == 4:
        full_balances(network, get_balance)


if __name__ == "__main__":
    main()
