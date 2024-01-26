r"""
utilities.py
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

a collection of shared utilities for Graphene Python Gateway
"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-arguments, broad-except, invalid-name
# pylint: disable=too-many-branches, too-many-statements, no-member

# STANDARD PYTHON MODULES
import base64
import inspect
import time
import traceback
from calendar import timegm
from hashlib import sha256
from json import dumps as json_dumps
from json import loads as json_loads
from random import choice, random, shuffle

from websocket import create_connection as wss

# BITSHARES GATEWAY MODULES
from nodes import bitcoin_node, bitshares_nodes, litecoin_node

# THIRD PARTY MODULES
from signing.bitcoin.bitcoinrpc.authproxy import AuthServiceProxy


def encode_memo(network, seed):
    """
    encode memos for transaction hashes when using single gateway address
    """
    sha_msg = sha256(bytearray(str(seed), "utf-8")).hexdigest()
    if network == "xrp":
        # 10 digit base 10, eg for ripple network
        # NOTE: pylint does not like .hex() but its a pylint bug not a real issue
        memo = str(int(sha_msg.encode(encoding="utf_8").hex(), 16))[10:20]
        memo = int(("1" + memo)[:10]) if memo[0] == "0" else int(memo)
    else:
        # 10 digit base 32 ~1,000,000,000,000,000 unique values
        memo = (
            base64.b32encode(bytearray(sha_msg, "utf-8")).decode("utf-8").lower()[:10]
        )
    return memo


def microseconds():
    """
    nano * 10**3 = micro * 10**3 = milli * 10**3 = second  as integer
    """
    return int(time.time() * 10**6)


def roughly(amount, reference):
    """
    ensure an amount is roughly equal to the reference
    :param float(amount)
    :param float(reference)
    :return True / False
    """
    return bool(0.9999 * reference <= amount <= reference * 1.0001)


def create_access(network):
    """
    create an RPC connection to bitcoind or litecoind node
    """
    nodes = {
        "btc": bitcoin_node(),
        "ltc": litecoin_node(),
    }
    node = nodes[network]
    if network == "btc":
        access = AuthServiceProxy(node[0])
        try:
            access.loadwallet(node[1])
        except Exception:
            pass
    elif network == "ltc":
        access = AuthServiceProxy(node[0] + "/wallet/" + node[1])

    return access


def event_id(prefix, number):
    """
    create and event id of fixed length
    """
    return prefix + ("0000000000" + str(number))[-10:]


def line_number():
    """
    prints file name, line number and function of the caller; h/t @ Streamsoup
    """
    stack = inspect.stack()
    full_stack = str(stack[1][1]) + ":" + str(stack[1][2]) + ":" + str(stack[1][3])
    print(full_stack)
    return full_stack


def timestamp():
    """
    print local time, timezone, and unix timestamp
    """
    now = (
        str(time.ctime())
        + " "
        + str(time.tzname[0])
        + " epoch "
        + str(int(time.time()))
    )
    print(now)
    return now


def from_iso_date(date):
    """
    BitShares ISO8601 or time.ctime to UNIX time conversion
    """
    ret = 0
    try:
        ret = int(timegm(time.strptime(str(date), "%Y-%m-%dT%H:%M:%S")))
    except ValueError:
        ret = int(timegm(time.strptime(str(date), "%a %b %d %H:%M:%S %Y")))
    return ret


def logo():
    r"""
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
    """
    return logo.__doc__


def precisely(number, precision):
    """
    format float or int as string to specific number of decimal places
    :param number: int or float to be returned to specific number of decimal places
    :param int(precision): truncated decimal places to return; no more no less
    :return str(): string representation of a decimal to specific number of places
    """
    num = f"{float(number):.99f}"
    for _ in range(precision):
        num += "0"
    return num[: num.find(".") + precision + 1]


def vivid(bright=0.5):
    """
    a random vivid rgb tuple of specified brightness
    :param float(bright): max(1)=all white; min(0)=all black
    """
    if 0 > bright > 1:
        raise ValueError("brightness must be between 0 and 1")
    num = int(10000000 * random())
    color = (
        int(str(num)[-3:]) % 255,
        int(str(num)[-4:-1]) % 255,
        int(str(num)[-5:-2]) % 255,
    )
    min_bright = int(bright * 222 * 3)
    max_bright = int(bright * 255 * 3)
    while sum(color) < min_bright:
        color = [i + 1 if i < 255 else 255 for i in color]
    while sum(color) > max_bright:
        color = [i - 1 if i > 0 else 0 for i in color]
    return tuple(color)


def xterm():
    """
    a random color code for xterm-256color pallet
    eliminating primary, secondary, darkest, and gray scale
    """
    not_vivid = [*range(52, 58)] + [88, 89]
    return choice([i for i in [*range(27, 217)] if i not in not_vivid])


def it(style, text, foreground=True):
    """
    Color printing in terminal
    """
    emphasis = {
        "red": 197,
        "green": 154,
        "yellow": 227,
        "orange": 208,
        "purple": 141,  # 177,
        "blue": 51,
        "white": 231,
        "gray": 250,
        "grey": 250,
        "black": 236,
        "cyan": 51,
    }
    lie = 4
    if foreground:
        lie = 3
    if isinstance(style, tuple):  # RGB
        ret = f"\033[{lie}8;2;{style[0]};{style[1]};{style[2]}m{str(text)}\033[0;00m"
    elif isinstance(style, int):  # xterm-256
        ret = f"\033[{lie}8;5;{style}m{str(text)}\033[0;00m"
    else:  # 6 color emphasis dict
        ret = f"\033[{lie}8;5;{emphasis[style]}m{str(text)}\033[0m"
    return ret


def at(pos, text):
    """
    Use ANSI escape code to print text at position
    """
    new_text = "\033[s"
    for idx, line in enumerate(text.split("\n")):
        new_text += f"\033[{pos[1]+idx};{pos[0]}H{line}"
    return new_text + "\033[u"


def raw_operations():
    """
    bitshares/python-bitshares/master/bitsharesbase/operationids.py"
    """
    return {
        0: "transfer",
        1: "limit_order_create",
        2: "limit_order_cancel",
        3: "call_order_update",
        4: "fill_order",
        5: "account_create",
        6: "account_update",
        7: "account_whitelist",
        8: "account_upgrade",
        9: "account_transfer",
        10: "asset_create",
        11: "asset_update",
        12: "asset_update_bitasset",
        13: "asset_update_feed_producers",
        14: "asset_issue",
        15: "asset_reserve",
        16: "asset_fund_fee_pool",
        17: "asset_settle",
        18: "asset_global_settle",
        19: "asset_publish_feed",
        20: "witness_create",
        21: "witness_update",
        22: "proposal_create",
        23: "proposal_update",
        24: "proposal_delete",
        25: "withdraw_permission_create",
        26: "withdraw_permission_update",
        27: "withdraw_permission_claim",
        28: "withdraw_permission_delete",
        29: "committee_member_create",
        30: "committee_member_update",
        31: "committee_member_update_global_parameters",
        32: "vesting_balance_create",
        33: "vesting_balance_withdraw",
        34: "worker_create",
        35: "custom",
        36: "assert",
        37: "balance_claim",
        38: "override_transfer",
        39: "transfer_to_blind",
        40: "blind_transfer",
        41: "transfer_from_blind",
        42: "asset_settle_cancel",
        43: "asset_claim_fees",
        44: "fba_distribute",
        45: "bid_collateral",
        46: "execute_bid",
        47: "asset_claim_pool",
        48: "asset_update_issuer",
        49: "htlc_create",
        50: "htlc_redeem",
        51: "htlc_redeemed",
        52: "htlc_extend",
        53: "htlc_refund",
    }


def wss_handshake(rpc):
    """
    Create a websocket handshake
    """
    nodes = bitshares_nodes()
    while True:
        try:
            rpc.close()
        except Exception:
            pass
        try:
            shuffle(nodes)
            node = nodes[0]
            start = time.time()
            rpc = wss(node, timeout=4)
            if time.time() - start < 3:
                break
        except Exception:
            print(node, "failed to connect")
    return rpc


def wss_query(rpc, params):
    """
    Send and receive websocket requests
    """
    query = json_dumps({"method": "call", "params": params, "jsonrpc": "2.0", "id": 1})
    # print(query)
    rpc.send(query)
    ret = rpc.recv()
    # print(ret)
    ret = json_loads(ret)
    # print(ret)
    try:
        return ret["result"]  # if there is result key take it
    except Exception:
        try:
            print(ret)
        except Exception:
            pass
        print(traceback.format_exc())
        return None


def block_ops_logo():
    """
     ######  ## ######## ####### ##   ##  #####  ######  ####### #######
     ##   ## ##    ##    ##      ##   ## ##   ## ##   ## ##      ##
     ######  ##    ##    ####### ####### ####### ######  #####   #######
     ##   ## ##    ##         ## ##   ## ##   ## ##   ## ##           ##
     ######  ##    ##    ####### ##   ## ##   ## ##   ## ####### #######

    ######  ##       ######   ###### ##   ##      ######  ######  #######
    ##   ## ##      ##    ## ##      ##  ##      ##    ## ##   ## ##
    ######  ##      ##    ## ##      #####       ##    ## ######  #######
    ##   ## ##      ##    ## ##      ##  ##      ##    ## ##           ##
    ######  #######  ######   ###### ##   ##      ######  ##      #######

        ##      ## ####### ######## ####### ###    ## ####### ######
        ##      ## ##         ##    ##      ####   ## ##      ##   ##
        ##      ## #######    ##    #####   ## ##  ## #####   ######
        ##      ##      ##    ##    ##      ##  ## ## ##      ##   ##
        ####### ## #######    ##    ####### ##   #### ####### ##   ##
    """
    return logo.__doc__
