import json
import time

from eosiopy import eosio_config
from eosiopy.nodenetwork import NodeNetwork
from eosiopy.packedtransaction import PackedTransaction
from eosiopy.sign import sign


class EosioParams(object):
    def __init__(self, params_actions_list, wif=None):
        self.get_info_block()
        self.params = dict()

        # actions = list()
        # actions.append(params_dict)
        tmp_dict = dict()
        tmp_dict["actions"] = params_actions_list

        self.params.setdefault("transaction", tmp_dict)
        self.params.setdefault("ref_block_num", self.info_block["last_irreversible_block_num"])
        self.params.setdefault("ref_block_prefix", self.info_block["ref_block_prefix"])
        self.params.setdefault("delay_sec", 0)
        self.params.setdefault("max_kcpu_usage", 0)
        self.params.setdefault("max_net_usage_words", 0)
        self.params.setdefault("expiration", self.get_expiration())
        self.params.setdefault("signatures", list())
        p = json.dumps(self.params)
        self.packed()
        if wif:
            self.sign(wif)

    def get_info_block(self):
        self.info_block = NodeNetwork.get_info_block()

    def get_expiration(self):
        return int(time.time() + eosio_config.expiration)

    def packed(self):
        self.params["packed_trx"] = PackedTransaction(self.params, self.info_block["chain_id"])

    def sign(self, wif):
        signatures = list()
        signatures.append(sign(wif, self.params["packed_trx"].get_digest_signature()))
        self.params["signatures"] = signatures

    @property
    def trx_json(self):
        data = dict()
        data["compression"] = "none"
        data["packed_context_free_data"] = "00"
        data["packed_trx"] = self.params["packed_trx"].bytes_list.hex()
        data["signatures"] = self.params["signatures"]
        return data
