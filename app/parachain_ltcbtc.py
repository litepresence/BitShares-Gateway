r"""
parachain_ltcbtc.py
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

Litecoin and Bitcoin parachain builder
"""

# FIXME enable flat fee and percent fee for gateway use

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-locals, too-many-nested-blocks, bare-except, broad-except
# pylint: disable=too-many-function-args, too-many-branches, too-many-statements

# STANDARD PYTHON MODULES
import time
from typing import Dict, List, Union

# BITSHARES GATEWAY MODULES
from utilities import create_access, precisely


def verify_ltcbtc_account(account: str, comptroller: Dict) -> bool:
    """
    Check to see if the Litecoin or Bitcoin address is valid.

    :param str(account): Litecoin or Bitcoin address
    :param dict(comptroller): Used to distinguish LTC vs BTC network
    :return bool: True if the address is valid, False otherwise
    """
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration**2)
        try:
            access = create_access(network)
            return bool(access.validateaddress(account)["isvalid"])
        except Exception as error:
            print(f"get_received_by {network} access failed {error.args}")
        iteration += 1


def get_block_number(network: Dict) -> int:
    """
    Get the current Litecoin or Bitcoin block number.

    :param dict(comptroller): Used to distinguish LTC vs BTC network
    :return int: Current block number
    """
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration**2)
        try:
            access = create_access(network)
            return int(access.getblockcount())
        except Exception as error:
            print(f"get_block_count {network} access failed {error.args}")
        iteration += 1


def get_block(network: Dict, block_num: int) -> List[Dict]:
    """
    Extract Litecoin or Bitcoin block transactions given a block number.
    """
    access = create_access(network)
    block_num = access.getblockcount()
    block_hash = access.getblockhash(block_num)
    block_data = access.getblock(block_hash)
    transactions = block_data["tx"]
    decoded_trxs = []
    for _, trx in enumerate(transactions):
        raw_trx = access.getrawtransaction(trx)
        decoded_trx = access.decoderawtransaction(raw_trx)
        decoded_trxs.append(decoded_trx)
    return decoded_trxs


def get_received_by(address: str, comptroller: Dict) -> float:
    """
    Return the amount received by Litecoin or Bitcoin address.

    :param str(address): Litecoin or Bitcoin address
    :param dict(comptroller): Used to distinguish LTC vs BTC network
    :return float: Total received by this address
    """
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration**2)
        try:
            access = create_access(comptroller["network"])
            return float(precisely(float(access.getreceivedbyaddress(address, 2)), 8))
        except Exception as error:
            print(f"get_received_by {network} access failed {error.args}")
        iteration += 1


def apodize_block_data(
    comptroller: Dict[str, Union[str, int]], new_blocks: list
) -> Dict[str, List[Dict[str, Union[str, float]]]]:
    """
    Build a parachain fragment of all new blocks.

    :param dict comptroller: A dict containing information about the network and other parameters.
        - "network" (str): The network identifier (e.g., "ltc" for Litecoin).
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
            - "asset" (str): The asset type (e.g., "LTC").
            - "amount" (float): The amount of the transaction.
    """
    network = comptroller["network"]
    parachain = {}
    # check every block from last check till now
    for block_num in new_blocks:
        transfers = []
        # get each new validated ledger
        transactions = get_block(network, block_num)
        # iterate through all transactions in the list of transactions
        for trx in transactions:
            for vout in trx["vout"]:
                if "addresses" in vout["scriptPubKey"].keys():
                    if len(vout["scriptPubKey"]["addresses"]) == 1:
                        # localize data from the transaction
                        trx_amount = float(vout["value"])
                        trx_to = vout["scriptPubKey"]["addresses"][0]
                        trx_from = ""
                        trx_hash = trx["txid"]
                        trx_asset = network.upper()
                        trx_memo = ""
                        # build transfer dict and append to transfer list
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
