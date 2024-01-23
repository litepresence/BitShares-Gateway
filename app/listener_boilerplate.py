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
# Importing necessary modules

# STANDARD MODULES
import time
from pprint import pprint
from typing import Any, Dict

# BITSHARES GATEWAY MODULES
from address_allocator import unlock_address
from config import foreign_accounts, gateway_assets, parachain_params, timing
from ipc_utilities import chronicle, json_ipc
from issue_or_reserve import issue_or_reserve
from parachain_eosio import verify_eosio_account
from parachain_ltcbtc import verify_ltcbtc_account
from parachain_ripple import verify_ripple_account
from parachain_xyz import verify_xyz_account
from utilities import it, precisely, xterm


def verifier_specific(network: str) -> Any:
    """Return the verifier for this network."""
    dispatch = {
        "ltc": verify_ltcbtc_account,
        "btc": verify_ltcbtc_account,
        "xrp": verify_ripple_account,
        "eos": verify_eosio_account,
        "xyz": verify_xyz_account,
    }
    return dispatch[network]


def listener_boilerplate(comptroller: Dict[str, Any]) -> None:
    """
    For every block from initialized until detected:
    Check for a transaction to the gateway, issue or reserve UIA upon receipt of gateway transfer.

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
    # Localizing the comptroller values
    memo = comptroller["memo"]
    nonce = comptroller["nonce"]
    network = comptroller["network"]
    account_idx = comptroller["account_idx"]
    issuer_action = comptroller["issuer_action"]
    # Localizing configuration for this network
    uia = gateway_assets()[network]["asset_name"]
    uia_id = gateway_assets()[network]["asset_id"]
    gateway_address = foreign_accounts()[network][account_idx]["public"]
    # Apply appropriate logic for issue, reserve, and unit testing
    # to tx direction, client_address, withdrawal_amount, and listening_to
    if issuer_action == "issue":
        # Issuing uia to cover deposit of foreign tokens
        # Monitor the gateway address
        # Awaiting unknown amount of incoming funds
        direction = "incoming deposit"
        client_address = None  # not applicable to deposits
        withdrawal_amount = None  # not applicable to deposits
        listening_to = gateway_address
    elif issuer_action == "reserve":
        # Reserving uia to cover withdrawal of foreign tokens
        # Monitor the client address
        # Awaiting the specific amount that was withdrawn
        direction = "outgoing withdrawal"
        client_address = comptroller["client_address"]
        withdrawal_amount = comptroller["withdrawal_amount"]
        listening_to = client_address
    else:
        # For unit testing issuer action is None
        # Monitor the zero idx foreign account for an unknown amount
        direction = None
        client_address = None
        withdrawal_amount = None
        listening_to = foreign_accounts()[network][0]["public"]
    # Initialize the block counter
    parachain = json_ipc(f"parachain_{network}.txt")
    parachain_keys = [int(x) for x in list(parachain.keys())]
    start_block_num = max(parachain_keys)
    checked_blocks = [start_block_num]
    # Update the audit trail
    comptroller["uia"] = uia
    comptroller["uia_id"] = uia_id
    comptroller["complete"] = False  # signal to break the while loop
    comptroller["direction"] = direction
    comptroller["listening_to"] = listening_to
    comptroller["client_address"] = client_address
    comptroller["gateway_address"] = gateway_address
    comptroller["start_block_num"] = start_block_num
    comptroller["withdrawal_amount"] = withdrawal_amount
    print("Start Block:", start_block_num, "NONCE", nonce, "LISTENING TO", listening_to)
    # Iterate through irreversible block data
    while 1:
        # Limit parachain read frequency
        time.sleep(parachain_params()[network]["pause"])
        # if issue/reserve has signaled to break the while loop
        if comptroller["complete"]:
            break
        # After timeout, break the while loop; if deposit, release the address
        elapsed = time.time() - start
        if elapsed > timing()[network]["timeout"]:
            print(it("red", f"NONCE {memo} {network.upper()} GATEWAY TIMEOUT"))
            if issuer_action == "issue":
                if network not in ["eos", "xrp"]:
                    unlock_address(network, account_idx, timing()[network]["pause"])
            msg = "listener timeout"
            chronicle(comptroller, msg)
            break
        # Otherwise, get the latest block number from the parachain
        parachain = json_ipc(f"parachain_{network}.txt")
        parachain_keys = [int(x) for x in list(parachain.keys())]
        current_block_num = max(parachain_keys)
        # Get the maximum block number we have checked
        max_checked_block = max(checked_blocks)
        # If there are any new blocks
        if current_block_num > max_checked_block + 1:
            # announce every block from last checked till now
            new_blocks = [*range(max_checked_block + 1, current_block_num)]
            # announce the latest blocks
            str_also = ""
            if len(new_blocks) > 1:
                min_new = str(min(new_blocks[:-1]))
                max_new = str(max(new_blocks[:-1]))
                str_also = "[" + min_new + " ... " + max_new + "]"
            print(
                it(color, comptroller["event_id"]),
                it(color, f"{memo} {nonce}"),
                it("yellow", f"{network}".upper()),
                it(color, "BLOCK"),
                it("yellow", max(new_blocks)),
                it(color, time.ctime()[11:19]),
                it(color, "GATE"),
                it("yellow", account_idx),
                it(color, str_also),
            )
            # With a new cache of blocks, check every block from last check till now
            for block_num in new_blocks:
                if block_num not in checked_blocks:
                    checked_blocks.append(block_num)
                try:
                    transfers = parachain[str(block_num)]
                except Exception:
                    transfers = []
                    msg = f"missing block data for {block_num}"
                    # FIXME fallback mechanism?
                    chronicle(comptroller, msg)
                for transfer in transfers:
                    # Extract the transaction data
                    trx_to = transfer["to"]
                    trx_hash = transfer["hash"]
                    trx_memo = transfer["memo"]
                    trx_from = transfer["from"]
                    trx_amount = transfer["amount"]
                    # Test the memo on pertinent network deposits
                    memo_check = True
                    if issuer_action == "issue" and network in ["eos", "xrp"]:
                        memo_check = bool(memo == trx_memo)
                    # Update the audit trail
                    comptroller["trx_to"] = trx_to
                    comptroller["elapsed"] = elapsed
                    comptroller["trx_hash"] = trx_hash
                    comptroller["trx_memo"] = trx_memo
                    comptroller["trx_from"] = trx_from
                    comptroller["trx_block"] = block_num
                    comptroller["str_amount"] = precisely(trx_amount, 8)
                    comptroller["trx_amount"] = trx_amount
                    comptroller["memo_check"] = memo_check
                    comptroller["current_block"] = current_block_num
                    # Issue or reserve and return the modified audit trail
                    comptroller = issue_or_reserve(comptroller)


def main() -> None:
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
    choice = int(input("\nWhich listener would you like to demo?\n"))
    network = dispatch[choice]
    # Build a test comptroller dictionary
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
    verifier = verifier_specific(network)
    # Verify a True address
    account = foreign_accounts()[network][0]["public"]
    print(
        f"verify_{network}_account(",
        account,
        ")",
        verifier(account, comptroller),
    )
    # Verify a False address
    print(
        f"verify_{network}_account(",
        "test fail )",
        verifier("test fail", comptroller),
    )
    print(f"\n{network.upper()} Transaction Listener\n============================")
    # Unit test the listener
    listener_boilerplate(comptroller)


if __name__ == "__main__":
    main()
