from .graphene_auth import broker, prototype_order, issue, reserve
from .config import NODES


def main():
    info = {
        "asset_id": "1.3.123",  # "1.3.x"
        "asset_name": "GATEWAY.XYZ",  # all caps
        "asset_precision": 5,  # int()
        "currency_id": "1.3.1234",  # "1.3.x"
        "currency_name": "GATEWAY.XYZA",  # all caps
        "currency_precision": 5,  # int()
        "issuer_id": "1.2.54321",  # "1.2.x"
        "issuer_public": "user",  # bitshares account name
        "issuer_private": "X" * 32,  # wif
    }

    issue(info, 10, "1.2.1234")
    reserve(info, 10)

    order = prototype_order(info)
    order["edicts"] = [{"op": "transfer", "amount": 10, "account_id": "1.2.789"}]
    broker(order)

    order = prototype_order(info)
    order["edicts"] = [{"op": "buy", "amount": 10, "price": 0.1, "expiration": 0}]
    broker(order)

    order = prototype_order(info)
    order["edicts"] = [{"op": "sell", "amount": 10, "price": 0.1, "expiration": 0}]
    broker(order)

    order = prototype_order(info)
    order["edicts"] = [{"op": "login"}]
    broker(order)


if __name__ == "__main__":
    main()
