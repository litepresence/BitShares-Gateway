r"""
signing_eosio.py
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

Eosio Transfer Operations and Account Balances
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except

# STANDARD PYTHON MODULES
import traceback
from json import dumps as json_dumps

from requests import post

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, test_accounts, timing
from ipc_utilities import chronicle
from nodes import eosio_node

# THIRD PARTY MODULES
from signing.eosio.eosiopy import eosio_config
from signing.eosio.eosiopy.eosioparams import EosioParams
from signing.eosio.eosiopy.nodenetwork import NodeNetwork
from signing.eosio.eosiopy.rawinputparams import RawinputParams
from utilities import it, line_number, precisely, timestamp


def eos_balance(account, comptroller):
    """
    eosio public api consensus of EOS balance
    """
    timeout = timing()["eos"]["request"]
    url = eosio_node() + "/v1/chain/get_currency_balance"
    params = {"code": "eosio.token", "account": account, "symbol": "EOS"}
    iteration = 0
    while True:
        try:
            data = json_dumps(params)
            ret = post(url, data=data, timeout=timeout).json()
            return float(ret[0].split(" ")[0])
        except Exception:
            print(traceback.format_exc())
            msg = "failed to fetch balance"
            chronicle(comptroller, msg)
        iteration += 1


def eos_transfer(order, comptroller):
    """
    serialize, sign, and broadcast an order dictionary with nine keys
    """
    # FIXME carefully consider the SECURITY of this event!
    timestamp()
    line_number()
    print("\nORDER\n\n", {k: v for k, v in order.items() if k != "private"}, "\n")
    while 1:
        # configure the url and port
        eosio_config.url = eosio_node()
        eosio_config.port = ""
        # assemble the transfer operation dictionary
        operation = {
            "from": order["public"],
            "memo": "",
            # eos must have 4 decimal places formatted as string with space and "EOS"
            "quantity": precisely(order["quantity"], 4) + " EOS",
            "to": order["to"],
        }
        print("\nOPERATION\n\n", operation, "\n")
        # serialize the transfer operation
        raw = RawinputParams(
            "transfer",  # the operation type
            operation,  # the parameters
            "eosio.token",  # the contract; for our purposes always "eosio.token"
            order["public"] + "@active",  # the permitted party (or @owner)
        )
        print("\nSERIALIZE\n\n", raw.params_actions_list, "\n")
        # sign the transfer operation
        params = EosioParams(raw.params_actions_list, order["private"])
        print("\nSIGN\n\n", params.trx_json, "\n")
        # broadcast the transfer to the network
        try:
            ret = NodeNetwork.push_transaction(params.trx_json)
            if "processed" not in ret.keys():
                raise ValueError("NOT PROCESSED")
            break  # SECURITY: must break!
        except Exception as error:
            print(error)
            print(it("red", "BROADCAST FAILED"), "trying again...")
            msg = "eos transfer broadcast failed"
            chronicle(comptroller, msg)
            continue
    print(it("red", "EOS TRANSFERRED"), "\nBROADCAST\n\n", ret)
    comptroller["tx_id"] = ret
    comptroller["order"] = order
    msg = "eos transferred"
    chronicle(comptroller, it("red", "EOS TRANSFERRED"))
    return ret


def unit_test_eos_transfer():
    """
    UNIT TEST demo transfer
    """
    try:
        order = {}
        order["private"] = test_accounts()["eos"]["private"]
        order["public"] = test_accounts()["eos"]["public"]
        order["to"] = foreign_accounts()["eos"][0]["public"]
        order["quantity"] = 0.0001
        # serialize, sign, and broadcast
        comptroller = {"test": "test"}
        eos_transfer(order, comptroller)
    except Exception:
        print(traceback.format_exc())


if __name__ == "__main__":
    unit_test_eos_transfer()
