r"""
create_ltcbtc_accounts.py
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
"""

# BITSHARES GATEWAY MODULES
from nodes import bitcoin_node, litecoin_node

# THIRD PARTY MODULES
from signing.bitcoin.bitcoinrpc.authproxy import AuthServiceProxy


def create_ltcbtc_accounts(number: int, network: str) -> None:
    """
    Create Litecoin (LTC) or Bitcoin (BTC) accounts using the wallet specified in nodes.py.

    :param number: The number of accounts to create.
    :param network: The network for which accounts should be created ("ltc" or "btc").

    :return: None
    """

    for i in range(number):
        if network == "ltc":
            access = AuthServiceProxy(
                litecoin_node()[0] + "/wallet/" + litecoin_node()[1]
            )
            public = access.getaddressinfo(access.getnewaddress())["embedded"][
                "address"
            ]
            private = access.dumpprivkey(public)
            print("LTC", i + 1)
            print('"public":', '"' + public + '",')
            print('"private":', '"' + private + '",', "\n")

        elif network == "btc":
            access = AuthServiceProxy(
                bitcoin_node()[0] + "/wallet/" + bitcoin_node()[1]
            )
            public = access.getnewaddress("", "legacy")
            private = access.dumpprivkey(public)
            print("BTC", i + 1)
            print('"public":', '"' + public + '",')
            print('"private":', '"' + private + '",', "\n")


def main() -> None:
    """
    Offer the user a choice to create a specified number of Litecoin (LTC)
    or Bitcoin (BTC) public/private key pairs.

    :return: None
    """

    dispatch = {
        1: "ltc",
        2: "btc",
    }
    print("create litecoin and bitcoin public/private key pairs\n\n")
    for key, val in dispatch.items():
        print("    ", key, ":", val)
    choice = int(input("\nchoice 1 or 2 ?\n\n"))
    number = int(input("how many accounts?\n\n"))
    network = dispatch[choice]
    create_ltcbtc_accounts(number, network)


if __name__ == "__main__":
    main()
