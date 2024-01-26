r"""
parachain_xyz.py
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

XYZ (papertrade test chain) parachain builder 


To use, write transaction of the following format to pipe/xyz_transactions.txt:

{
    "type": str, "transfer" to trigger
    "amount": Graphene; precision 5
    "destination": to this account
    "account": from this account
    "memo": str
    "block_num": int blocknum to execute in, -1 for asap
}

"""

# FIXME enable flat fee and percent fee for gateway use

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-locals, too-many-nested-blocks, bare-except, broad-except
# pylint: disable=too-many-function-args, too-many-branches, too-many-statements

import hashlib
import time

# STANDARD MODULES
from typing import Dict, List, Union

# BITSHARES GATEWAY MODULES
from ipc_utilities import json_ipc


def verify_xyz_account(*_) -> bool:
    """
    Presume address is valid, because there is nothing to check against.

    :param *_: Required for cross-chain compatibility but no applicable to XYZ
    :return bool: True
    """
    return True


def get_block_number(_) -> int:
    """
    Get the current "block number".  Block number is emulated as every third second in unix time.

    :param _: Required for cross-chain compatibility but not applicable to XYZ
    :return int: Block number
    """
    return int(time.time() / 3)


def get_transactions(block_num) -> list:
    """
    Get the list of transactions to be executed in the given block.

    :param int(block_num): Block number
    :return list(ret): List of transactions on this block
    """
    all_trxs = json_ipc("xyz_transactions.txt") or []
    ret = []
    for idx, trx in enumerate(all_trxs):
        # if this block or "any" block (-1)
        if trx.get("block_num", block_num) == block_num:
            # add (mostly) unique hash to transaction
            trx["hash"] = hashlib.sha256(
                (str(idx) + str(block_num) + str(trx)).encode()
            ).hexdigest()
            # add to process list
            ret.append(trx)
    # update pending transactions
    json_ipc("xyz_transactions.txt", [])
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
        transactions = get_transactions(block_num)
        # Iterate through all transactions in the list of transactions
        for trx in transactions:
            #
            if trx["type"] == "transfer":
                # Localize data from the transaction
                trx_amount = int(trx["quantity"]) / 10**5  # Precision of 5
                trx_to = trx["to"]
                trx_from = trx["public"]
                trx_hash = trx["hash"]
                trx_asset = comptroller["network"].upper()
                trx_memo = trx.get("memo", "")
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
