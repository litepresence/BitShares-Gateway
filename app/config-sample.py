r"""
config-sample.py
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

Sample configuration settings
"""

# SAMPLE config file - copy this file as config.py and fill in or edit
# relevant information.

# FIXME don't keep private keys in a config file:
# should build encrypted "wallet", but this is outside of the scope of the task
# maybe this file should be stored on a thumb drive?
# perhaps security/obscurity is best addressed by the gateway admin!


def offerings():
    """
    initialize only the gateways listed in offerings
    """
    return ["eos", "xrp", "ltc", "btc"]


def processes():
    """
    select which processes to enable
    """
    return {
        "ingots": False,  # return fund to zero index account
        "deposits": True,  # api server for issuing uia
        "withdrawals": False,  # bitshares listener for returning and reserving uia
    }


def contact():
    """
    gateway admin support email
    """
    return "email@domain.com"


def server_config():
    """
    port number for the deposit server
    """
    return {
        "url": "192.168.0.3",  # note the actual host url will be displayed at startup
        "port": 4018,
        "route": "gateway",
    }


def logo():
    """
    enable/disable startup logo animation and audio
    disabling the animation will disable both
    """
    return {"animate": False, "audio": True}


def fees():
    """
    # FIXME enable flat fee and percent fee for gateway use in the listeners
    # FIXME announce fee schedule via deposit JSON
    # FIXME charge fees on withdrawals
    # FIXME create api endpoint for fee schedule
    """
    return {
        "eos": {  # eos has no flat tx fees; requires staking NET/CPU/RAM
            "tx": 0,  # EOS
            "flat": 0,  # EOS
            "percent": 0,  # percent
        },
        "xrp": {  # xrpl.org/transaction-cost.html
            "tx": 0.00001,  # XRP
            "flat": 0,  # XRP
            "percent": 0,  # percent
        },
        "ltc": {  # bitinfocharts.com/comparison/litecoin-transactionfees.html
            "tx": 0.00019,  # LTC
            "flat": 0,  # LTC
            "percent": 0,  # percent
        },
        "btc": {  # bitinfocharts.com/comparison/bitcoin-transactionfees.html
            "tx": 0.00037,  # BTC
            "flat": 0,  # BTC
            "percent": 0,  # percent
        },
        "ada": {"tx": 0, "flat": 0, "percent": 0,},  # ADA  # ADA  # percent
        "eth": {"tx": 0, "flat": 0, "percent": 0,},  # ETH  # ETH  # percent
    }


def timing():
    """
    # FIXME periodically fine tune gateway timeouts in seconds
    """
    return {
        "eos": {
            "pause": 600,  # keep address out of use after timeout
            "timeout": 1800,  # listener timeout
            "request": 5,  # api request timeout
        },
        "xrp": {"pause": 600, "timeout": 1800, "request": 5,},
        "ltc": {"pause": 900, "timeout": 3600, "request": 5,},
        "btc": {"pause": 900, "timeout": 7200, "request": 5,},
        "ingot": 1800,
    }


def nil():
    """
    # nil amounts were set to "about $10" Feb 1, 2021
    # FIXME integrate nil amounts in both deposit server and withdrawal listener
    # FIXME suggest periodically fine tuning nil amounts to $10 value
    # FIXME should we automate via 3rd party api what $10 value is?
    """
    return {
        "eos": 3,
        "xrp": 27,
        "ltc": 0.065,
        "btc": 0.00027,
    }


def max_unspent():
    """
    # if there too many addresses with dust, consolidate an ingot
    """
    return {
        "eos": None,  # not applicable / utxo only
        "xrp": None,  # not applicable / utxo only
        "ltc": 10,
        "btc": 10,
    }


def issuing_chain():
    """
    core token and chain id
    # bitsharesbase/chains.py
    """
    return {
        "prefix": "BTS",  # core token
        "id": "4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8",
    }
    # Other chains:
    # BitShares public testnet:
    # {
    #   "prefix": "TEST",
    #   "id": "39f5e2ede1f8bc1a3a54a7914414e3779e33193f1f5693510e73cb7a87617447",
    # }


def gateway_assets():
    """
    # gateway user issued assets
    """
    return {
        "eos": {
            "asset_id": "",  # "1.3.x"
            "dynamic_id": "",  # "2.3.x" same x as asset_id
            "asset_name": "",  # all caps
            "asset_precision": 0,  # int()
            "issuer_id": "",  # "1.2.x"
            "issuer_public": "",  # bitshares account name
            "issuer_private": "",  # wif
        },
        "xrp": {
            "asset_id": "",  # "1.3.x"
            "dynamic_id": "",  # "2.3.x" same x as asset_id
            "asset_name": "",  # all caps
            "asset_precision": 0,  # int()
            "issuer_id": "",  # "1.2.x"
            "issuer_public": "",  # bitshares account name
            "issuer_private": "",  # wif
        },
        "btc": {
            "asset_id": "",  # "1.3.x"
            "dynamic_id": "",  # "2.3.x" same x as asset_id
            "asset_name": "",  # all caps
            "asset_precision": 0,  # int()
            "issuer_id": "",  # "1.2.x"
            "issuer_public": "",  # bitshares account name
            "issuer_private": "",  # wif
        },
        "ltc": {
            "asset_id": "",  # "1.3.x"
            "dynamic_id": "",  # "2.3.x" same x as asset_id
            "asset_name": "",  # all caps
            "asset_precision": 0,  # int()
            "issuer_id": "",  # "1.2.x"
            "issuer_public": "",  # bitshares account name
            "issuer_private": "",  # wif
        },
        "ada": {
            "asset_id": "",  # "1.3.x"
            "dynamic_id": "",  # "2.3.x" same x as asset_id
            "asset_name": "",  # all caps
            "asset_precision": 0,  # int()
            "issuer_id": "",  # "1.2.x"
            "issuer_public": "",  # bitshares account name
            "issuer_private": "",  # wif
        },
        "eth": {
            "asset_id": "",  # "1.3.x"
            "dynamic_id": "",  # "2.3.x" same x as asset_id
            "asset_name": "",  # all caps
            "asset_precision": 0,  # int()
            "issuer_id": "",  # "1.2.x"
            "issuer_public": "",  # bitshares account name
            "issuer_private": "",  # wif
        },
    }


def foreign_accounts():
    """
    foreign chain public and private keys
    """
    return {
        # eosio account name and wif
        # Note: eosio list should include only ONE account; multiplexing
        # is via memo nonce.
        "eos": [{"public": "", "private": "",},],  # eosio account name  # wif
        # List of Ripple foreign chain gateway accounts, min 2
        "xrp": [
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            # etc.
        ],
        # List of Bitcoin foreign chain gateway accounts, min 2
        # Here use "WIF compressed" and "Address 1 compressed"
        "btc": [
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            # etc.
        ],
        # List of Litcoin foreign chain gateway accounts, min 2
        # Here use "WIF compressed" and "Address 1 compressed"
        "ltc": [
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            # etc.
        ],
        "ada": [
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            # etc.
        ],
        "eth": [
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            {"public": "", "private": "",},
            # etc.
        ],
    }


def test_accounts():
    """
    test client account is used only in unit tests
    """
    return {
        "bts": {
            "id": "",  # bitshares account id
            "public": "",  # bitshares account name
            "private": "",  # wif
        },
        "eos": {"public": "", "private": "",},  # eosio account name  # wif
        "xrp": {"public": "", "private": "",},
        "ltc": {"public": "", "private": "",},  # address compressed / wif compressed
        "btc": {"public": "", "private": "",},  # address compressed / wif compressed
        "ada": {"public": "", "private": "",},
        "eth": {"public": "", "private": "",},
    }
