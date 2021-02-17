r"""
decoder_ring.py
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

Wrapper for Pybitshares Memo ECDSA decoding
"""

# PYBITSHARES MODULES
from graphenebase import PrivateKey, PublicKey
from graphenebase.memo import decode_memo

# BITSHARES GATEWAY MODULES
from config import gateway_assets, issuing_chain


def ovaltine(memo, private_key):
    """
    Decode BitShares Transfer Memo
    """
    return (
        decode_memo(
            PrivateKey(private_key),  # associated with memo["to"] public key
            PublicKey(memo["from"], prefix=issuing_chain()["prefix"]),
            memo["nonce"],
            memo["message"],
        )
        .replace("\n", "")
        .replace(" ", "")
    )


def main(memo=None, private_key=None):
    """
    Sample memo to decode, should say "test"
    """
    if memo is None:
        memo = {
            "from": "BTS6upQe7xWa15Rj757Szygi8memj1PCGXugyC17WWZuKxkSJ1iW2",
            "to": "BTS7kFHKTgvVic1XqUBKRd4apAUwGqvLNpRuSR1DP4DkWDg64BLSG",
            "nonce": "407795228621064",
            "message": "9823e23c5c00e4880ce76d0aed5453de",
        }
    if private_key is None:
        private_key = gateway_assets()["eos"]["issuer_private"]
    print("memo:         ", memo)
    print("decoded memo: ", ovaltine(memo, private_key))


if __name__ == "__main__":

    main()
