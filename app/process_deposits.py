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
from json import dumps as json_dumps
from subprocess import PIPE, Popen
from threading import Thread
from wsgiref.simple_server import make_server

# THIRD PARTY MODULES
from falcon import HTTP_200, App

# BITSHARES GATEWAY MODULES
from address_allocator import initialize_addresses, lock_address
from config import (contact, foreign_accounts, gateway_assets, offerings,
                    server_config, timing)
from listener_boilerplate import listener_boilerplate
from utilities import (chronicle, encode_memo, it, line_number, milleseconds,
                       timestamp)

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
        # localize the comptroller to this get request
        comptroller = self.comptroller
        # create a millesecond nonce to log this event
        nonce = milleseconds()
        # extract the incoming parameters to a dictionary
        req_params = dict(req.params)
        # update the comptroller and chronicle this request
        comptroller["req_params"] = req_params
        comptroller["nonce"] = nonce
        comptroller["issuer_action"] = "issue"
        msg = "received deposit request"
        chronicle(comptroller, msg)
        timestamp()
        line_number()
        print(it("red", "DEPOSIT SERVER RECEIVED A GET REQUEST"), "\n")
        print(SERVER_URL)
        print(req_params, "\n")
        client_id, uia = "", ""
        try:
            client_id = req_params["client_id"]
            uia = req_params["uia_name"]
            print(1)
        except:
            msg = "invalid request"
            chronicle(comptroller, msg)
            print(2)
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
            print(3)
        print("network", network, "\n")
        print(4)
        comptroller["uia"] = uia
        comptroller["network"] = network
        comptroller["client_id"] = client_id
        if network in comptroller["offerings"]:
            trx_hash = ""
            print(5)
            # lock an address until this transaction is complete
            if network == "eos":
                account_idx = 0
            else:
                account_idx = lock_address(network)
            print("gateway index", account_idx, "\n")
            print(6)
            if account_idx is not None:
                timestamp()
                line_number()
                print(7)
                # configure the estimated gateway timing for this network
                estimate = int(0.5 * timing()[network]["timeout"] / 60)
                # get the deposit address assigned to this request
                deposit_address = foreign_accounts()[network][account_idx]["public"]
                print("gateway address", deposit_address, "\n")
                # format a response json to the api request
                response_body = {
                    "response": "success",
                    "server_time": nonce,
                    "deposit_address": deposit_address,
                    "gateway_timeout": "30 MINUTES",
                    "msg": (
                        f"Welcome {client_id}, please deposit your gateway issued "
                        + f"{network} asset, to the {uia} gateway 'deposit_address' "
                        + "in this response.  Make ONE transfer to this address, "
                        + "within the gateway_timeout specified. Transactions on "
                        + f"this network take about {estimate} "
                        + f"minutes to confirm. "
                    ),
                    "contact": contact(),
                }
                if network == "eos":  # eos deposts will require a hashed memo
                    trx_hash = encode_memo(client_id, nonce)
                    response_body[
                        "msg"
                    ] += "\n\nALERT: EOS transfers must include a 'trx_hash' memo!!!"
                    response_body["trx_hash"] = trx_hash
                response_body = json_dumps(response_body)
                print(8, response_body)

                print(
                    it("red", f"STARTING {network} LISTENER TO ISSUE to {client_id}"),
                    "\n",
                )
                # update the audit dictionary
                comptroller["amount"] = None
                comptroller["trx_hash"] = trx_hash
                comptroller["account_idx"] = account_idx
                comptroller["deposit_address"] = deposit_address
                # in subprocess listen for payment from client_id to gateway[idx]
                # upon receipt issue asset, else timeout
                listener = Thread(target=listener_boilerplate, args=(comptroller,),)
                listener.start()
                msg = "listener process started"
                chronicle(comptroller, msg)
                print(f"{network} listener process started", "\n")
            else:
                msg = "gateway overloaded"
                chronicle(comptroller, msg)
                response_body = json_dumps(
                    {
                        "response": "error",
                        "server_time": nonce,
                        "msg": f"oops! all {uia} gateway addresses are in use, "
                        + "please try again later",
                        "contact": contact(),
                    }
                )
        else:
            msg = "invalid uia"
            chronicle(comptroller, msg)
            response_body = json_dumps(
                {
                    "response": "error",
                    "server_time": nonce,
                    "msg": f"{uia} is an invalid gateway UIA, please try again",
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
    app = App()
    app.add_route(f"/{ROUTE}", GatewayDepositServer(comptroller))
    print(it("red", "INITIALIZING DEPOSIT SERVER\n"))
    # print(comptroller["offerings"], "\n")
    print("serving http at:", it("green", SERVER_URL))
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
