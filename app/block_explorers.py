r"""
block_explorers.py
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

Open 3rd party block explorers in web browser for all pertinent accounts
"""


from webbrowser import open as browse

# BITSHARES GATEWAY MODULES
from config import foreign_accounts, test_accounts

# GLOBAL CONSTANTS
BITSHARES_EXPLORER = "https://blocksights.info/#/accounts/"
RIPPLE_EXPLORER = "http://www.bithomp.com/explorer/"
EOSIO_EXPLORER = "http://www.eosflare.io/account/"


def block_explorers():
    """
    use system browser to open block explorers
    """
    print("opening block explorers for client test accounts...")
    for coin, account in test_accounts().items():
        if coin == "bts":
            browse(BITSHARES_EXPLORER + account["public"], 1)  # 1 = open a new window
        elif coin == "xrp":
            browse(RIPPLE_EXPLORER + account["public"], 2)  # 2 = open a new tab
        elif coin == "eos":
            browse(EOSIO_EXPLORER + account["public"], 2)
    print("opening block explorers for ripple gateway deposit accounts...")
    for idx, account in enumerate(foreign_accounts()["xrp"]):
        browse(RIPPLE_EXPLORER + account["public"], int(bool(idx)) + 1)
    print("opening block explorers for eosio gateway deposit accounts...")
    for idx, account in enumerate(foreign_accounts()["eos"]):
        browse(EOSIO_EXPLORER + account["public"], int(bool(idx)) + 1)
    print("opening block explorers for bitshares asset issuer accounts...")
    browse(BITSHARES_EXPLORER + foreign_accounts()["uia"]["eos"]["issuer_public"], 1)
    browse(BITSHARES_EXPLORER + foreign_accounts()["uia"]["xrp"]["issuer_public"], 2)
    print("done")


if __name__ == "__main__":
    block_explorers()
