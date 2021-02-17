"""
create_bitcoin_accounts.py
╔══════════════════════════╗
║ ╔═╗┬─┐┌─┐┌─┐┬ ┬┌─┐┌┐┌┌─┐ ║
║ ║ ╦├┬┘├─┤├─┘├─┤├┤ │││├┤  ║
║ ╚═╝┴└─┴ ┴┴  ┴ ┴└─┘┘└┘└─┘ ║
║ ╔═╗┬ ┬┌┬┐┬ ┬┌─┐┌┐┌       ║
║ ╠═╝└┬┘ │ ├─┤│ ││││       ║
║ ╩   ┴  ┴ ┴ ┴└─┘┘└┘       ║
║ ╔═╗┌─┐┌┬┐┌─┐┬ ┬┌─┐┬ ┬    ║
║ ║ ╦├─┤ │ ├┤ │││├─┤└┬┘    ║
║ ╚═╝┴ ┴ ┴ └─┘└┴┘┴ ┴ ┴     ║
╚══════════════════════════╝

WTFPL litepresence.com Jan 2021

Create and Authenticate Bitcoin Key Pairs

- create n public/private key pairs on Bitcoin testnet or mainnet
- authenticate them to the wallet
- check address info to confirm

pip3 install bitcoinaddress
pip3 install python-bitcoinprc
"""

# pylint: disable=bad-continuation, bare-except

# STANDARD PYTHON MODULES
import time
from multiprocessing import Process
from pprint import pprint

# THIRD PARTY MODULES
from bitcoinaddress import Wallet

# GRAPHENE PYTHON GATEWAY MODULES
from config import foreign_accounts
from utilities import create_access


def create_n_accounts(amount, testnet):
    """
    create n private/public key pairs
    print list of dicts with keys private and public
    :param: int(amount) of key pairs to create
    :param: bool(testnet) testnet(True) or mainnet(False)
    """
    accounts = []
    for _ in range(amount):
        wallet = Wallet(testnet=testnet)
        keys = {
            "private": str(wallet)
            .split("Private Key WIF compressed: ")[1]
            .split("\n")[0]
            .strip(),
            "public": str(wallet)
            .split("Public Address 1 compressed: ")[1]
            .split("\n")[0]
            .strip(),
        }
        accounts.append(keys)
    print("\nCREATING", ("TESTNET" if testnet else "MAINNET"), "ADDRESSES...\n")
    pprint(accounts)
    print(
        "\nBefore this script can authenticate these to the wallet,"
        + "\nmanually add this list of dicts to the config.py file at:"
        + "\n\n    foreign_accounts()['btc']\n"
    )


def add_addresses_to_wallet():
    """
    authenticate all the addresses in the config file to the wallet
    """

    def add_priv_key(idx, address):
        """
        use multiprocessing so this does not get hung on open connections
        """
        access = create_access("btc")
        print((1 + idx), address["public"])
        try:
            access.abortrescan()
        except:
            pass
        try:
            print(access.importprivkey(address["private"]))
        except:
            pass
        try:
            access.abortrescan()
        except:
            pass

    print(f"\nADDING PRIVATE KEYS TO WALLET...")
    print("\nThis process takes about a minute, wait for command prompt to return\n")
    processes = {}
    for idx, address in enumerate(foreign_accounts()["btc"]):
        processes[idx] = Process(target=add_priv_key, args=(idx, address,))
        processes[idx].start()
        time.sleep(1)
    for idx, _ in enumerate(foreign_accounts()["btc"]):
        processes[idx].join()
    print("\nAUTHENTICATED!\n")


def get_address_info():
    """
    perform a bitcoind getaddressinfo for each public key in the config file
    """
    access = create_access("btc")
    print("\nGATHERING ADDRESS INFO...\n")
    for idx, key in enumerate(foreign_accounts()["btc"]):

        info = access.getaddressinfo(key["public"])
        if info["solvable"] and info["ismine"]:
            msg = "AUTHENTICATED WITH PRIVATE KEY"
        else:
            msg = "PUBLIC KEY ONLY"
        print((1 + idx), msg)
        print(info, "\n")


def get_balance():
    """
    get balance
    get balances
    list unspent solvable
    list unspend unsolvable
    get received by address for each in gateway addresses
    """
    access = create_access("btc")
    print("\nGATHERING BALANCE INFO...\n")
    print("get balance\n\n", access.getbalance())
    print("\nget balances\n")
    pprint(access.getbalances())
    unspent = access.listunspent()
    solvable = [i for i in unspent if i["solvable"]]
    unsolvable = [i for i in unspent if not i["solvable"]]
    print("\nlist unspent solvable\n")
    pprint(solvable)
    print("\nlist unspent unsolvable (not mine)\n")
    pprint(unsolvable)
    print("\nget received by address")
    for idx, key in enumerate(foreign_accounts()["btc"]):
        print("\n", idx, key["public"], access.getreceivedbyaddress(key["public"]))


def main():
    """
    user choice input
    """

    def create_accounts():
        """
        create some amount of bitcoin public/private key pair paper wallets
        """
        print("\nBitcoin accounts are free to create!")
        amount = int(input("\nHow many accounts would you like?\n\n"))
        choice = int(input("\nInput choice number\n\n   1) mainnet\n   2) testnet\n\n"))
        create_n_accounts(amount, testnet=bool(choice - 1))

    choice = int(
        input(
            "\nInput choice number\n\n"
            + "   1) Create paper wallets\n"
            + "   2) Authenticate config file addresses to wallet\n"
            + "   3) Get info on addresses in config.py\n"
            + "   4) Get wallet balance\n\n"
        )
    )
    dispatch = {
        1: create_accounts,
        2: add_addresses_to_wallet,
        3: get_address_info,
        4: get_balance,
    }
    dispatch[choice]()


if __name__ == "__main__":

    main()
