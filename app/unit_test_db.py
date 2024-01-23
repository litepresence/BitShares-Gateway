"""
clear database and add test data
"""
import time

from db_setup import reset_database
from ipc_utilities import chronicle

reset_database()


comptroller = {
    "process": "ingots",
    "msg": "Hi!",
    "unix": 123456,
    "event_unix": 123456,
    "date": "Jan 1 1234",
    "year": 6431,
    "month": 2,
    "network": "ABC",
    "tx_id": "1234",
    "order_public": "yes",
    "order_to": "me",
    "order_quantity": 0,
}
i = 0

# while True:
#     i += 1
#     chronicle(comptroller, msg="testing..." + str(i))
#     time.sleep(1)
chronicle(comptroller, msg="testing2.-..")
chronicle(comptroller, msg="testing3.*..")
chronicle(comptroller, msg="testing../.")
chronicle(comptroller, msg="testing2.7..")
chronicle(comptroller, msg="testing3.8..")
chronicle(comptroller, msg="testing..9.")
chronicle(comptroller, msg="testing2.4..")
chronicle(comptroller, msg="testing3.5..")
chronicle(comptroller, msg="testing...6")
chronicle(comptroller, msg="testing2.0..")
chronicle(comptroller, msg="testing3.1..")


comptroller = {
    "process": "withdrawals",
    "msg": "Hi!",
    "unix": 123456,
    "event_unix": 123456,
    "date": "Jan 40 3025",
    "year": 3025,
    "month": 12,
    "network": "OEM",
    "session_unix": 1200,
    "session_date": "May 12 2035",
    "op": "None",
    "nonce": 4567262,
    "uia_id": "1.3.1234",
    "event_id": "1.7.4568",
    "withdrawal_amount": 2,
    "gateway_address": "abcd",
    "client_address": "bcda",
    "client_id": "1.2.1235",
    "account_idx": 1,
    "tx_id": "1.11.1234",
    "order_public": "abcde",
    "order_to": "bcda",
    "order_quantity": 12,
    "memo": "yay!",
}

time.sleep(2)
chronicle(comptroller, msg="testing..1.")
chronicle(comptroller, msg="testing2.2..")
chronicle(comptroller, msg="testing3.3..")
chronicle(comptroller, msg="testing..4.")
chronicle(comptroller, msg="testing2.5..")
chronicle(comptroller, msg="testing3.6..")
chronicle(comptroller, msg="testing..7.")
chronicle(comptroller, msg="testing2.8..")
chronicle(comptroller, msg="testing3.9..")
chronicle(comptroller, msg="testing../.")
chronicle(comptroller, msg="testing2.*..")
chronicle(comptroller, msg="testing3.-..")


comptroller = {
    "process": "deposits",
    "msg": "Hi!",
    "unix": 123456,
    "event_unix": 123456,
    "date": "Jan 8 1994",
    "year": 1994,
    "month": 1,
    "network": "RPC",
    "session_unix": 123456,
    "session_date": "March 12 1992",
    "req_params": "Nothing to see here",
    "nonce": 1234569,
    "event_id": "1.11.12352",
    "uia": "aiu",
    "client_id": "1.2.45328",
    "amount": 3.141592656853,
    "account_idx": 1,
    "required_memo": "Nope.",
    "deposit_address": "1.2.1586",
}

chronicle(comptroller, msg="testing...")
chronicle(comptroller, msg="testing2...")
chronicle(comptroller, msg="testing3...")
chronicle(comptroller, msg="testing4...")
chronicle(comptroller, msg="testing21...")
chronicle(comptroller, msg="testing32...")
chronicle(comptroller, msg="testing.3..")
chronicle(comptroller, msg="testing23...-")
chronicle(comptroller, msg="testing33..8.")
chronicle(comptroller, msg="testing.3.-.")
chronicle(comptroller, msg="testing24...")
chronicle(comptroller, msg="testing36...")
