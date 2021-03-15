r"""
process_parachains.py
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

apodize block data and write a parachain to disk for each offering
"""

# STANDARD PYTHON MODULES
import time
from json import dumps as json_dumps
from multiprocessing import Process

# BITSHARES GATEWAY MODULES
from config import offerings, parachain_params
from parachain_eosio import apodize_block_data as apodize_eosio_block_data
from parachain_eosio import get_block_number as get_eosio_block_number
from parachain_ltcbtc import apodize_block_data as apodize_ltcbtc_block_data
from parachain_ltcbtc import get_block_number as get_ltcbtc_block_number
from parachain_ripple import apodize_block_data as apodize_ripple_block_data
from parachain_ripple import get_block_number as get_ripple_block_number
from utilities import json_ipc, chronicle


def get_block_number(network):
    """
    return the correct irreversible block number function for each network
    """
    dispatch = {
        "ltc": get_ltcbtc_block_number,
        "btc": get_ltcbtc_block_number,
        "eos": get_eosio_block_number,
        "xrp": get_ripple_block_number,
    }
    return dispatch[network](network)


def apodize_block_data(network):
    """
    return the correct apodize function for each network
    """
    dispatch = {
        "ltc": apodize_ltcbtc_block_data,
        "btc": apodize_ltcbtc_block_data,
        "eos": apodize_eosio_block_data,
        "xrp": apodize_ripple_block_data,
    }
    return dispatch[network]


def spawn_parachains(comptroller):
    """
    for each network listed in offerings launch a parachain subprocess
    """
    # scrub the parachains
    for network in offerings():
        json_ipc(f"parachain_{network}.txt", json_dumps({}))

    # launch parachain writing processes
    parachains = {}
    for network in offerings():
        comptroller["network"] = network
        parachains[network] = Process(target=window_parachain, args=(comptroller,))
        parachains[network].start()


def window_parachain(comptroller):
    """
    maintain a windowed parachain in the pipe folder as parachain_{network}.txt
    """
    network = comptroller["network"]
    block_num = get_block_number(network) - 1
    apodize = apodize_block_data(network)
    new_blocks = [block_num]
    new_parachain = apodize(comptroller, new_blocks)
    json_ipc(f"parachain_{network}.txt", json_dumps(new_parachain))
    params = parachain_params()
    chronicle(comptroller, "initilizing parachain")
    while True:
        # limit parachain write frequency
        time.sleep(params[network]["pause"])
        # get the current block number
        current_block_num = get_block_number(network)
        # get the cahed parachain via text pipe ipc
        parachain_cache = json_ipc(f"parachain_{network}.txt")
        # extract the block numbers in the cached parachain
        parachain_cache_nums = sorted([str(i) for i in list(parachain_cache.keys())])
        # determine the maximum block number on record
        max_checked_block = max(parachain_cache_nums)
        if int(current_block_num) > int(max_checked_block) + 1:
            # print(current_block_num)
            # new blocks are all those from max on record to the current
            new_blocks = [*range(int(max_checked_block) + 1, int(current_block_num))]
            # get block data for all the new block numbers
            new_parachain = apodize(comptroller, new_blocks)
            # append the new parachain to the old
            parachain_cache.update(new_parachain)
            # get all the block numbers in the concatenated parachains
            parachain_cache_nums = sorted(
                [str(i) for i in list(parachain_cache.keys())]
            )
            # window the block numbers to the latest blocks only
            window = parachain_cache_nums[-params[network]["window"] :]
            # window the parachain
            windowed_parachain = {
                k: v for k, v in parachain_cache.items() if k in window
            }
            # print(len(windowed_parachain))
            # write the windowed parachain to file
            json_ipc(f"parachain_{network}.txt", json_dumps(windowed_parachain))


def unit_test_parachains():
    """
    this should launch parachains in the pipe folder for networks in config offerings()
    """
    comptroller = {}
    spawn_parachains(comptroller)


if __name__ == "__main__":
    unit_test_parachains()
