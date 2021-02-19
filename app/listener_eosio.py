r"""
listener_eosio.py
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

EOSIO Block Ops Listener

triggers:

    issue UIA upon deposited foreign coin
    reserve UIA upon confirmed withdrawal
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
from hashlib import sha256
from json import dumps as json_dumps
from multiprocessing import Manager, Process, Value

# THIRD PARTY MODULES
from requests import post

# BITSHARES GATEWAY MODULES
from address_allocator import unlock_address  # NOTE not actually used
from config import foreign_accounts, gateway_assets, nil, timing
from issue_or_reserve import issue_or_reserve
from nodes import eosio_node
from signing_bitshares import issue, reserve
from utilities import chronicle, it, line_number, precisely, roughly, timestamp


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


def listener_eosio(comptroller):
    """
    for every block from initialized until detected
        check for transaction to the gateway
            issue or reserve uia upon receipt of gateway transfer

    NOTE: use multiprocessing to process fast moving blocks concurrently

    NOTE: eosio has a complex block structure:
    :dict(block["transactions"][i]["trx"]["transaction"]["actions"][j])
        :key str("name") # 'transfer' etc.
        :key dict("data") # keys: [to, from, quantity]
        :key srt("account") # !!! SECURITY WARN, MUST BE: 'eosio.token' !!!

    :dict(comproller) contains full audit trail and these pertinent keys:
      :key int(account_idx) # from gateway_state.py
      :key str(issuer_action) # reserve, issue, or None in unit test case
      :key str(client_id) #1.2.X
      :key int(nonce) # the millesecond label for this listening event

    for reserving withdrawals two additional comptroller keys are available:
      :key float(withdrawal_amount)
      :key str(client_address)

    updates the comptroller then :calls: issue_or_reserve()

    :return dict(comtroller) # updated audit dictionary
    """
    # localize the audit trail
    nonce = comptroller["nonce"]
    client_id = comptroller["client_id"]
    new_blocks = comptroller["new_blocks"]
    checked_blocks = comptroller["checked_blocks"]
    # hash the client id and nonce to be checked vs the transaction memo
    trx_hash = str(sha256(str(client_id).encode("utf-8") + str(nonce).encode("utf-8")))
    # using multiprocessing, get any new unchecked blocks
    blocks = eos_block_cache(new_blocks)
    # with new cache of blocks, check every block from last check till now
    for block_num in new_blocks:
        if block_num not in checked_blocks:
            checked_blocks.append(block_num)
        comptroller["block_num"] = block_num
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
                    str_amount = comptroller["str_amount"] = precisely(trx_amount, 8)
                    action_name = action["name"]
                    action_account = action["account"]
                except:
                    pass
                # sort by tranfer ops
                if (
                    # SECURITY: ensure it is the correct contract!!!
                    action_account == "eosio.token"
                    and action_name == "transfer"
                    and trx_asset == "EOS"
                ):
                    # print("transfer detected")
                    # extract transfer op data
                    trx_to = action["data"]["to"]
                    trx_from = action["data"]["from"]
                    trx_memo = action["data"]["memo"].replace(" ", "")
                    # issue UIA to client_id
                    # upon receipt of their foreign funds
                    # eos deposits will use one address
                    # distinguish between deposits by memo
                    memo_check = bool(trx_memo == trx_hash)
                    comptroller["trx_action"] = action
                    comptroller["trx_hash"] = trx_hash
                    # update the audit trail
                    comptroller["trx_to"] = trx_to
                    comptroller["trx_from"] = trx_from
                    comptroller["str_amount"] = str_amount
                    comptroller["trx_amount"] = trx_amount
                    comptroller["memo_check"] = memo_check
                    comptroller["checked_blocks"] = checked_blocks
                    # issue or reserve and return the modified audit trail
                    comptroller = issue_or_reserve(comptroller)

    return comptroller
