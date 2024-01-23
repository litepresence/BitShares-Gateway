r"""
config.py

  ____  _ _   ____  _                         
 | __ )(_) |_/ ___|| |__   __ _ _ __ ___  ___ 
 |  _ \| | __\___ \| '_ \ / _` | '__/ _ \/ __|
 | |_) | | |_ ___) | | | | (_| | | |  __/\__ \
 |____/|_|\__|____/|_| |_|\__,_|_|  \___||___/
       ____  _             _                  
      / ___|(_) __ _ _ __ (_)_ __   __ _      
      \___ \| |/ _` | '_ \| | '_ \ / _` |     
       ___) | | (_| | | | | | | | | (_| |     
      |____/|_|\__, |_| |_|_|_| |_|\__, |     
               |___/               |___/      


WTFPL litepresence.com Dec 2021 & squidKid-deluxe Jan 2024

USER CONTROLS

"""

# timeout during websocket handshake; default 4 seconds
HANDSHAKE_TIMEOUT = 4
# multiprocessing handler lifespan, default 20 seconds
PROCESS_TIMEOUT = 20
# default False for persistent limit orders
KILL_OR_FILL = False
# default True scales elements of oversize gross order to means
AUTOSCALE = True
# default True to never spend last 2 bitshares
CORE_FEES = True
# multiprocessing incarnations, default 3 attempts
ATTEMPTS = 3
# prevent extreme number of AI generated edicts; default 20
LIMIT = 20
# default True to execute order in primary script process
JOIN = True
# ignore orders value less than ~X bitshares; 0 to disable
DUST = 0
# True = heavy print output
DEV = False
# Application version
VERSION = "1.0.0"
# Node list bitshares
NODES = [
    "wss://api.bts.mobi/wss",
    "wss://api-us.61bts.com/wss",
    "wss://cloud.xbts.io/ws",
    "wss://api.dex.trading/wss",
    "wss://eu.nodes.bitshares.ws/ws",
    "wss://api.pindd.club/ws",
    "wss://dex.iobanker.com/ws",
    "wss://public.xbts.io/ws",
    "wss://node.xbts.io/ws",
    "wss://node.market.rudex.org/ws",
    "wss://nexus01.co.uk/ws",
    "wss://api-bts.liondani.com/ws",
    "wss://api.bitshares.bhuz.info/wss",
    "wss://btsws.roelandp.nl/ws",
    "wss://hongkong.bitshares.im/ws",
    "wss://node1.deex.exchange/wss",
    "wss://api.cnvote.vip:888/wss",
    "wss://bts.open.icowallet.net/ws",
    "wss://api.weaccount.cn/ws",
    "wss://api.61bts.com",
    "wss://api.btsgo.net/ws",
    "wss://bitshares.bts123.cc:15138/wss",
    "wss://singapore.bitshares.im/wss",
]

# BitShares Mainnet
ID = "4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8"
PREFIX = "BTS"
