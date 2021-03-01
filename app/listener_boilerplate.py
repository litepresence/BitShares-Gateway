r"""
listener_boilerplate.py
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

Standarized Transaction Listener Boilerplate for All Blockchains

called by process_withdrawals.py and process_deposits.py
    initializes a foreign chain listening while loop
    imports chain specific block processing to await for a specific transfer
    finalizes the gateway transaction by issuing or reserving UIA
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-locals

# STANDARD PYTHON MODULES
import time
from pprint import pprint

# BITSHARES GATEWAY MODULES
from address_allocator import unlock_address
from config import foreign_accounts, gateway_assets, timing
from issue_or_reserve import issue_or_reserve
from parachain_eosio import get_block_number as get_eosio_block_number
from parachain_eosio import verify_eosio_account
from parachain_ltcbtc import get_block_number as get_ltcbtc_block_number
from parachain_ltcbtc import verify_ltcbtc_account
from parachain_ripple import get_block_number as get_ripple_block_number
from parachain_ripple import verify_ripple_account
from utilities import chronicle, encode_memo, it, json_ipc, precisely, xterm


def get_block_number(comptroller):
    """
    return the current block height as an integer for the appropriate network
    """
    network = comptroller["network"]
    dispatch = {
        "ltc": get_ltcbtc_block_number,
        "btc": get_ltcbtc_block_number,
        "eos": get_eosio_block_number,
        "xrp": get_ripple_block_number,
    }
    return dispatch[network](comptroller)


def verifier_specific(comptroller):
    """
    return the verifier for this network
    """
    network = comptroller["network"]
    dispatch = {
        "ltc": verify_ltcbtc_account,
        "btc": verify_ltcbtc_account,
        "xrp": verify_ripple_account,
        "eos": verify_eosio_account,
    }
    return dispatch[network]


def listener_boilerplate(comptroller):
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

    :return None
    """
    color = xterm()
    start = time.time()
    # localize the comptroller values
    nonce = comptroller["nonce"]
    network = comptroller["network"]
    client_id = comptroller["client_id"]
    account_idx = comptroller["account_idx"]
    issuer_action = comptroller["issuer_action"]
    # localize configuration for this network
    uia = gateway_assets()[network]["asset_name"]
    uia_id = gateway_assets()[network]["asset_id"]
    gateway_address = foreign_accounts()[network][account_idx]["public"]
    # apply appropriate logic for issue, reserve, and unit testing
    # to tx direction, client_address, withdrawal_amount, and listening_to
    if issuer_action == "issue":
        # issuing uia to cover deposit of foreign tokens
        # monitor the gateway address
        # awaiting unknown amount of incoming funds
        direction = "INCOMING"
        client_address = None  # not applicable to deposits
        withdrawal_amount = None  # not applicable to deposits
        listening_to = gateway_address
    elif issuer_action == "reserve":
        # reserving uia to cover withdrawal of foreign tokens
        # monitor the client address
        # awaiting the specific amount that was withdrawn
        direction = "OUTGOING"
        client_address = comptroller["client_address"]
        withdrawal_amount = comptroller["withdrawal_amount"]
        listening_to = client_address
    else:
        # for unit testing issuer action is None
        # monitor the zero idx foreign account for an unknown amount
        direction = None
        client_address = None
        withdrawal_amount = None
        listening_to = foreign_accounts()[network][0]["public"]
    # initialize the block counter
    start_block_num = get_block_number(comptroller)
    checked_blocks = [start_block_num]
    print("Start Block:", start_block_num, "\n")
    # update the audit trail
    comptroller["uia"] = uia
    comptroller["uia_id"] = uia_id
    comptroller["complete"] = False  # signal to break the while loop
    comptroller["direction"] = direction
    comptroller["listening_to"] = listening_to
    comptroller["client_address"] = client_address
    comptroller["gateway_address"] = gateway_address
    comptroller["start_block_num"] = start_block_num
    comptroller["withdrawal_amount"] = withdrawal_amount
    print("NONCE", nonce, "LISTENING TO", listening_to)
    # iterate through irreversible block data
    while 1:
        wait = {
            "ltc": 60,
            "btc": 60,
            "xrp": 3,
            "eos": 6,
        }
        time.sleep(wait[network])
        # if issue/reserve has signaled to break the while loop
        if comptroller["complete"]:
            break
        # after timeout, break the while loop; if deposit: release the address
        elapsed = time.time() - start
        if elapsed > timing()[network]["timeout"]:
            print(it("red", f"NONCE {nonce} {network.upper()} GATEWAY TIMEOUT"))
            if issuer_action == "issue":
                unlock_address(network, account_idx, timing()[network]["pause"])
            msg = "listener timeout"
            chronicle(comptroller, msg)
            break
        # otherwise, get the latest block number from the parachain
        parachain = json_ipc(f"parachain_{network}.txt")
        parachain_keys = [int(x) for x in list(parachain.keys())]
        current_block_num = max(parachain_keys)
        # get the maximum block number we have checked
        max_checked_block = max(checked_blocks)
        # if there are any new blocks
        if current_block_num > max_checked_block + 1:
            # announce every block from last checked till now
            new_blocks = [*range(max_checked_block + 1, current_block_num)]
            # announce the latest blocks
            str_also = ""
            if len(new_blocks) > 1:
                min_new = str(min(new_blocks[:-1]))
                max_new = str(max(new_blocks[:-1]))
                str_also = "ALSO: [" + min_new + " ... " + max_new + "]"
            print(
                it(color, f"NONCE {nonce}"),
                it("yellow", f"{network}".upper()),
                it(color, "BLOCK"),
                it("yellow", max(new_blocks)),
                it(color, time.ctime()[11:19]),
                it(color, "GATE"),
                it("yellow", account_idx),
                it(color, str_also),
            )
            # update the comptroller with a list of the latest blocks
            # hash the client id and nonce to be checked vs the transaction memo
            memo = encode_memo(client_id, nonce)
            # with new cache of blocks, check every block from last check till now
            for block_num in new_blocks:
                if block_num not in checked_blocks:
                    checked_blocks.append(block_num)
                transfers = []
                try:
                    transfers = parachain[str(block_num)]
                except:
                    msg = f"missing block data for {block_num}"
                    chronicle(comptroller, msg)
                for transfer in transfers:
                    # extract the transaction data
                    trx_to = transfer["to"]
                    trx_hash = transfer["hash"]
                    trx_memo = transfer["memo"]
                    trx_from = transfer["from"]
                    trx_amount = transfer["amount"]
                    # update the audit trail
                    comptroller["trx_to"] = trx_to
                    comptroller["elapsed"] = elapsed
                    comptroller["trx_hash"] = trx_hash
                    comptroller["trx_memo"] = trx_memo
                    comptroller["trx_from"] = trx_from
                    comptroller["trx_block"] = block_num
                    comptroller["str_amount"] = precisely(trx_amount, 8)
                    comptroller["trx_amount"] = trx_amount
                    comptroller["memo_check"] = bool(memo == trx_memo)
                    comptroller["current_block"] = current_block_num
                    # issue or reserve and return the modified audit trail
                    comptroller = issue_or_reserve(comptroller)


def main():
    """
    UNIT TEST listener demonstration
    """
    dispatch = {
        1: "ltc",
        2: "btc",
        3: "xrp",
        4: "eos",
    }
    print("\033c\n")
    print(main.__doc__)
    print(time.ctime(), "\n")
    for key, val in dispatch.items():
        print("   ", key, ":", val)
    choice = int(input("\nwhich listener would you like to demo?\n"))
    network = dispatch[choice]
    # build a test comptroller dictionary
    comptroller = {
        "issuer_action": None,
        "account_idx": 0,
        "client_id": "1.2.xxx",
        "network": network,
        "nonce": int(time.time() * 1000),
        "uia": "test",
        "new_blocks": [],
        "checked_blocks": [1],
    }
    print("\nnetwork", network.upper(), "\n\n", "comptroller\n===============")
    pprint(comptroller)
    print(f"\n{network.upper()} Account Verification\n============================")
    verifier = verifier_specific(comptroller)
    # verify a True address
    account = foreign_accounts()[network][0]["public"]
    print(
        f"verify_{network}_account(", account, ")", verifier(account, comptroller),
    )
    # verify a False address
    print(
        f"verify_{network}_account(", "test fail )", verifier("test fail", comptroller),
    )
    print(f"\n{network.upper()} Transaction Listener\n============================")
    # unit test the listener
    listener_boilerplate(comptroller)


if __name__ == "__main__":

    main()
