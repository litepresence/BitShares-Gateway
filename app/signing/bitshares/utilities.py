r"""
utilities.py

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

UTILITIES

"""

# DISABLE SELECT PYLINT TESTS
# pylint: disable=invalid-name

import os
import sys
from calendar import timegm
from datetime import datetime
from time import strptime
from traceback import format_exc

# ISO8601 timeformat; 'graphene time'
ISO8601 = "%Y-%m-%dT%H:%M:%S%Z"


def disable_print():
    """
    temporarily disable printing
    """
    sys.stdout = open(os.devnull, "w")


def enable_print():
    """
    re-enable printing
    """
    sys.stdout = sys.__stdout__


def trace(error):
    """
    print stack trace upon exception
    """
    msg = str(type(error).__name__) + "\n"
    msg += str(error.args) + "\n"
    msg += str(format_exc()) + "\n"
    print(msg)


def it(style, text):
    """
    Text coloring
    """
    emphasis = {
        "red": 91,
        "green": 92,
        "yellow": 93,
        "blue": 94,
        "purple": 95,
        "cyan": 96,
    }

    return ("\033[%sm" % emphasis[style]) + str(text) + "\033[0m"


def to_iso_date(unix):
    """
    returns iso8601 datetime given unix epoch
    """
    return datetime.utcfromtimestamp(int(unix)).isoformat()


def from_iso_date(iso):
    """
    returns unix epoch given iso8601 datetime
    """
    return int(timegm(strptime((iso + "UTC"), ISO8601)))
