from eosiopy.eosioparams import EosioParams
from eosiopy.exception import ErrInputParams
from eosiopy.nodenetwork import NodeNetwork


class RawinputParams(object):

    def __init__(self, action=None, args=None, code=None, authorization=None):
        self.params_actions_list=list()
        if action and args and code and authorization:
            self.add(action, args, code, authorization)

    def add(self, action, args, code, authorization):
        raw_params = dict()
        raw_params["action"] = action
        raw_params["args"] = args
        raw_params["code"] = code

        try:
            actor = authorization.split("@")[0]
            permission = authorization.split("@")[1]
        except:
            raise ErrInputParams()
        _action_obj = {
            "account": code,
            "authorization": [
                {
                    "actor": actor,
                    "permission": permission
                }
            ],
            "data": self.get_bin(raw_params),
            "name": action
        }
        self.params_actions_list.append(_action_obj)
        return self

    def get_bin(self, json_data):
        return NodeNetwork.json_to_abi(json_data=json_data)["binargs"]






if __name__ == "__main__":
    raw = RawinputParams("transfer", {
        "from": "eosio.token",
        "memo": "dd",
        "quantity": "20.0000 EOS",
        "to": "eosio"
    }, "eosio.token", "eosio.token@active")
    param=EosioParams(raw.params_actions_list)
    print(raw.params_actions_list)

