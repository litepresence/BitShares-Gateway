"""
Test a full gateway operation (deposit/withdrawal) on the XYZ paper chain
"""

import json
import time

from requests import get

from config import gateway_assets
from ipc_utilities import json_ipc

XYZ_ADDRESS = "1.2.123456789"
BITSHARES_ADDRESS = "1.2.31415"


print("requesting deposit address")
resp = get(
    f"http://localhost:4018/gateway?uia_name=GATEWAY.XYZ&client_id={BITSHARES_ADDRESS}"
).json()
print(f"sending XYZs to {resp['deposit_address']} with memo {resp['memo']}")
trx = {
    "type": "transfer",
    "quantity": 100000,  # Graphene; precision 5
    "to": resp["deposit_address"],
    "public": XYZ_ADDRESS,
    "memo": resp["memo"],
    "block_num": int(time.time() / 3) + 1,  # int: blocknum to execute in, 0 for asap
}
print(json.dumps(trx, indent=4))
json_ipc("xyz_transactions.txt", json.dumps([trx]))

print("pausing 20 seconds")
time.sleep(20)


print("withdrawing 0.1 GATEWAY.XYZ token")
json_ipc(
    "unit_test_withdrawal.txt",
    json.dumps(
        [
            0,
            {
                "amount": {"asset_id": gateway_assets()["xyz"]["asset_id"], "amount": 10000},
                "to": gateway_assets()["xyz"]["issuer_id"],
                "memo": XYZ_ADDRESS,
                "from": BITSHARES_ADDRESS,
            },
        ]
    ),
)
