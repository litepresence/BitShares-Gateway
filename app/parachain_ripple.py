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

# STANDARD MODULES
from json import dumps as json_dumps
from typing import Dict, List, Union

# THIRD PARTY MODULES
from requests import get

# BITSHARES GATEWAY MODULES
from config import timing
from ipc_utilities import chronicle
from nodes import ripple_node


def verify_ripple_account(account: str, comptroller: Dict[str, Union[str, int]]) -> bool:
    """
    Check if the Ripple address is valid.

    :param str(account): Ripple address
    :param dict(comptroller): Dictionary used to specify the network and log failure
    :return bool: True if the address is valid, False otherwise
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
        msg = "Invalid address"
        chronicle(comptroller, msg)
    return bool(is_account)


def get_block_number(_) -> int:
    """
    Get the validated ledger index from the Ripple public API.

    :param _: Required for cross-chain compatibility but not applicable to Ripple
    :return int: Validated ledger index
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

    return ledger_index


def get_ledger(ledger: int) -> list:
    """
    Get the list of transactions on a specific ledger from the Ripple public API.

    :param int(ledger): Validated ledger index
    :return list(ret): List of transactions on this ledger
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

    return ret


def apodize_block_data(
    comptroller: Dict[str, Union[str, int]], new_blocks: list
) -> Dict[str, List[Dict[str, Union[str, float]]]]:
    """
    Build a parachain fragment of all new blocks.

    :param dict comptroller: A dict containing information about the network and other parameters.
        - "network" (str): The network identifier (e.g., "xrp" for Ripple).
        - "msg" (str): A message attribute for storing additional information.
    :param List[int] new_blocks: List of block numbers to process and build the parachain fragment.
    :return Dict[str, List[Dict[str, Union[str, float]]]]:
            A dictionary representing the parachain with block numbers as keys.
            Each value is a list of transfers,
            where each transfer is represented as a dictionary with keys:
            - "to" (str): The recipient address.
            - "from" (str): The sender address.
            - "memo" (str): The memo associated with the transaction.
            - "hash" (str): The hash identifier of the transaction.
            - "asset" (str): The asset type (e.g., "XRP").
            - "amount" (float): The amount of the transaction.
    """
    parachain = {}
    # Check every block from the last check till now
    for block_num in new_blocks:
        transfers = []
        # Get each new validated ledger
        transactions = get_ledger(block_num)
        # Iterate through all transactions in the list of transactions
        for trx in transactions:
            # Non-XRP transaction amounts are in dict format
            if not isinstance(trx["Amount"], dict):
                # Localize data from the transaction
                trx_amount = int(trx["Amount"]) / 10**6  # Convert drops to XRP
                trx_to = trx["Destination"]
                trx_from = trx["Account"]
                trx_hash = trx["hash"]
                trx_asset = comptroller["network"].upper()
                trx_memo = trx.get("DestinationTag", "")
                if len(str(trx_memo)) == 10 and trx_amount > 0.1:
                    # Build transfer dict and append to transfer list
                    transfer = {
                        "to": trx_to,
                        "from": trx_from,
                        "memo": trx_memo,
                        "hash": trx_hash,
                        "asset": trx_asset,
                        "amount": trx_amount,
                    }
                    transfers.append(transfer)
        # Build parachain fragment of transfers for new blocks
        parachain[str(block_num)] = transfers

    return parachain
