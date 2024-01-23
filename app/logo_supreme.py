r"""
logo_flash.py

***
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
***

Copyright (C) 2021 squiddible and contributors
This project is licensed under the MIT license.
mit-license.org/ for more information.

font:
Calvin S www.patorjk.com/software/taag

sound track:
IOU - Freeez 1983
"""

# STANDARD PYTHON MODULES
import os
import time
from random import randint as rint

# BITSHARES GATEWAY MODULES
from config import logo_config, offerings
from utilities import it

AUDIO = logo_config()["audio"]
ANIMATE = logo_config()["animate"]

SPEED = 1.1

COLOR = [
    39,  # cursor
    117,  # border
    45,  # bitshares
    81,  # gateway
    159,  # network
]

ISSUE = [
    # left gateway
    [11, 10],
    [11, 11],
    [11, 12],
    [12, 12],
    [12, 11],
    [12, 10],
    [11, 10],
    [11, 11],
    [11, 12],
    # upper arrow
    [11, 14],
    [11, 15],
    [11, 16],
    [11, 17],
    # right gateway
    [11, 19],
    [11, 20],
    [11, 21],
    [12, 21],
    [12, 20],
    [12, 19],
    [11, 19],
    [11, 20],
    [11, 21],
]

PATHS = [
    # coin side
    [
        [[8, 6], [9, 7], [10, 8]],
        [[10, 6], [11, 7]],
        [[12, 6], [12, 7]],
        [[14, 6], [14, 7], [13, 8]],
    ],
    # UIA side
    [
        [[10, 22], [9, 23], [8, 24]],
        [[11, 23], [10, 24]],
        [[12, 23], [12, 24]],
        [[13, 22], [14, 23], [14, 24]],
    ],
]

COIN1 = [[8, 4], [8, 3], [8, 2], [9, 2], [9, 3], [9, 4]]

NOTES = {
    "D5": 576,
    "C5": 512,
    "D4": 288,
    "A5": 432,
    "REST": 0,
}

PLAYLIST = [
    (NOTES["D5"], 0.066),
    (NOTES["D5"], 0.066),
    (NOTES["D5"], 0.066),
    (NOTES["C5"], 0.066),
    (NOTES["D4"], 0.081),
    (NOTES["REST"], 0.225),
    (NOTES["D5"], 0.075),
    (NOTES["D5"], 0.081),
    (NOTES["D5"], 0.11),
    (NOTES["D4"], 0.135),
    (NOTES["A5"], 0.054),
    (NOTES["D5"], 0.066),
    (NOTES["REST"], 0.102),
]


def bell(duration, freq):
    """
    play the linux bell tone using:  'sudo apt install sox'
    """
    if not freq or not AUDIO:
        time.sleep(duration / SPEED)
    else:
        os.system(f"play -n -q -t  alsa synth {duration/SPEED} saw {freq} gain -35")


def logo_mat():
    """
    create a matrix from the block text string logo
    """
    inner_list = []
    final_list = []
    for char in __doc__.split("***")[1]:
        inner_list.append(char)
        if char == "\n":
            final_list.append(inner_list)
            inner_list = []

    return final_list


def uia_mat():
    """
    produce a list of coordinates for the right side uias
    """
    return [[[item[0] + i * 2, item[1] + 24] for item in COIN1[::-1]] for i in range(4)]


def coin_mat():
    """
    produce a list of coordinates for the left side coins
    """
    return [[[item[0] + i * 2, item[1]] for item in COIN1[::-1]] for i in range(4)]


def reserve_mat():
    """
    reverse the issue path to become a reserve path
    """
    return [
        (
            [ISSUE[::-1][i][0] + 1, ISSUE[::-1][i][1]]
            if i in range(9, 13)
            else [ISSUE[::-1][i][0], ISSUE[::-1][i][1]]
        )
        for i in range(22)
    ]


def text_only():
    """
    extract the text only of the logo
    """
    text = logo_mat()
    # text = text[2:8:1]
    final_text = ""
    for item in text:
        for index, char in enumerate(item):
            if 1 < index < 29:
                final_text += char
        final_text += "\n"

    for index, line in enumerate(final_text.split("\n")):
        if 2 <= index < 5:
            print(f"\033[{index+2};3H", end="")
            print(it(COLOR[2], line))
        if 5 <= index < 8:
            print(f"\033[{index+2};3H", end="")
            print(it(COLOR[3], line))
        if 8 <= index < 16:
            print(f"\033[{index+2};3H", end="")
            print(it(COLOR[4], line))
    print("\033[0m", end="")


def animate(note=0, coin_num=0, issuing=True):
    """
    turn the appropriate characters on and off to animate the logo
    """
    steps = [
        *COINS[coin_num][::-1],
        *PATHS[0][coin_num],
        *ISSUE,
        *PATHS[1][coin_num],
        *UIA[coin_num],
    ]
    if not issuing:
        steps = [
            *UIA[coin_num][::-1],
            *PATHS[1][coin_num][::-1],
            *RESERVE,
            *PATHS[0][coin_num][::-1],
            *COINS[coin_num],
        ]
    for position in steps:
        print(
            f"\033[{position[0]+2};{position[1]+1}H"
            + it(COLOR[0], LOGO_MAT[position[0]][position[1]], True)
        )
        print("\033[25;0H")
        bell(PLAYLIST[note][1], PLAYLIST[note][0])
        note += 1
        if note > 12:
            note = 0
        print(
            f"\033[0m\033[{position[0]+2};{position[1]+1}H"
            + it(COLOR[4], LOGO_MAT[position[0]][position[1]])
        )
        print("\033[25;0H")

    return note


def main():
    """
    animate the logo gateway paths with soundtrack
    """
    logo = it(COLOR[1], __doc__.split("***")[1])
    print("\033c")
    print(logo)
    text_only()
    print("\n")
    print(it("red", "OFFERINGS\n\n") + it(45, offerings()), "\n")
    print(it("red", "INITIALIZING PARACHAINS\n"))
    if ANIMATE:
        note = 0
        for _ in range(3):
            note = animate(note, rint(0, 3), rint(0, 1))
        print("\033[0m\033[2;0H" + logo + "\033[25;0H")
        text_only()
        print("\033[25;0H")
    else:
        # either way wait to allow parachains to initialize
        time.sleep(5)


def run():
    """
    main runner
    """
    global LOGO_MAT, RESERVE, COINS, UIA
    LOGO_MAT = logo_mat()
    RESERVE = reserve_mat()
    COINS = coin_mat()
    UIA = uia_mat()
    main()
