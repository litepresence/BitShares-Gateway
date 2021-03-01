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

# BITSHARES GATEWAY MODULES
from utilities import create_access, chronicle


def verify_ltcbtc_account(account, comptroller):
    """
    check to see if the address is valid

    :param str(account): bitcoin address
    :param dict(comptroller): used to distinguish ltc vs btc network
    :return bool(): is this a valid address?
    """
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration ** 2)
        try:
            access = create_access(network)
            return bool(access.validateaddress(account)["isvalid"])
        except Exception as error:
            print(f"get_received_by {network} access failed {error.args}")
        iteration += 1


def get_block_number(network):
    """
    the current block height as an integer
    :param dict(comptroller): used to distinguish ltc vs btc network
    :return int(): current block number
    """
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration ** 2)
        try:
            access = create_access(network)
            return int(access.getblockcount())
        except Exception as error:
            print(f"get_block_count {network} access failed {error.args}")
        iteration += 1


def get_block(network, block_num):
    """
    extract litecoin or bitcoin block transactions given a block number
    """
    access = create_access(network)
    block_num = access.getblockcount()
    block_hash = access.getblockhash(block_num)
    block_data = access.getblock(block_hash)
    transactions = block_data["tx"]
    # print("chain_info", chain_info)
    # print("block_num", block_num)
    # print("block_hash", block_hash)
    # print("block_data", block_data)
    decoded_trxs = []
    for _, trx in enumerate(transactions):
        raw_trx = access.getrawtransaction(trx)
        decoded_trx = access.decoderawtransaction(raw_trx)
        # pprint(decoded_tx)

    decoded_trxs.append(decoded_trx)

    return decoded_trxs


def get_received_by(address, comptroller):
    """
    return the amount received by address as float with 8 decimal places

    :param str(address): bitcoin address
    :param dict(comptroller): used to distinguish ltc vs btc network
    :return float(): total received by this address
    """
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration ** 2)
        try:
            access = create_access(comptroller["network"])
            return float(precisely(float(access.getreceivedbyaddress(address, 2)), 8))
        except Exception as error:
            print(f"get_received_by {network} access failed {error.args}")
        iteration += 1
        

def apodize_block_data(comptroller, new_blocks):
    """
    build a parachain fragment of all new blocks

    :return dict(parachain) with int(block_num) keys
        and value dict() containing normalized transactions with keys:
        ["to", "from", "memo", "hash", "asset", "amount"]
    """
    chronicle(comptroller, "initilizing parachain")
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
