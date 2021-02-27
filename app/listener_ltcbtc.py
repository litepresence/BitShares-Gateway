r"""
listener_bitcoin.py
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

Litecoin and Bitcoin Received by Address Listener

triggers:

    issue UIA upon deposited foreign coin
    reserve UIA upon confirmed withdrawal
"""

# FIXME enable flat fee and percent fee for gateway use

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-locals, too-many-nested-blocks, bare-except, broad-except
# pylint: disable=too-many-function-args, too-many-branches, too-many-statements

# STANDARD PYTHON MODULES
import time

# BITSHARES GATEWAY MODULES
from config import foreign_accounts
from issue_or_reserve import issue_or_reserve
from utilities import create_access, precisely


def get_block_number(comptroller):
    """
    the current block height as an integer

    :param dict(comptroller): used to distinguish ltc vs btc network
    :return int(): current block number
    """
    network = comptroller["network"]
    iteration = 0
    while True:
        # increment the delay between attempts exponentially
        time.sleep(0.02 * iteration ** 2)
        try:
            access = create_access(comptroller["network"])
            return int(access.getblockcount())
        except Exception as error:
            print(f"get_block_count {network} access failed {error.args}")
        iteration += 1


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


def listener_ltcbtc(comptroller):
    """
    tare the "received by" amount of the address we're watching
    for every block from initialized until detected
        check if received by amount has increased since tare
        issue or reserve uia upon receipt of gateway transfer

    :dict(comproller) contains full audit trail and these pertinent keys:
      :key int(account_idx): from gateway_state.py
      :key str(issuer_action): reserve, issue, or None in unit test case
      :key str(client_id): ie. 1.2.X
      :key int(nonce): the millesecond label for this listening event
      :key list(new_blocks) initially empty, thereafter any unsearched block nums
      :key list(checked_blocks) initially start block num, thereafter all checked
      :key float(tare) starting get_received_by for this address / nonce

    for reserving withdrawals two additional comptroller keys are available:
      :key float(withdrawal_amount):
      :key str(client_address):

    :calls: issue_or_reserve() after updating the comptroller dict

    :return dict(comtroller): updated audit dictionary
    """
    # localize the audit trail
    tare = comptroller["tare"]
    network = comptroller["network"]
    new_blocks = comptroller["new_blocks"]
    listening_to = comptroller["listening_to"]
    issuer_action = comptroller["issuer_action"]
    checked_blocks = comptroller["checked_blocks"]
    # check every block from last check till now
    for block_num in new_blocks:
        comptroller["block_num"] = block_num
        # append this block number to the list of checked numbers
        if block_num not in checked_blocks:
            checked_blocks.append(block_num)
        # ensure no duplicates in the checked list
        checked_blocks = sorted(list(set(checked_blocks)))
    # has the amount received by the address being monitored changed?
    comptroller["received_by"] = get_received_by(listening_to, comptroller)
    rec_amount = comptroller["received_by"] - tare
    str_amount = comptroller["str_amount"] = precisely(rec_amount, 8)
    trx_amount = comptroller["trx_amount"] = float(comptroller["str_amount"])
    trx_from = foreign_accounts()[network][0]["public"]
    if issuer_action == "reserve":
        trx_from = "unknown"
    memo_check = True  # not applicable to ltc or btc
    # if funds rec'd and unit testing update the tare, and print the comptroller
    if trx_amount > 0 and issuer_action is None:
        tare = comptroller["received_by"]
    # update the audit trail
    comptroller["tare"] = tare  # return new tare to unit test!
    comptroller["trx_from"] = trx_from
    comptroller["trx_to"] = listening_to
    comptroller["str_amount"] = str_amount
    comptroller["trx_amount"] = trx_amount
    comptroller["memo_check"] = memo_check
    comptroller["checked_blocks"] = checked_blocks  # return checked!
    # issue or reserve and return the modified audit trail
    comptroller = issue_or_reserve(comptroller)
    return comptroller
