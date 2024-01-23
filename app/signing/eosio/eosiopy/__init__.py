from .config import eosio_config
from .eosioparams import EosioParams
from .nodenetwork import NodeNetwork
from .rawinputparams import RawinputParams
from .sign import sign

VERSION = (0, 1, 4)

__version__ = VERSION
__versionstr__ = '.'.join(map(str, VERSION))

__all__ = ['VERSION', 'config', 'eosioparams', 'nodenetwork', 'packedtransaction',
           'rawinputparams', 'sign', 'utils']

# from eosiopy import eosio_config, RawinputParams, EosioParams, NodeNetwork
#
# eosio_config.url="http://127.0.0.1"
# eosio_config.port=8888
# raw = RawinputParams("newaccount", {"creator":"eosio","name":"aeztcnjmhege","owner":{"threshold":1,"keys":[{"key":"EOS5XhYEWPJH2P77rh6dwMURsgjFodjXqTadSf1tNZAHVhnBpWyNu","weight":1}],"accounts":[],"waits":[]},"active":{"threshold":1,"keys":[{"key":"EOS7EZgfh13yVxaXuzH12cC2Yru7Wv1JNNNbxnSdZQXNX2hWAyBTm","weight":1}],"accounts":[],"waits":[]}}, "eosio", "eosio@active")
# eosiop_arams=EosioParams(raw.params_actions_list,"5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3")
# net=NodeNetwork.push_transaction(eosiop_arams.trx_json)
# print(net)
