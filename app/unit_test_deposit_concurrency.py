"""
Attack the local host to test software resiliance
"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=redefined-outer-name, missing-timeout
# STANDARD MODULES
import time
from collections import Counter
from random import choice
from threading import Thread

# THIRD PARTY MODULES
import requests

from config import server_config

# GATEWAY MODULES
from utilities import it


def make_call(rpc):
    """
    Wrap requests.get so we can thread it
    """
    for _ in range(10):
        requests.get(rpc)


def main() -> None:
    """
    Attack the local host to test software resiliance
    """
    threads = {}
    calls = []
    iteration = 0
    while True:
        iteration += 1
        network = choice(["XYZ"])
        calls.append(network)
        rpc = (
            f"http://localhost:{server_config()['port']}/gateway?uia_name=GATEWAY.{network}"
            "&client_id=1.2.25634&amount=10&memo="
        )

        threads[iteration] = Thread(target=make_call, args=(rpc,))
        threads[iteration].start()
        time.sleep(0.1)

        print(it("red", f"\nTotal: {len(calls)} - {Counter(calls)}\n"))
        if iteration == 50:
            break


if __name__ == "__main__":
    main()
