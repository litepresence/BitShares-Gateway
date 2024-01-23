import ctypes
import hashlib
from ctypes import *

import base58
import pkg_resources

from eosiopy.exception import CantFindRecId, CantFindResInPack
from eosiopy.exception import IllegalKey


def get_res_path(name):
    for i in pkg_resources.resource_listdir(__name__, "../"):
        if i.find(name) >= 0:
            return i


def get_private_ket_by_wif(wif):
    eos_byte_array = bytearray(base58.b58decode(wif))
    if eos_byte_array[0] != 0x80:
        raise IllegalKey()
    hex_bytea_array = eos_byte_array[1:33]
    return hex_bytea_array


def sign(wfi, trx):
    pri = get_private_ket_by_wif(wfi)
    sha = hashlib.sha256(trx)
    trx = sha.digest()
    pri = bytes(pri)
    ll = ctypes.cdll.LoadLibrary
    try:
        if get_res_path("uECC"):
            libuecc = pkg_resources.resource_filename(__name__, "../" + get_res_path("uECC.cpython"))
        else:
            raise CantFindResInPack
    except:
        libuecc = './uECC.so'

    libuecc = ll(libuecc)
    c_uint_array = c_uint8 * 64
    c_uint_array32 = c_uint8 * 32
    signature = c_uint_array(0)
    c_trx = c_uint_array32(0)
    c_pri = c_uint_array32(0)
    for i in range(32):
        c_trx[i] = trx[i]
        c_pri[i] = pri[i]

    recId = libuecc.uECC_sign_forbc(c_pri, c_trx, signature)
    if recId == -1:
        raise CantFindRecId
    bin = bytearray()
    binlen = 65 + 4
    headerBytes = recId + 27 + 4
    bin.append(headerBytes)
    bin.extend(bytearray(signature))
    temp = bytearray()
    temp.extend(bin[0:65])
    temp.append(75)
    temp.append(49)
    rmd160 = hashlib.new("rmd160")
    rmd160.update(temp)
    bin.extend(rmd160.digest())
    sig = str(base58.b58encode(bytes(bin)))[2:-1]
    sig = "SIG_K1_" + sig
    return sig
