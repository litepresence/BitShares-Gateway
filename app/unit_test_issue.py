r"""
unit_test_issue.py
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

Unit Test BitShares:

ISSUE asset to test_accounts() client
TRANSFER asset back to foreign_accounts()
RESERVE asset
"""

# BITSHARES GATEWAY MODULES
from config import gateway_assets, test_accounts
from nodes import bitshares_nodes
from signing.bitshares.graphene_auth import broker

# GLOBALS
AMOUNT = 1  # must be integer during testing due to precision of testnet uia


def unit_test_issue():
    """
    print chain state
    issue, transfer, reserve a BitShares UIA
    print chain state again
    """

    network = input(
        "Enter XRP or EOS to unit test Bitshares UIA Issue, " + "Transfer, and Reserve"
    ).lower()

    gate_header = {
        "asset_id": gateway_assets()[network]["asset_id"],
        "asset_precision": gateway_assets()[network]["asset_precision"],
        # gate account details
        "account_id": gateway_assets()[network]["issuer_id"],
        "account_name": gateway_assets()[network]["issuer_public"],
        "wif": gateway_assets()[network]["issuer_private"],
    }
    test_header = {
        "asset_id": gateway_assets()[network]["asset_id"],
        "asset_precision": gateway_assets()[network]["asset_precision"],
        # test account details
        "account_id": test_accounts()["bts"]["id"],
        "account_name": test_accounts()["bts"]["public"],
        "wif": test_accounts()["bts"]["private"],
    }
    order = {"nodes": bitshares_nodes()}
    # login to accounts
    order["edicts"] = [{"op": "login"}]
    order["header"] = test_header
    print("Log In", order["header"]["account_name"], broker(order), "\n\n")
    order["header"] = gate_header
    print("Log In", order["header"]["account_name"], broker(order), "\n\n")
    # issue asset
    order["edicts"] = [
        {
            "op": "issue",
            "amount": AMOUNT,
            "account_id": test_header["account_id"],
            "memo": "",
        }
    ]
    print({k: v for k, v in order["header"].items() if k != "wif"})
    print("Issue Asset", order["edicts"], broker(order), "\n\n")
    # transfer
    order["header"] = test_header
    order["edicts"] = [
        {
            "op": "transfer",
            "amount": AMOUNT,
            "account_id": gate_header["account_id"],
            "memo": "",
        }
    ]
    print({k: v for k, v in order["header"].items() if k != "wif"})
    print("Transfer Asset", order["edicts"], broker(order), "\n\n")
    # reserve asset
    order["header"] = gate_header
    order["edicts"] = [{"op": "reserve", "amount": AMOUNT}]
    print({k: v for k, v in order["header"].items() if k != "wif"})
    print("Reserve Asset", order["edicts"], broker(order), "\n\n")


def refill_test_account():
    """
    manually add uia funds to continue testing
    """
    networks = ["xrp", "eos"]
    for network in networks:
        order = {"nodes": bitshares_nodes()}
        order["header"] = {
            "asset_id": gateway_assets()[network]["asset_id"],
            "asset_precision": gateway_assets()[network]["asset_precision"],
            # gate account details
            "account_id": gateway_assets()[network]["issuer_id"],
            "account_name": gateway_assets()[network]["issuer_public"],
            "wif": gateway_assets()[network]["issuer_private"],
        }
        order["edicts"] = [
            {
                "op": "issue",
                "amount": 100,
                "account_id": test_accounts()["bts"]["id"],
                "memo": "",
            }
        ]
        print({k: v for k, v in order["header"].items() if k != "wif"})
        print("Issue Asset", order["edicts"], broker(order), "\n\n")


def main():
    """
    Enter 1 to refill test account or 2 to unit test
    """
    choice = int(input(main.__doc__))
    dispatch = {
        1: refill_test_account,
        2: unit_test_issue,
    }
    dispatch[choice]()  # ignore pointless-statement


if __name__ == "__main__":
    main()
