r"""
black_all.py
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

A simple script that blacks and pylints *.py files

http://pylint.pycqa.org/en/latest/
"""

# STANDARD PYTHON MODULES
import os
from time import time

# these can be safely ignored in most circumstances
DISABLE = (
    # too many?
    "too-many-statements",
    "too-many-locals",
    "too-many-branches",
    "too-many-function-args",
    "too-many-arguments",
    "too-many-nested-blocks",
    "too-many-lines",
    # improper exception handling
    "bare-except",
    "broad-except",
    # snake_case, etc.
    "invalid-name",
    # sometimes it just can't find the modules referenced - on this machine
    "import-error",
    # class minimums
    "too-few-public-methods",
    # suppression
    "suppressed-message",
    "locally-disabled",
    "useless-suppression",
    "useless-option-value",
)


def main():
    r"""
    \033c\nWelcome to lite Black Pylint Lite All! \n
    """
    print(main.__doc__)
    dispatch = {
        1: "Black Pylint Lite All!",
        2: "Black Pylint All!",
        3: "Pylint Lite All Only",
        4: "Pylint All Only",
        5: "Black All Only",
    }
    print("          Menu\n")
    for key, val in dispatch.items():
        print("         ", key, "  :  ", val)
    choice = input("\n\nInput Number or Press Enter for Choice 1\n\n  ")
    if choice == "":
        choice = 1
    choice = int(choice)
    disabled = ""
    if choice in [1, 3]:
        disabled = "--enable=all --disable="
        for item in DISABLE:
            disabled += item + ","
        disabled.rstrip(",")
    # Get the start time
    start = time()
    # Clear the screen
    print("\033c")
    # Get all of the python files in the current folder
    pythons = [f for f in os.listdir() + os.listdir("signing") if f.endswith(".py")]
    # pythons = [f for f in os.listdir() if f in ONLY]
    # For every file in that list:
    if choice in [1, 2, 5]:
        for name in pythons:
            # Print the script we are blacking.
            print("Blacking script:", name)
            # Black the script.
            os.system(f"black {name}")
            # Print a divider.
            print("-" * 100)
    if choice in [1, 2, 3, 4]:
        for name in pythons:
            # Print the script we are blacking.
            print("Pylinting script:", name)
            # Black the script.
            os.system(f"pylint {name} {disabled}")
            # Print a divider.
            print("-" * 100)
    os.system("isort *.py")
    # Say we are done.
    print("Done.")
    # Get the end time:
    end = time()
    # Find the time it took to black the scripts.
    took = end - start
    # Print that time.
    print(len(pythons), f"scripts took {took:1f} seconds.")


if __name__ == "__main__":
    main()
