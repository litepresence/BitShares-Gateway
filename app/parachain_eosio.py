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
# pylint: disable=bad-continuation, too-many-branches, too-many-statements
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
import traceback
from ctypes import c_wchar_p
from json import dumps as json_dumps
from multiprocessing import Manager, Process, Value

# THIRD PARTY MODULES
from requests import post

# BITSHARES GATEWAY MODULES
from address_allocator import unlock_address  # NOTE not actually used
from config import foreign_accounts, gateway_assets, timing
from issue_or_reserve import issue_or_reserve
from nodes import eosio_node
from signing_bitshares import issue, reserve
from utilities import (chronicle, encode_memo, it, json_ipc, line_number,
                       precisely, roughly, timestamp)


def verify_eosio_account(account, comptroller):
    """
    check to see if the address is valid

    :param str(account_name): eosio 12 character account name
    :return bool(is_account):
    """
    timeout = timing()["eos"]["request"]
    url = eosio_node() + "/v1/chain/get_account"
    params = {"account_name": str(account)}
    data = json_dumps(params)
    iteration = 0
    while True:
        try:
            ret = post(url, data=data, timeout=timeout).json()
            break
        except Exception as error:
            print(f"verify_eosio_account access failed {error.args}")
        iteration += 1
    is_account = True
    if "created" not in ret.keys():
        is_account = False
        msg = "invalid address"
        chronicle(comptroller, msg)
    return is_account


def get_block_number(_):
    """
    get current eosio block number
    :param _: required for cross chain compatability but not applicable to eosio
    :return int(irr_block):
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


def eos_block_cache(new_blocks):
    """
    eosio has a 0.5 second block time, to prevail over network latency:
    concurrently fetch all new blocks with multiprocessing

    :param list(new_blocks): a list of block numbers we have not checked yet
    :return list(blocks): a list of block data for each block in new_blocks
    """

    def get_block(block_num, blocks_pipe):
        """
        return the block data via multiprocessing Value pipe

        :param int(block_num): the current block number we're testing
        :param dict(blocks_pipe): a dict of multiprocessing c_wchar_p Value objects
        :returns None:
        :updates: the multiprocessing Value pipe
        """
        timeout = timing()["eos"]["request"]
        url = eosio_node() + "/v1/chain/get_block"
        data = json_dumps({"block_num_or_id": str(block_num)})
        iteration = 0
        while True:
            try:
                ret = post(url, data=data, timeout=timeout).json()
                break
            except Exception as error:
                print(f"get_block access failed {error.args}")
            iteration += 1
        blocks_pipe[block_num].value = ret

    block_processes = {}  # dictionary of multiprocessing "Process" events
    blocks_pipe = {}  # dictionary of multiprocessing "Value" pipes
    # spawn multpiple processes to gather the "new" blocks
    for block_num in new_blocks:
        manager = Manager()
        blocks_pipe[block_num] = manager.Value(c_wchar_p, "")
        block_processes[block_num] = Process(
            target=get_block, args=(block_num, blocks_pipe,)
        )
        block_processes[block_num].start()
    # join all subprocess back to main process; wait for all to finish
    for block_num in new_blocks:
        block_processes[block_num].join()
    # extract the blocks from each "Value" in blocks_pipe
    blocks = {}
    for block_num, block in blocks_pipe.items():
        # create block number keyed dict of block data dicts
        blocks[block_num] = block.value

    return blocks


def apodize_block_data(comptroller, new_blocks):
    """
    build a parachain fragment of all new blocks

    :return dict(parachain) with int(block_num) keys
        and value dict() containing normalized transactions with keys:
        ["to", "from", "memo", "hash", "asset", "amount"]
    """
    chronicle(comptroller, "initilizing parachain")
    parachain = {}
    # using multiprocessing, get any new unchecked blocks
    blocks = eos_block_cache(new_blocks)
    # with new cache of blocks, check every block from last check till now
    for block_num in new_blocks:
        transfers = []
        transactions = []
        try:
            # get each new irreversible block, extract the transactions
            block = blocks[block_num]
            transactions = block["transactions"]
        except:
            pass
        # iterate through all transactions in the list of transactions
        for trx in transactions:
            actions = []
            try:
                # check if there are any actions in this transaction
                actions = trx["trx"]["transaction"]["actions"]
            except:
                pass
            # if there are any, iterate through the actions
            for action in actions:
                action_name = ""
                action_account = ""
                trx_asset = ""
                try:
                    # extract the transaction amount and asset name
                    qty = action["data"]["quantity"]
                    trx_asset = qty.split(" ")[1].upper()
                    trx_amount = float(qty.split(" ")[0])
                    action_name = action["name"]
                    action_account = action["account"]
                    trx_to = action["data"]["to"]
                    trx_from = action["data"]["from"]
                    trx_memo = action["data"]["memo"].replace(" ", "")
                    trx_hash = trx["trx"]["id"]

                except:
                    pass
                # sort by tranfer ops
                if (
                    # SECURITY: ensure it is the correct contract!!!
                    action_account == "eosio.token"
                    and action_name == "transfer"
                    and trx_asset == "EOS"
                    and trx_amount > 0.01
                    and len(trx_memo) <= 10
                ):
                    # print(trx)
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
