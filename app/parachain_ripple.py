r"""
parachain_ripple.py
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

Ripple parachain builder
"""

# FIXME enable flat fee and percent fee for gateway use

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-locals, too-many-nested-blocks, bare-except, broad-except
# pylint: disable=too-many-function-args, too-many-branches, too-many-statements

# STANDARD PYTHON MODULES
from json import dumps as json_dumps

# THIRD PARTY MODULES
from requests import get

# BITSHARES GATEWAY MODULES
from config import timing
from nodes import ripple_node
from utilities import chronicle


def verify_ripple_account(account, comptroller):
    """
    check to see if the address is valid

    :param str(account): a ripple address
    :param dict(coptroller): specify network and allow for logging of failure
    :return bool(): is this a valid address?
    """
    network = comptroller["network"]
    timeout = timing()[network]["request"]
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
    iteration = 0
    while True:
        try:
            ret = get(ripple_node(), data=data, timeout=timeout).json()["result"]
            break
        except Exception as error:
            print(f"verify_ripple_account access failed {error.args}")
        iteration += 1

    is_account = True
    if "account_data" not in ret.keys():
        is_account = False
        comptroller["msg"] = "invalid address"
        chronicle(comptroller)
    return bool(is_account)


def get_block_number(_):
    """
    ripple public api validated ledger

    :param _: required for cross chain compatability but not applicable to eosio
    :return int(ledger_index):
    """
    timeout = timing()["xrp"]["request"]
    data = json_dumps({"method": "ledger", "params": [{"ledger_index": "validated"}]})
    iteration = 0
    while True:
        try:
            ret = get(ripple_node(), data=data, timeout=timeout).json()
            ledger_index = int(ret["result"]["ledger"]["ledger_index"])
            break
        except Exception as error:
            print(f"get_validated_ledger access failed {error.args}")
        iteration += 1
    # print(ledger_index)
    return ledger_index


def get_ledger(ledger):
    """
    ripple public api list of transactions on a specific ledger

    :param int(ledger): current block number
    :return list(ret): a list of transactions on this block
    """
    timeout = timing()["xrp"]["request"]
    data = json_dumps(
        {
            "method": "ledger",
            "params": [{"ledger_index": ledger, "transactions": True, "expand": True}],
        }
    )
    iteration = 0
    while True:
        try:
            ret = get(ripple_node(), data=data, timeout=timeout).json()
            ret = ret["result"]["ledger"]["transactions"]
            ret = [t for t in ret if t["TransactionType"] == "Payment"]
            ret = [t for t in ret if t["metaData"]["TransactionResult"] == "tesSUCCESS"]
            break
        except Exception as error:
            print(f"get_ledger access failed {error.args}")
        iteration += 1
    # print(json_dumps(ret, sort_keys=True, indent=2))
    return ret


def apodize_block_data(comptroller, new_blocks):
    """
    build a parachain fragment of all new blocks

    :return dict(parachain) with int(block_num) keys
        and value dict() containing normalized transactions with keys:
        ["to", "from", "memo", "hash", "asset", "amount"]
    """
    parachain = {}
    # check every block from last check till now
    for block_num in new_blocks:
        transfers = []
        # get each new validated ledger
        transactions = get_ledger(block_num)
        # iterate through all transactions in the list of transactions
        for trx in transactions:
            # non XRP transaction amounts are in dict format
            if not isinstance(trx["Amount"], dict):
                # localize data from the transaction
                trx_amount = int(trx["Amount"]) / 10 ** 6  # convert drops to xrp
                trx_to = trx["Destination"]
                trx_from = trx["Account"]
                trx_hash = trx["hash"]
                trx_asset = "XRP"
                trx_memo = ""
                try:
                    trx_memo = trx["DestinationTag"]
                except:
                    pass
                if len(str(trx_memo)) == 10 and trx_amount > 0.1:
                    # build transfer dict and append to transfer list
                    # print(trx)
                    transfer = {
                        "to": trx_to,
                        "from": trx_from,
                        "memo": trx_memo,
                        "hash": trx_hash,
                        "asset": trx_asset,
                        "amount": trx_amount,
                    }
                    transfers.append(transfer)
        # build parachain fragment of transfers for new blocks
        parachain[str(block_num)] = transfers
    return parachain
