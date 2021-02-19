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

# THIRD PARTY MODULES
from bitcoinrpc.authproxy import AuthServiceProxy

# BITSHARES GATEWAY MODULES
from nodes import bitcoin_node, litecoin_node


def create_ltcbtc_accounts(number, network):
    """
    create a litecoin or bitcoin account using the wallet in nodes.py
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


def main():
    """
    offer user choice to create any amount of ltc or btc public/private key pairs
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
