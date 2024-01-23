from eosiopy.utils import type_name_to_long


class PackedTransaction(object):

    def __init__(self, eosio_params, chain_id):
        self.bytes_list = bytearray()

        self.chain_id = chain_id
        params = eosio_params
        self.push_int(params["expiration"] & 0xFFFFFFFF)
        self.push_short(params["ref_block_num"] & 0xFFFF)
        self.push_int(params["ref_block_prefix"] & 0xFFFFFFFF)
        self.push_variableUInt(params["max_net_usage_words"])
        self.push_variableUInt(params["max_kcpu_usage"])
        self.push_variableUInt(params["delay_sec"])
        self.push_actiones(list())  # TODO packfreedata
        self.push_actiones(params["transaction"]["actions"])
        self.push_variableUInt(0)  # TODO packexdata

    def push_base(self, val, iteration):
        for i in iteration:
            self.bytes_list.append(0xFF & val >> i)

    def push_short(self, val):
        self.push_base(val, range(0, 9, 8))

    def push_int(self, val):
        self.push_base(val, range(0, 25, 8))

    def push_long(self, val):
        self.push_base(val, range(0, 57, 8))

    def push_char(self, val):
        self.bytes_list.append(int(val))

    def push_variableUInt(self, val):
        b = int((val) & 0x7f)
        val = val >> 7
        b = b | (((val > 0) if 1 else 0) << 7)
        self.push_char(b)
        while val:
            b = int((val) & 0x7f)
            val = val >> 7
            b = b | (((val > 0) if 1 else 0) << 7)
            self.push_char(b)

    def push_actiones(self, val_list):
        self.push_variableUInt(len(val_list))
        for i in val_list:
            self.push_long(type_name_to_long(i["account"]))
            self.push_long(type_name_to_long(i["name"]))
            self.push_permission(i["authorization"])
            if i["data"]:
                self.push_data(i["data"])
            else:
                self.push_variableUInt(0)

    def push_permission(self, val_list):
        self.push_variableUInt(len(val_list))
        for i in val_list:
            self.push_long(type_name_to_long(i["actor"]))
            self.push_long(type_name_to_long(i["permission"]))

    def push_data(self, val):
        bytes = bytearray.fromhex(val)
        self.push_variableUInt(len(bytes))
        for i in bytes:
            self.bytes_list.append(i)

    def push_transaction_extensions(self, val_list):
        self.push_variableUInt(len(val_list))

    def get_digest_signature(self):
        byte_array = bytearray.fromhex(self.chain_id)
        byte_array.extend(self.bytes_list)
        free_array = bytearray([0 for n in range(32)])
        byte_array.extend(free_array)
        return byte_array
