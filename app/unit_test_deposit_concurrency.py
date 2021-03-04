import time
from random import choice
from collections import Counter
from config import offerings
import requests
from utilities import it
from threading import Thread


def make_call(rpc):

    requests.get(rpc)

threads={}
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

    threads[iteration] = Thread(target=make_call, args=(rpc,))
    threads[iteration].start()
    #time.sleep(0.1)
    
    print(it("red", f"\nTotal: {len(calls)} - {Counter(calls)}\n"))
    if iteration == 50:
        break

