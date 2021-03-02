import time
from random import choice
from collections import Counter
from config import offerings
import requests
from utilities import it
from threading import Thread


calls = []
iteration = 0
while True:
    iteration += 1
    network = choice(["EOS", "XRP"])
    calls.append(network)
    rpc = (
        "http://localhost:4018/gateway?"
        +f"uia_name=GATEWAY.{network}&client_id=1.2.25634"
    )
    requests.get(rpc)
    print(it("red", f"\nTotal: {len(calls)} - {Counter(calls)}\n"))

