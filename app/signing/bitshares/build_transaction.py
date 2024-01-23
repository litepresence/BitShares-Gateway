r"""
build_transaction.py

  ____  _ _   ____  _                         
 | __ )(_) |_/ ___|| |__   __ _ _ __ ___  ___ 
 |  _ \| | __\___ \| '_ \ / _` | '__/ _ \/ __|
 | |_) | | |_ ___) | | | | (_| | | |  __/\__ \
 |____/|_|\__|____/|_| |_|\__,_|_|  \___||___/
       ____  _             _                  
      / ___|(_) __ _ _ __ (_)_ __   __ _      
      \___ \| |/ _` | '_ \| | '_ \ / _` |     
       ___) | | (_| | | | | | | | | (_| |     
      |____/|_|\__, |_| |_|_|_| |_|\__, |     
               |___/               |___/      


WTFPL litepresence.com Dec 2021 & squidKid-deluxe Jan 2024

Build graphene transactions from human-readable edicts

"""

# STANDARD PYTHON MODULES
import time
from binascii import unhexlify  # hexidecimal to binary text
from collections import OrderedDict
from decimal import Decimal as decimal
from struct import unpack_from  # convert back to PY variable


# GRAPHENE SIGNING MODULES
from .config import (
    AUTOSCALE,
    CORE_FEES,
    DUST,
    KILL_OR_FILL,
    LIMIT,
)
from .graphene_signing import (
    ObjectId,
)
from .rpc import (
    rpc_balances,
    rpc_block_number,
    rpc_open_orders,
    rpc_tx_fees,
)
from .utilities import it, to_iso_date

# MAX is 4294967295; year 2106 due to 4 byte unsigned integer
END_OF_TIME = 4 * 10**9  # about 75 years in future
# very little
SATOSHI = decimal(0.00000001)
# almost 1
SIXSIG = decimal(0.999999)


def graphenize_cancel(rpc, cancel_edicts, fees, order, account_name, tx_operations):
    """
    Translate cancel orders to graphene
    """
    for edict in cancel_edicts:
        if "ids" not in edict.keys():
            edict["ids"] = ["1.7.X"]
        if "1.7.X" in edict["ids"]:  # the "cancel all" signal
            # for cancel all op, we collect all open orders in 1 market
            edict["ids"] = rpc_open_orders(rpc, account_name, order["header"])
            print(it("yellow", str(edict)))
        for order_id in edict["ids"]:
            # confirm it is good 1.7.x format:
            order_id = str(order_id)
            aaa, bbb, ccc = order_id.split(".", 2)
            assert int(aaa) == 1
            assert int(bbb) == 7
            assert int(ccc) == float(ccc) > 0
            # create cancel fee ordered dictionary
            fee = OrderedDict([("amount", fees["cancel"]), ("asset_id", "1.3.0")])
            # create ordered operation dicitonary for this edict
            operation = [
                2,  # two means "Limit_order_cancel"
                OrderedDict(
                    [
                        ("fee", fee),
                        ("fee_paying_account", account_id),
                        ("order", order_id),
                        ("extensions", []),
                    ]
                ),
            ]
            # append the ordered dict to the trx operations list
            tx_operations.append(operation)
    return tx_operations


def graphenize_limit_orders(create_edicts, fees, asset, currency, account_id, tx_operations):
    """
    Translate limit orders to graphene
    """
    asset_id, asset_precision = asset
    currency_id, currency_precision = currency
    for idx, edict in enumerate(create_edicts):
        price = edict["price"]
        amount = edict["amount"]
        op_exp = int(edict["expiration"])
        # convert zero expiration flag to "really far in future"
        if op_exp == 0:
            op_exp = END_OF_TIME
        op_expiration = to_iso_date(op_exp)
        # we'll use ordered dicts and put items in api specific order
        min_to_receive = OrderedDict({})
        amount_to_sell = OrderedDict({})
        # derive min_to_receive & amount_to_sell from price & amount
        # means SELLING currency RECEIVING assets
        if edict["op"] == "buy":
            min_to_receive["amount"] = int(amount * 10**asset_precision)
            min_to_receive["asset_id"] = asset_id
            amount_to_sell["amount"] = int(amount * price * 10**currency_precision)
            amount_to_sell["asset_id"] = currency_id
        # means SELLING assets RECEIVING currency
        if edict["op"] == "sell":
            min_to_receive["amount"] = int(amount * price * 10**currency_precision)
            min_to_receive["asset_id"] = currency_id
            amount_to_sell["amount"] = int(amount * 10**asset_precision)
            amount_to_sell["asset_id"] = asset_id
        # Limit_order_create fee ordered dictionary
        fee = OrderedDict([("amount", fees["create"]), ("asset_id", "1.3.0")])
        # create ordered dicitonary from each buy/sell operation
        operation = [
            1,
            OrderedDict(
                [
                    ("fee", fee),  # OrderedDict
                    ("seller", account_id),  # "a.b.c"
                    ("amount_to_sell", amount_to_sell),  # OrderedDict
                    ("min_to_receive", min_to_receive),  # OrderedDict
                    ("expiration", op_expiration),  # ISO8601
                    ("fill_or_kill", KILL_OR_FILL),  # bool
                    (
                        "extensions",
                        [],
                    ),  # always empty list for our purpose
                ]
            ),
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_issue(issue_edicts, fees, asset_id, asset_precision, account_id, tx_operations):
    """
    Translate issue orders to graphene
    """
    for idx, issue in enumerate(issue_edicts):
        # convert to graphene amount, asset_id type
        # class Asset_issue(GrapheneObject): # OPERATION ID 14 "asset_issue"
        fee = OrderedDict([("amount", fees["issue"]), ("asset_id", "1.3.0")])
        graphene_amount = issue["amount"] * 10**asset_precision
        amount_dict = OrderedDict([("amount", graphene_amount), ("asset_id", asset_id)])
        # issue ordered dictionary from each buy/sell operation
        operation = [
            14,
            OrderedDict(
                [
                    ("fee", fee),
                    ("issuer", account_id),
                    ("asset_to_issue", amount_dict),
                    ("issue_to_account", issue["account_id"]),
                    # ("memo", issue["memo"]), # FIXME memos are not yet implemented
                    ("extensions", []),
                ]
            ),
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_reserve(reserve_edicts, fees, asset_id, asset_precision, account_id, tx_operations):
    """
    Translate reserve orders to graphene
    """
    for idx, reserve in enumerate(reserve_edicts):
        # convert to graphene amount, asset_id type
        # class Asset_reserve(GrapheneObject): # OPERATION ID 15 "asset_reserve"
        fee = OrderedDict([("amount", fees["reserve"]), ("asset_id", "1.3.0")])
        graphene_amount = reserve["amount"] * 10**asset_precision
        amount_dict = OrderedDict([("amount", graphene_amount), ("asset_id", asset_id)])
        # reserve ordered dictionary from each buy/sell operation
        operation = [
            15,
            OrderedDict(
                [
                    ("fee", fee),
                    ("payer", account_id),
                    ("amount_to_reserve", amount_dict),
                    ("extensions", []),
                ]
            ),
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_transfer(
    transfer_edicts, fees, asset_id, asset_precision, account_id, tx_operations
):
    """
    Translate transfer orders to graphene
    """
    for idx, transfer in enumerate(transfer_edicts):
        # convert to graphene amount, asset_id type
        # class Transfer(GrapheneObject): # OPERATION ID 0 "transfer"
        fee = OrderedDict([("amount", fees["transfer"]), ("asset_id", "1.3.0")])
        graphene_amount = int(transfer["amount"] * 10**asset_precision)
        amount_dict = OrderedDict([("amount", graphene_amount), ("asset_id", asset_id)])
        # transfer ordered dictionary from each buy/sell operation
        operation = [
            0,
            OrderedDict(
                [
                    ("fee", fee),
                    ("from", account_id),
                    ("to", transfer["account_id"]),
                    ("amount", amount_dict),
                    # ("memo", transfer["memo"]), # FIXME memos are not yet implemented
                    ("extensions", []),
                ]
            ),
        ]
        tx_operations.append(operation)
    return tx_operations


def graphenize_login(login_edicts, account_id, tx_operations):
    """
    Translate login to dummy graphene cancel order
    """
    if login_edicts:
        fee = OrderedDict([("amount", 0), ("asset_id", "1.3.0")])
        operation = [
            2,
            OrderedDict(
                [
                    ("fee", fee),
                    ("fee_paying_account", account_id),
                    ("order", "1.7.0"),
                    ("extensions", []),
                ]
            ),
        ]
        tx_operations.append(operation)
    return tx_operations


def scale_limit_orders(rpc, order, asset_id, currency_id, account_name, buy_edicts, sell_edicts):
    """
    Scale order size to funds on hand
    """
    if AUTOSCALE or CORE_FEES:
        currency, assets, bitshares = rpc_balances(rpc, account_name, order["header"])
        if AUTOSCALE and buy_edicts + sell_edicts:
            # autoscale buy edicts
            if buy_edicts:
                currency_value = 0
                # calculate total value of each amount in the order
                for idx, _ in enumerate(buy_edicts):
                    currency_value += buy_edicts[idx]["amount"] * buy_edicts[idx]["price"]
                # scale the order amounts to means
                scale = SIXSIG * currency / (currency_value + SATOSHI)
                if scale < 1:
                    print(it("yellow", "ALERT: scaling buy edicts to means: %.3f" % scale))
                    for idx, _ in enumerate(buy_edicts):
                        buy_edicts[idx]["amount"] *= scale
            # autoscale sell edicts
            if sell_edicts:
                asset_total = 0
                # calculate total amount in the order
                for idx, _ in enumerate(sell_edicts):
                    asset_total += sell_edicts[idx]["amount"]
                scale = SIXSIG * assets / (asset_total + SATOSHI)
                # scale the order amounts to means
                if scale < 1:
                    print(
                        it(
                            "yellow",
                            "ALERT: scaling sell edicts to means: %.3f" % scale,
                        )
                    )
                    for idx, _ in enumerate(sell_edicts):
                        sell_edicts[idx]["amount"] *= scale
        save_core_fees(buy_edicts, sell_edicts, asset_id, currency_id)

    # after scaling recombine buy and sell
    create_edicts = buy_edicts + sell_edicts

    ###### Remove dust edicts
    if DUST and create_edicts:
        create_edicts2 = []
        dust = DUST * 100000 / 10**asset_precision
        for idx, edict in enumerate(create_edicts):
            if edict["amount"] > dust:
                create_edicts2.append(edict)
            else:
                print(
                    it("red", "WARN: removing dust threshold %s order" % dust),
                    edict,
                )
        create_edicts = create_edicts2[:]  # copy as new list
        del create_edicts2
    return create_edicts


def save_core_fees(buy_edicts, sell_edicts, asset_id, currency_id):
    """
    Always save last two bitshares for fees
    """
    if CORE_FEES and (buy_edicts + sell_edicts and ("1.3.0" in [asset_id, currency_id])):
        # print(bitshares, 'BTS balance')
        # when BTS is the currency don't spend the last 2
        if currency_id == "1.3.0" and buy_edicts:
            bts_value = 0
            # calculate total bts value of each amount in the order
            for idx, _ in enumerate(buy_edicts):
                bts_value += buy_edicts[idx]["amount"] * buy_edicts[idx]["price"]
            # scale the order amounts to save last two bitshares
            scale = SIXSIG * max(0, (bitshares - 2)) / (bts_value + SATOSHI)
            if scale < 1:
                print(it("yellow", "ALERT: scaling buy edicts for fees: %.4f" % scale))
                for idx, _ in enumerate(buy_edicts):
                    buy_edicts[idx]["amount"] *= scale
        # when BTS is the asset don't sell the last 2
        if asset_id == "1.3.0" and sell_edicts:
            bts_total = 0
            # calculate total of each bts amount in the order
            for idx, _ in enumerate(sell_edicts):
                bts_total += sell_edicts[idx]["amount"]
            scale = SIXSIG * max(0, (bitshares - 2)) / (bts_total + SATOSHI)
            # scale the order amounts to save last two bitshares
            if scale < 1:
                print(
                    it(
                        "yellow",
                        "ALERT: scaling sell edicts for fees: %.4f" % scale,
                    )
                )
                for idx, _ in enumerate(sell_edicts):
                    sell_edicts[idx]["amount"] *= scale
    return buy_edicts, sell_edicts


def build_transaction(rpc, order):
    """
    # this performs incoming limit order api conversion
    # from human terms to graphene terms

    # humans speak:
     - account name, asset name, order number
     - decimal amounts, rounded is just fine
     - buy/sell/cancel
     - amount of assets
     - price in currency

    # graphene speaks:
     - 1.2.x, 1.3.x, 1.7.x
     - only in integers
     - create/cancel
     - min_to_receive/10^receiving_precision
     - amount_to_sell/10^selling_precision

    # build_transaction speaks:
     - list of buy/sell/cancel human terms edicts any order in
     - validated data request
     - autoscale amounts if out of budget
     - autoscale amounts if spending last bitshare
     - bundled cancel/buy/sell transactions out; cancel first
     - prevent inadvertent huge number of orders
     - do not place orders for dust amounts
    """
    # VALIDATE INCOMING DATA
    for key, expected_type in [("edicts", list), ("nodes", list), ("header", dict)]:
        if not isinstance(order[key], expected_type):
            raise ValueError(
                f"order parameter '{key}' must be of type {expected_type.__name__}:"
                f" {order[key]}; is {type(order[key]).__name__}"
            )

    # the location of the decimal place must be provided by order
    asset_precision = int(order["header"]["asset_precision"])
    asset_id = str(order["header"]["asset_id"])
    account_id = str(order["header"]["account_id"])
    account_name = str(order["header"]["account_name"])
    checks = [account_id, asset_id]

    # perform checks on currency for limit orders
    if order["edicts"][0]["op"] in ["buy", "sell"]:
        currency_precision = int(order["header"].get("currency_precision", 0))
        currency_id = str(order["header"].get("currency_id", 0))
        checks.append(currency_id)
        if not currency_precision or not currency_id:
            return -1
    # validate a.b.c identifiers of account id and asset ids
    for check in checks:
        ObjectId(check)
    # GATHER TRANSACTION HEADER DATA
    # fetch block data via websocket request
    block = rpc_block_number(rpc)
    ref_block_num = block["head_block_number"] & 0xFFFF
    ref_block_prefix = unpack_from("<I", unhexlify(block["head_block_id"]), 4)[0]
    # fetch limit order create and cancel fee via websocket request
    fees = rpc_tx_fees(rpc, account_id)
    # establish transaction expiration
    tx_expiration = to_iso_date(int(time.time() + 120))
    # initialize tx_operations list
    tx_operations = []

    # Sort incoming edicts by type
    edict_types = {
        "cancel": [],
        "buy": [],
        "sell": [],
        "issue": [],
        "reserve": [],
        "transfer": [],
        "login": [],
    }

    for edict in order["edicts"]:
        if edict["op"] in edict_types:
            print(it("yellow", str({k: str(v) for k, v in edict.items()})))
            edict_types[edict["op"]].append(edict)

    # convert to decimal type

    for op_type in ("buy", "sell"):
        for idx, item in enumerate(edict_types[op_type]):
            edict_types[op_type][idx]["amount"] = decimal(item["amount"])
            edict_types[op_type][idx]["price"] = decimal(item["price"])

    tx_operations = graphenize_cancel(
        rpc, edict_types["cancel"], order, account_name, fees, tx_operations
    )
    if any([edict_types["sell"], edict_types["buy"]]):
        scaled_limit_orders = scale_limit_orders(
            rpc, order, asset_id, currency_id, account_name, edict_types["buy"], edict_types["sell"]
        )
        tx_operations = graphenize_limit_orders(
            scaled_limit_orders,
            fees,
            [asset_id, asset_precision],
            [currency_id, currency_precision],
            account_id,
            tx_operations,
        )
    tx_operations = graphenize_transfer(
        edict_types["transfer"], fees, asset_id, asset_precision, account_id, tx_operations
    )
    tx_operations = graphenize_issue(
        edict_types["issue"], fees, asset_id, asset_precision, account_id, tx_operations
    )
    tx_operations = graphenize_reserve(
        edict_types["reserve"], fees, asset_id, asset_precision, account_id, tx_operations
    )
    tx_operations = graphenize_login(edict_types["login"], account_id, tx_operations)

    # prevent inadvertent huge number of orders
    tx_operations = tx_operations[:LIMIT]
    # the trx is just a regular dictionary we will convert to json later
    # the operations themselves must still be an OrderedDict
    trx = {
        "ref_block_num": ref_block_num,
        "ref_block_prefix": ref_block_prefix,
        "expiration": tx_expiration,
        "operations": tx_operations,
        "signatures": [],
        "extensions": [],
    }
    return trx
