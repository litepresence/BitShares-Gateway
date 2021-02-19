r"""
nodes-sample.py
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

public api endpoints

SECURITY ADVISORY: best to use a "private nodes" in production
"""

# SAMPLE nodes file - copy this file as nodes.py and fill in or edit
# to to reflect node slection for your specific use case.


def bitshares_nodes():
    """
    Bitshares websocket endpoints tested JULY 2021
    """
    # alternatively you can use single private node in the list
    # if using more than 1 node it is best to use at least 5
    # using multiple nodes will implement "metaNODE" statistical verification
    return ['wss://api.bts.mobi/wss', 'wss://api.iamredbar.com/ws', 'wss://newyork.bitshares.im/wss', 'wss://api.dex.trading/ws', 'wss://eu.nodes.bitshares.ws/ws', 'wss://public.xbts.io/ws', 'wss://node.xbts.io/ws', 'wss://cloud.xbts.io/ws', 'wss://nexus01.co.uk/ws', 'wss://node.market.rudex.org/ws', 'wss://api-bts.liondani.com/ws', 'wss://dex.iobanker.com/wss', 'wss://btsws.roelandp.nl/ws', 'wss://node1.deex.exchange/ws', 'wss://api.gbacenter.org/wss', 'wss://api.weaccount.cn/wss', 'wss://bts.open.icowallet.net/wss', 'wss://ws.gdex.top/ws', 'wss://bitshares.bts123.cc:15138/ws', 'wss://api.btsgo.net/ws', 'wss://singapore.bitshares.im/ws', 'wss://api.61bts.com/wss', 'wss://api.cnvote.vip:888/wss', 'wss://freedom.bts123.cc:15138/wss']

def eosio_node():
    """
    remote host access
    """
    # https://validate.eosnation.io/eos/reports/ << node lists
    # alternatively you can use single private node in list
    # if using more than 1 node it is best to use at least 5
    return "https://eos.greymass.com"

    # endpoints tested MAY 2021
    # "https://api.tokenika.io"
    # "https://api1.eosasia.one"
    # "https://eos.greymass.com"
    # "https://api.eosdetroit.io"  Failed FEB 2021
    # "https://bp.cryptolions.io"
    # "https://mainnet.eoscannon.io"
    # "https://user-api.eoseoul.io"
    # "https://node.eosflare.io"
    # "https://api.eossweden.se"
    # "https://eosbp.atticlab.net"
    # "https://node1.eosphere.io"
    # "https://node2.eosphere.io"


def bitcoin_node():
    """
    remote host access
    """
    user = "myrpc01"
    auth = "password01"
    host = "127.0.0.1"
    port = "18332"  # usually 8332 mainnet / 18332 testnet
    wallet = "test_wallet_1"

    return (f"http://{user}:{auth}@{host}:{port}", wallet) # NOTE tuple


def litecoin_node():
    """
    remote host access
    """
    user = "myrpc01"
    auth = "password01"
    host = "127.0.0.1"
    port = "19332"  # usually 9333 mainnet / 19333 testnet
    wallet = "test_wallet_2"

    return (f"http://{user}:{auth}@{host}:{port}", wallet) # NOTE tuple


def ripple_node():
    """
    remote host access
    """
    return "https://s1.ripple.com:51234/"


def unit_test_nodes():
    """
    print the list of nodes in use by the Gateway
    """
    print("eosio node\n", eosio_node(), "\n\n")
    print("ripple node\n", ripple_node(), "\n\n")
    print("bitcoin node\n", bitcoin_node(), "\n\n")
    print("litecoin node\n", litecoin_node(), "\n\n")
    print("bitshares nodes\n", bitshares_nodes(), "\n\n")


if __name__ == "__main__":

    unit_test_nodes()
