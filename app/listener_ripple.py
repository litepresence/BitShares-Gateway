r"""
listener_ripple.py
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

Ripple Ledger Ops Listener

triggers:

    issue UIA upon deposited foreign coin
    reserve UIA upon confirmed withdrawal
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
from issue_or_reserve import issue_or_reserve
from nodes import ripple_node
from utilities import chronicle, precisely


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


def listener_ripple(comptroller):
    """
    for every block from initialized until detected
        check for transaction to the gateway
            issue or reserve uia upon receipt of gateway transfer

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
    new_blocks = comptroller["new_blocks"]
    checked_blocks = comptroller["checked_blocks"]
    # check every block from last check till now
    for block_num in new_blocks:
        comptroller["block_num"] = block_num
        # append this block number to the list of checked numbers
        if block_num not in checked_blocks:
            checked_blocks.append(block_num)
        # ensure no duplicates in the checked list
        checked_blocks = sorted(list(set(checked_blocks)))
        # get each new validated ledger
        transactions = get_ledger(block_num)
        # iterate through all transactions in the list of transactions
        for trx in transactions:
            if not isinstance(trx["Amount"], dict):
                # localize data from the transaction
                trx_amount = int(trx["Amount"]) / 10 ** 6  # convert drops to xrp
                trx_from = trx["Account"]
                trx_to = trx["Destination"]
                comptroller["trx"] = trx
                memo_check = True  # not applicable to xrp
                str_amount = comptroller["str_amount"] = precisely(trx_amount, 8)
                # update the audit trail
                comptroller["trx_to"] = trx_to
                comptroller["trx_from"] = trx_from
                comptroller["str_amount"] = str_amount
                comptroller["trx_amount"] = trx_amount
                comptroller["memo_check"] = memo_check
                comptroller["checked_blocks"] = checked_blocks  # return checked!
                # issue or reserve and return the modified audit trail
                comptroller = issue_or_reserve(comptroller)
    return comptroller
