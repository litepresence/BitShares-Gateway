r"""
process_deposits.py
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

Falcon API Server for Gateway Deposit Requests
    upon deposit offer address
    upon receipt issue UIA
"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-few-public-methods, too-many-function-args
# pylint: disable=too-many-statements, too-many-locals, bare-except

# STANDARD MODULES
import time
from copy import deepcopy
from json import dumps as json_dumps
from os import urandom
from random import randint, random, seed
from subprocess import PIPE, Popen
from threading import Thread
from typing import Any, Dict

# THIRD PARTY MODULES
from falcon import App

# GATEWAY MODULES
import wsgiserver
from address_allocator import initialize_addresses, lock_address
from config import (contact, foreign_accounts, gateway_assets, offerings,
                    server_config, timing)
from ipc_utilities import chronicle, json_ipc
from listener_boilerplate import listener_boilerplate
from utilities import encode_memo, event_id, it, microseconds

# GLOBAL CONSTANTS
STDOUT, _ = Popen(["hostname", "-I"], stdout=PIPE, stderr=PIPE).communicate()
URL = STDOUT.decode("utf-8").split(" ", maxsplit=1)[0]
PORT = server_config()["port"]
ROUTE = server_config()["route"]
SERVER_URL = f"http://{URL}:{PORT}/{ROUTE}"


class GatewayDepositServer:
    """
    Provide Webserver Public API for deposit gateway service
    """

    # FIXME add api endpoint for flat fees, percent fees, and minimum deposit / withdraw
    def __init__(self, comptroller: Dict[str, Any]) -> None:
        """
        Initialize the GatewayDepositServer instance.

        :param comptroller: The comptroller dictionary.
        """
        self.comptroller = comptroller
        self.deposit_id = 0

    def on_get(self, req: Any, resp: Any) -> None:
        """
        When there is a get request made to the deposit server api
        User GET request includes the client_id's BitShares account_name
        Select a gateway wallet from list currently available; remove it from the list
        the available address list will be stored in a json_ipc text pipe
        Server RESPONSE is deposit address and timeout
        After timeout or deposit return address to text pipe list

        :param req: The Falcon request object.
        :param resp: The Falcon response object.
        """
        # localize the comptroller to this get request
        comptroller = deepcopy(self.comptroller)
        # seed pseudorandom in a cryptographically secure manner
        seed(urandom(20))
        # pause for a random 1/10 of a seocond
        time.sleep(random() / 10)
        # increment the event identifier
        self.deposit_id += 1
        # create a millesecond nonce to log this event
        nonce = microseconds()
        # extract the incoming parameters to a dictionary
        req_params = dict(req.params)
        # update the comptroller and chronicle this request
        comptroller["req_params"] = req_params
        comptroller["nonce"] = nonce
        comptroller["event_id"] = event_id("D", self.deposit_id)
        comptroller["issuer_action"] = "issue"
        msg = "received deposit request"
        chronicle(comptroller, msg)
        print(it("red", "DEPOSIT SERVER RECEIVED REQUEST"), SERVER_URL, req_params)
        # assuming the client is using an approved wallet this should never fail
        client_id, uia = "", ""
        comptroller["uia"] = uia
        comptroller["client_id"] = client_id
        try:
            client_id = req_params["client_id"]
            uia = req_params["uia_name"]
            comptroller["uia"] = uia
            comptroller["client_id"] = client_id
        except:
            msg = "invalid request"
            chronicle(comptroller, msg)
            return
        # translate the incoming uia request to the appropriate network
        network = ""
        if uia == gateway_assets()["xrp"]["asset_name"]:
            network = "xrp"
        if uia == gateway_assets()["xyz"]["asset_name"]:
            network = "xyz"
        elif uia == gateway_assets()["eos"]["asset_name"]:
            network = "eos"
        elif uia == gateway_assets()["btc"]["asset_name"]:
            network = "btc"
        elif uia == gateway_assets()["ltc"]["asset_name"]:
            network = "ltc"
        else:
            msg = "invalid request"
            chronicle(comptroller, msg)
            return
        # create a unique memo for this event
        memo = encode_memo(network, randint(10**17, 10**18))
        comptroller["memo"] = memo
        # beyond this point we have a valid uia and client_id
        comptroller["network"] = network
        if network in comptroller["offerings"]:
            if network in ["eos", "xrp"]:
                # UIA's using memo method will always default to zero idx gateway
                account_idx = 0
            else:
                # lock an address until this transaction is complete
                account_idx = lock_address(network)
            # lock_address will return None if all rotating addresses are in use
            if account_idx is not None:
                # configure the estimated gateway timing for this network
                estimate = int(timing()[network]["estimate"] / 60)
                # get the deposit address assigned to this request
                deposit_address = foreign_accounts()[network][account_idx]["public"]
                print("gateway address", deposit_address, "index", account_idx)
                # format a response json to the api request
                response_body = {
                    "response": "success",
                    "server_time": nonce,
                    "deposit_address": deposit_address,
                    "gateway_timeout": "30 MINUTES",
                    "msg": (
                        f"Welcome {client_id}, please tranfer your foreign blockchain "
                        + f"{network.upper()} asset, to the {uia.upper()} gateway "
                        + "'deposit_address' in this response.  "
                        + "Make ONE transfer to this address, "
                        + "within the 'gateway_timeout' specified. Transactions on "
                        + f"this network take about {estimate} minutes to confirm. "
                    ),
                    "contact": contact(),
                }
                if network in ["eos", "xrp", "xyz"]:  # some deposts will require a hashed memo
                    response_body["msg"] += (
                        f"\n\n*ALERT*: {network.upper()} deposits must include a the "
                        + "*MEMO* provided in this response!!!"
                    )
                    response_body["memo"] = memo
                print(it("red", f"STARTING {network.upper()} LISTENER TO ISSUE to {client_id}"))
                comptroller["amount"] = None
                comptroller["account_idx"] = account_idx
                comptroller["required_memo"] = memo
                comptroller["deposit_address"] = deposit_address
                listener = Thread(target=listener_boilerplate, args=(comptroller,))
                listener.start()
                msg = "listener process started"
                chronicle(comptroller, msg)
            else:
                msg = f"{comptroller['event_id']} {uia.upper()} gateway overloaded."
                print(it("red", msg.upper()))
                chronicle(comptroller, msg)
                response_body = {
                    "response": "error",
                    "server_time": nonce,
                    "msg": (
                        msg
                        + f"oops! all {uia.upper()} gateway addresses are "
                        + "in use, please try again later"
                    ),
                    "contact": contact(),
                }

        else:
            msg = f"{comptroller['event_id']} {uia.upper()} not listed in offerings."
            print(it("red", msg.upper()))
            chronicle(comptroller, msg)
            response_body = {
                "response": "error",
                "server_time": nonce,
                "msg": (
                    msg
                    + f"oops! {uia.upper()} gateway is currently down for "
                    + "maintainance, please try again later"
                ),
                "contact": contact(),
            }

        time.sleep(0.5)  # allow time for listener to start before offering address
        resp.media = response_body
        resp.status = 200


def deposit_server(comptroller: Dict[str, Any]) -> None:
    """
    Spawn a run forever API server instance and add routing information.

    :param comptroller: The comptroller dictionary.
    """
    json_ipc("deposit_id.txt", json_dumps(1))
    app = App()
    app.add_route(f"/{ROUTE}", GatewayDepositServer(comptroller))
    print(it("red", "INITIALIZING DEPOSIT SERVER\n"))
    print(it(159, "serving http at:"), it("green", SERVER_URL))
    my_apps = wsgiserver.WSGIPathInfoDispatcher({"/": app})
    server = wsgiserver.WSGIServer(my_apps, host="0.0.0.0", port=PORT, num_threads=100)
    server.start()


def unit_test() -> None:
    """
    Perform a unit test of the deposit server.

    Use unit_test_client.py to interact with the server.
    """
    print("\033c")
    print(unit_test.__doc__, "\n")
    # initialize financial incident reporting for audits
    comptroller = {}
    comptroller["session_unix"] = int(time.time())
    comptroller["session_date"] = time.ctime()
    comptroller["offerings"] = offerings()
    msg = "initializing gateway main"
    for network in comptroller["offerings"]:
        comptroller["network"] = network
        chronicle(comptroller, msg)
    comptroller["network"] = ""
    # set state machine to "all incoming accounts available"
    for network in comptroller["offerings"]:
        initialize_addresses(network)
    print("\nofferings " + it(45, comptroller["offerings"]), "\n")
    deposit_server(comptroller)


if __name__ == "__main__":
    unit_test()
