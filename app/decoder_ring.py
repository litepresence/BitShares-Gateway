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

# STANDARD MODULES
from typing import Dict, Optional

# BITSHARES GATEWAY MODULES
from config import gateway_assets, issuing_chain
# PYBITSHARES MODULES
from signing.bitshares.graphene_signing import PrivateKey, PublicKey
from signing.bitshares.memo import decode_memo


def ovaltine(memo: Dict[str, str], private_key: str) -> str:
    """
    Decode a BitShares transfer memo.

    :param memo: Memo information including "from," "to," "nonce," and "message" fields.
    :param private_key: Private key associated with the memo "to" public key.

    :return: Decoded memo.
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


def main(memo: Optional[Dict[str, str]] = None, private_key: Optional[str] = None) -> None:
    """
    Sample memo decoding. If no memo or private key is provided,
    it uses default values for demonstration.

    :param memo: Memo information including "from," "to," "nonce," and "message" fields.
    :param private_key: Private key associated with the memo "to" public key.

    :return: None
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
