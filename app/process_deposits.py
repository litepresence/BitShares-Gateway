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
# pylint: disable=too-few-public-methods, no-self-use, too-many-function-args
# pylint: disable=bad-continuation, too-many-statements, too-many-locals, bare-except


# STANDARD PYTHON MODULES
import time
from copy import deepcopy
from json import dumps as json_dumps
from subprocess import PIPE, Popen
from threading import Thread
from multiprocessing import Process
from wsgiref.simple_server import make_server

# THIRD PARTY MODULES
from falcon import HTTP_200, App

# BITSHARES GATEWAY MODULES
from address_allocator import initialize_addresses, lock_address
from config import (contact, foreign_accounts, gateway_assets, offerings,
                    server_config, timing)
from listener_boilerplate import listener_boilerplate
from utilities import (chronicle, encode_memo, it, line_number, milleseconds,
                       timestamp, event_id, json_ipc)

# GLOBALS
STDOUT, _ = Popen(["hostname", "-I"], stdout=PIPE, stderr=PIPE).communicate()
URL = STDOUT.decode("utf-8").split(" ")[0]
PORT = server_config()["port"]
ROUTE = server_config()["route"]
SERVER_URL = f"http://{URL}:{PORT}/{ROUTE}"


class GatewayDepositServer:
    """
    Provide Webserver Public API for deposit gateway service
    """

    # FIXME add api endpoint for flat fees, percent fees, and minimum deposit / withdraw
    def __init__(self, comptroller):
        self.comptroller = comptroller

    def on_get(self, req, resp):
        """
        When there is a get request made to the deposit server api
        User GET request includes the client_id's BitShares account_name
        Select a gateway wallet from list currently available; remove it from the list
        the available address list will be stored in a json_ipc text pipe
        Server RESPONSE is deposit address and timeout
        After timeout or deposit return address to text pipe list
        """
        # increment the event identifier
        previous_id = int(json_ipc("deposit_id.txt"))
        deposit_id = previous_id + 1
        json_ipc("deposit_id.txt", json_dumps(deposit_id))
        # localize the comptroller to this get request
        comptroller = self.comptroller
        # create a millesecond nonce to log this event
        nonce = milleseconds()
        # extract the incoming parameters to a dictionary
        req_params = dict(req.params)
        # update the comptroller and chronicle this request
        comptroller["req_params"] = req_params
        comptroller["nonce"] = nonce
        comptroller["event_id"] = event_id("D", deposit_id)
        comptroller["issuer_action"] = "issue"
        msg = "received deposit request"
        chronicle(comptroller, msg)
        timestamp()
        line_number()
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
        # beyond this point we have a valid uia and client_id
        #print("network", network, "\n")
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
                timestamp()
                line_number()
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
                        f"Welcome {client_id}, please deposit your gateway issued "
                        + f"{network.upper()} asset, to the {uia.upper()} gateway "
                        + "'deposit_address' in this response.  "
                        + "Make ONE transfer to this address, "
                        + "within the 'gateway_timeout' specified. Transactions on "
                        + f"this network take about {estimate} minutes to confirm. "
                    ),
                    "contact": contact(),
                }
                memo = ""
                if network in ["eos", "xrp"]:  # some deposts will require a hashed memo
                    memo = encode_memo(network, client_id, nonce)
                    response_body["msg"] += (
                        f"\n\n*ALERT*: {network.upper()} deposits must include a the "
                        + "*MEMO* provided in this response!!!"
                    )
                    response_body["memo"] = memo
                response_body = json_dumps(response_body)
                print(it("red", f"STARTING {network} LISTENER TO ISSUE to {client_id}"))
                # update the audit dictionary
                comptroller["amount"] = None
                comptroller["account_idx"] = account_idx
                comptroller["required_memo"] = memo
                comptroller["deposit_address"] = deposit_address
                # in subprocess listen for payment from client_id to gateway[idx]
                # upon receipt issue asset, else timeout
                listener = Thread(target=listener_boilerplate, args=(deepcopy(comptroller),))
                listener.start()
                msg = "listener process started"
                chronicle(comptroller, msg)
            else:
                msg = f"{uia.upper()} gateway overloaded"
                print(it("red", msg.upper()))
                chronicle(comptroller, msg)
                response_body = json_dumps(
                    {
                        "response": "error",
                        "server_time": nonce,
                        "msg": f"oops! all {uia.upper()} gateway addresses are in use, "
                        + "please try again later",
                        "contact": contact(),
                    }
                )
        else:
            msg = f"{uia.upper()} not listed in offerings"
            chronicle(comptroller, msg)
            response_body = json_dumps(
                {
                    "response": "error",
                    "server_time": nonce,
                    "msg": f"oops! {uia.upper()} gateway is currently down for "
                    + "maintainance, please try again later",
                    "contact": contact(),
                }
            )
        time.sleep(5)  # allow some time for listener to start before offering address
        print(9)
        resp.body = response_body
        resp.status = HTTP_200


def deposit_server(comptroller):
    """
    spawn a run forever api server instance and add routing information
    """
    json_ipc("deposit_id.txt", json_dumps(1))
    app = App()
    app.add_route(f"/{ROUTE}", GatewayDepositServer(comptroller))
    print(it("red", "INITIALIZING DEPOSIT SERVER\n"))
    # print(comptroller["offerings"], "\n")
    print(it(159, "serving http at:"), it("green", SERVER_URL))
    with make_server("", PORT, app) as httpd:
        httpd.serve_forever()


def unit_test():
    """
    perform a unit test of the deposit server

    use unit_test_client.py to interact with the server
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
