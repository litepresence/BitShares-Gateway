r"""
process_ingots.py
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

ensure all inbound funds are transfered to the zero index outbound account
"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-nested-blocks

# STANDARD MODULES
from typing import Any, Dict

# GATEWAY MODULES
from config import foreign_accounts, max_unspent, nil, offerings, timing
from ipc_utilities import chronicle
from parachain_ltcbtc import get_block_number as get_ltcbtc_block_number
from parachain_ripple import get_block_number as get_xrp_block_number
from signing_eosio import eos_balance
from signing_ltcbtc import ltcbtc_balance, ltcbtc_balances, ltcbtc_transfer
from signing_ripple import xrp_balance, xrp_transfer
from utilities import it, line_number, timestamp
from watchdog import watchdog_sleep


def ingot_casting(comptroller: Dict[str, Any]) -> None:
    """
    In a background process, check incoming accounts & move funds to outbound accounts.

    :param comptroller: The comptroller dictionary.
    """
    print(it("red", "INITIALIZING INGOT CASTING\n"))

    while 1:
        for network in offerings():
            comptroller["network"] = network
            order = {}

            # Gateways with a single incoming account
            if network in ["eos", "xyz"]:
                pass  # NOTE: no ingot casting

            # Gateways with traditional account balance accounting
            # recycle gateway incoming transfers to the outbound account
            # allow this loop to be used by multiple coins
            elif network in ["xrp"]:
                # XRP specific parameters
                if network == "xrp":
                    get_balance = xrp_balance
                    transfer = xrp_transfer
                    block = get_xrp_block_number({"ingot_process": None})

                for idx, gateway in enumerate(foreign_accounts()[network]):
                    if bool(idx):  # exclude the zero index
                        balance = get_balance(gateway["public"], comptroller)
                        if balance > nil()[network]:
                            timestamp()
                            line_number()
                            print(it("red", f"{network.upper()} RECYCLER"))
                            print(gateway["public"], balance, "\n")

                            # Finalize the order
                            order["private"] = gateway["private"]
                            order["public"] = gateway["public"]
                            # Always send back to the zero index address
                            order["to"] = foreign_accounts()[network][0]["public"]
                            order["quantity"] = balance

                            if network == "xrp":  # Must maintain min balance for xrp
                                order["quantity"] -= 20.1

                            # Final quantity check
                            if order["quantity"] > nil()[network]:
                                # Serialize, sign, and broadcast
                                ingot = transfer(order, comptroller)
                                msg = (
                                    "consolidating an ingot on",
                                    network,
                                    block,
                                    ingot,
                                )
                                chronicle(comptroller, msg)
                                print(msg)

            # Gateways with unspent transaction output (UTXO) accounting
            # FIXME can we better game the utxo fee schedule?
            elif network in ["btc", "ltc"]:
                comptroller["network"] = network
                if len(ltcbtc_balances(None, comptroller)) > max_unspent()[network]:
                    # Get the block number
                    block_num = get_ltcbtc_block_number(comptroller)
                    # Consolidate balances into a single ingot
                    order = {
                        "to": foreign_accounts()[network][0]["public"],
                        "quantity": ltcbtc_balance(None, comptroller),
                    }
                    ingot = ltcbtc_transfer(order, comptroller, pay_fee=True)
                    msg = ("consolidating an ingot on", network, block_num, ingot)
                    chronicle(comptroller, msg)
                    print(msg)

        # Check in with the main process and limit ingot casting frequency
        watchdog_sleep("ingots", int(timing()["ingots"]))


def gateway_balances(network=None) -> None:
    """
    Print gateway balances.

    :param network: The network to print balances for, defaults to None.
    """
    comptroller = {}
    if network in ["xrp", None]:
        for gateway in foreign_accounts()["xrp"]:
            print(
                "Gateway XRP balance for",
                gateway["public"].rjust(40),
                xrp_balance(gateway["public"], comptroller),
            )
    if network in ["eos", None]:
        print(
            "Gateway EOS balance for",
            foreign_accounts()["eos"][0]["public"].rjust(40),
            eos_balance(foreign_accounts()["eos"][0]["public"], comptroller),
        )
    if network in ["btc", None]:
        comptroller["network"] = "btc"
        balance = ltcbtc_balance(None, comptroller)
        balances = ltcbtc_balances(None, comptroller)
        print("Gateway BTC balance\n", balance)
        print("Unspent Balances\n", balances)
    if network in ["ltc", None]:
        comptroller["network"] = "ltc"
        balance = ltcbtc_balance(None, comptroller)
        balances = ltcbtc_balances(None, comptroller)
        print("Gateway LTC balance\n", balance)
        print("Unspent Balances\n", balances)


def unit_test_ingots() -> None:
    """
    Quick test of the definitions above.
    """
    gateway_balances()
    input("press Enter to continue")
    gateway_balances()
    print("\n\nRECYCLING\n\n")
    comptroller = {"offerings": offerings()}
    ingot_casting(comptroller)
    gateway_balances()


if __name__ == "__main__":
    unit_test_ingots()
