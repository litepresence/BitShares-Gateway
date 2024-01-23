r"""
parachain_eosio.py
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

EOSIO parachain builder
"""

# FIXME enable flat fee and percent fee for gateway use

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-locals, too-many-nested-blocks, broad-except
# pylint: disable=too-many-branches, too-many-statements
# pylint: disable=unused-import # ignore unused "Value" from multiprocessing

# REFERENCE
# https://github.com/eosmoto/eosiopy
# https://eosnodes.privex.io/?config=1
# https://developers.eos.io/welcome/latest/index
# https://developers.eos.io/manuals/eos/latest/nodeos/plugins/chain_api_plugin
#     /api-reference/index#operation/get_info << latest block numbern
#     /api-reference/index#operation/get_block  << transactions on a block
#     /api-reference/index#operation/get_block_header_state   << confirmations
# {protocol}://{host}:{port}/v1/chain/get_block_header_state

# STANDARD PYTHON MODULES
import time
from threading import Thread
from typing import Dict, List, Union

# THIRD PARTY MODULES
from requests import post

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, gateway_assets, timing
from ipc_utilities import chronicle, json_ipc
from nodes import eosio_node
from utilities import precisely, roughly


def verify_eosio_account(account: str, comptroller) -> bool:
    """
    Check to see if the EOSIO account is valid.

    :param str(account): EOSIO 12-character account name
    :return bool: True if the account is valid, False otherwise
    """
    timeout = timing()["eos"]["request"]
    url = eosio_node() + "/v1/chain/get_account"
    params = {"account_name": str(account)}
    iteration = 0
    while True:
        try:
            ret = post(url, json=params, timeout=timeout).json()
            break
        except Exception as error:
            print(f"verify_eosio_account access failed {error.args}")
        iteration += 1

    is_account = "created" in ret
    if not is_account:
        msg = "Invalid address"
        chronicle(comptroller, msg)
    return is_account


def get_block_number(_) -> int:
    """
    Get the current EOSIO block number.

    :param _: Required for cross chain compatability but not applicable to EOSIO
    :return int: Last irreversible block number
    """
    timeout = timing()["eos"]["request"]
    url = eosio_node() + "/v1/chain/get_info"
    iteration = 0
    while True:
        try:
            ret = post(url, timeout=timeout).json()
            irr_block = ret["last_irreversible_block_num"]
            break
        except Exception as error:
            print(f"get_irreversible_block access failed {error.args}")
        iteration += 1

    return irr_block


def eos_block_cache(new_blocks: List[int]) -> Dict[int, Dict]:
    """
    EOSIO has a 0.5 second block time, to prevail over network latency,
    concurrently fetch all new blocks using threading.

    :param list(new_blocks): List of block numbers to check
    :return dict: Block data for each block in new_blocks
    """

    def get_block(block_num: int, blocks_pipe: Dict[int, Union[int, Dict]]) -> None:
        """
        Get the block data via a separate thread.

        :param int(block_num): The current block number
        :param dict(blocks_pipe): Dictionary of block data
        :returns None:
        :updates: The dictionary of block data
        """
        timeout = timing()["eos"]["request"]
        url = eosio_node() + "/v1/chain/get_block"
        params = {"block_num_or_id": str(block_num)}
        iteration = 0
        while True:
            time.sleep(0.02 * iteration**2)
            try:
                ret = post(url, json=params, timeout=timeout).json()
                break
            except Exception as error:
                print(f"get_block access failed {error.args}")
            iteration += 1
        blocks_pipe[block_num] = ret

    block_processes = {}  # Dictionary of threads
    blocks_pipe = {}  # Interprocess communication dictionary
    # Spawn multiple threads to gather the "new" blocks
    for block_num in new_blocks:
        blocks_pipe[block_num] = 0
        block_processes[block_num] = Thread(
            target=get_block,
            args=(
                block_num,
                blocks_pipe,
            ),
        )
        block_processes[block_num].start()
    while True:
        time.sleep(0.2)
        if all(blocks_pipe.values()):
            break
    return blocks_pipe


def apodize_block_data(
    comptroller: Dict[str, Union[str, int]], new_blocks: list
) -> Dict[str, List[Dict[str, Union[str, float]]]]:
    """
    Build a parachain fragment of all new blocks.

    :param dict comptroller: A dict containing information about the network and other parameters.
        - "network" (str): The network identifier (e.g., "EOS" for EOSIO).
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
            - "asset" (str): The asset type (e.g., "EOS").
            - "amount" (float): The amount of the transaction.
    """
    parachain = {}
    # Using threading, get any new unchecked blocks
    blocks = eos_block_cache(new_blocks)
    # With new cache of blocks, check every block from last check till now
    for block_num in new_blocks:
        transfers = []
        transactions = blocks[block_num].get("transactions", [])
        # Iterate through all transactions in the list of transactions
        for trx in transactions:
            actions = trx.get("trx", {}).get("transaction", {}).get("actions", [])
            # If there are any, iterate through the actions
            for action in actions:
                action_name = action_account = trx_asset = ""
                try:
                    # Extract the transaction amount and asset name
                    qty = action["data"]["quantity"]
                    trx_asset = qty.split(" ")[1].upper()
                    trx_amount = float(qty.split(" ")[0])
                    action_name = action["name"]
                    action_account = action["account"]
                    trx_to = action["data"]["to"]
                    trx_from = action["data"]["from"]
                    trx_memo = action["data"]["memo"].replace(" ", "")
                    trx_hash = trx["trx"]["id"]
                except Exception:
                    pass
                # Sort by transfer ops
                if (
                    # SECURITY: Ensure it is the correct contract!!!
                    action_account == "eosio.token"
                    and action_name == "transfer"
                    and trx_asset == comptroller["network"].upper()
                    and trx_amount > 0.01
                    and len(trx_memo) <= 10
                ):
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
