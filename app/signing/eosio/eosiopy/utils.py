import json
from collections import namedtuple

from eosiopy.config import eosio_config


def _json_object_hook(d):
    return namedtuple('X', d.keys())(*d.values())


def json2obj(data):
    return json.loads(data, object_hook=_json_object_hook)


def char_to_symbol(c):
    if (ord(c) >= ord('a') and ord(c) <= ord('z')):
        return chr(((ord(c) - ord('a')) + 6))

    if (ord(c) >= ord('1') and ord(c) <= ord('5')):
        return chr(((ord(c) - ord('1')) + 1))
    return chr(0)


def type_name_to_long(type_name):
    if type_name == None or type_name == "":
        return 0
    c = 0
    value = 0
    type_name_len = len(type_name)
    for i in range(eosio_config.MAX_NAME_IDX + 1):
        if (i < type_name_len and i <= eosio_config.MAX_NAME_IDX):
            c = ord(char_to_symbol(type_name[i]))
        if (i < eosio_config.MAX_NAME_IDX):
            c &= 0x1f
            c <<= 64 - 5 * (i + 1)
        else:
            c &= 0x0f
        value |= c
    return value
