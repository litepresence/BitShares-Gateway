r"""
  ____    _  _____  _    ____    _    ____  _____ 
 |  _ \  / \|_   _|/ \  | __ )  / \  / ___|| ____|
 | | | |/ _ \ | | / _ \ |  _ \ / _ \ \___ \|  _|  
 | |_| / ___ \| |/ ___ \| |_) / ___ \ ___) | |___ 
 |____/_/   \_\_/_/   \_\____/_/   \_\____/|_____|

***
  _______  ______  _     ___  ____  _____ ____  
 | ____\ \/ /  _ \| |   / _ \|  _ \| ____|  _ \ 
 |  _|  \  /| |_) | |  | | | | |_) |  _| | |_) |
 | |___ /  \|  __/| |__| |_| |  _ <| |___|  _ < 
 |_____/_/\_\_|   |_____\___/|_| \_\_____|_| \_\

"""
import os
import sys
import termios

# STANDARD PYTHON MODULES
import time
import tty
from typing import Dict, List

from ipc_utilities import sql_db

# BITSHARES GATEWAY MODULES
from utilities import at, it
from utilities import logo as gateway_logo

# Strip logo out of script docstring
EXPLORER_LOGO = __doc__.strip("\n").split("***")


def center_at(where: int, text: str) -> str:
    """
    Center-align text within a specified width.
    """
    return "\n".join([i.center(where * 2) for i in text.split("\n")])


def custom_center(string: str, length: int, width: int, fillchar: str = " ") -> str:
    """
    Center-align a string within a specified width.

    Parameters:
    - string: The string to be centered.
    - width: The total width of the output string.
    - fillchar: (optional) The character used for padding. Default is space (' ').

    Returns:
    - Center-aligned string.
    """
    if length >= width:
        return string

    left_padding = (width - length) // 2
    right_padding = width - length - left_padding

    centered_string = fillchar * left_padding + string + fillchar * right_padding
    return centered_string


def get_table_data(
    columns: Dict[str, List[str]], tables: List[str]
) -> Dict[str, List[str]]:
    """
    Get data from tables.

    Parameters:
    - columns: Dictionary of table columns.
    - tables: List of table names.

    Returns:
    - Dictionary containing table data.
    """
    return {
        table: sql_db(
            f"SELECT {', '.join(columns[table])} FROM {table} ORDER BY id DESC"
        )
        for table in tables
    }


def get_table_columns(table: str) -> List[str]:
    """
    Get columns of a table.

    Parameters:
    - table: Table name.

    Returns:
    - List of table columns.
    """
    query = f"PRAGMA table_info ({table})"
    columns = [
        i[1]
        for i in sql_db(query)
        if i[1]
        not in [
            "month",
            "unix",
            "event_year",
            "event_month",
            "year",
            "session_date",
            "session_unix",
            "id",
            "req_params",
        ]
    ]
    return columns


def read_table(
    table: str, columns: List[str], curfetchall: List[str], term_size: List[int]
) -> bool:
    """
    Print the contents of a table.

    Parameters:
    - table: Table name.
    - columns: List of table columns.
    - curfetchall: List of fetched data.
    - term_size: Terminal size.

    Returns:
    - True if any entry is highlighted, False otherwise.
    """
    curfetchall = [
        i
        for i in curfetchall
        if time.time() - i[columns.index("event_unix")] < 60 * 60 * 24 * 60
    ]

    col_sizes = [
        max(map(len, [str(i[idx]) for i in curfetchall] + [col])) + 2
        for idx, col in enumerate(columns)
    ]

    table_label = "=" * 30 + f"   {table} table   ".upper() + "=" * 30

    text = it("blue", table_label.center(term_size[0])) + "\n\n"
    highlighted = False
    if curfetchall:
        header = ""
        for idx, col in list(enumerate(columns))[1:]:
            header += str(col).ljust(col_sizes[idx]).upper()
        text += it("green", header.center(term_size[0])) + "\n\n"
        for row in curfetchall:
            data = ""
            escape_len = 0
            for idx, val in list(enumerate(row))[1:]:
                if (
                    columns[idx] == "date"
                    and time.time() - row[columns.index("event_unix")] < 5 * 60
                ):
                    highlighted = True
                    nval = it("orange", str(val).ljust(col_sizes[idx]))
                else:
                    nval = it("gray", str(val).ljust(col_sizes[idx]))
                data += nval
                escape_len += len(nval) - len(str(val).ljust(col_sizes[idx]))
            text += (
                custom_center(
                    row[0], len(header) + escape_len, term_size[0] + escape_len
                )
                + "\n"
            )
            text += (
                custom_center(data, len(header) + escape_len, term_size[0] + escape_len)
                + "\n"
            )
    text += "\n\n"
    print(text)
    return highlighted


def print_message(color: int, message: str, term_size: List[int]) -> None:
    """
    Print a message with a specified color.
    """
    print(it(color, message.center(term_size[0])))


def print_table_header(
    color: int, columns: List[str], col_sizes: List[int], term_size: List[int]
) -> None:
    """
    Print the header of a table with a specified color.
    """
    header = "".join(
        it(color, col.ljust(col_size).upper())
        for col, col_size in zip(columns, col_sizes)
    )
    print(header.center(term_size[0]) + "\n\n")


def logo(term_size: List[int]) -> None:
    """
    Display the gateway logo.
    """
    padded_logo = "\n".join(
        [
            i.center(term_size[0])
            for i in gateway_logo().strip("\n ").replace("\n    ", "\n").split("\n")
        ]
    )
    print("\033c")
    print(it("yellow", padded_logo))
    if term_size[0] > 160:
        print(
            it(
                "cyan",
                at(
                    [
                        (
                            ((term_size[0] - 50) // 2)
                            - len(EXPLORER_LOGO[0].split("\n")[0])
                        )
                        // 2,
                        7,
                    ],
                    EXPLORER_LOGO[0],
                ),
            )
        )
        print(
            it(
                "cyan",
                at(
                    [
                        (
                            ((term_size[0] - 50) // 2)
                            - len(EXPLORER_LOGO[1].split("\n")[0])
                        )
                        // 2
                        + (term_size[0] - 50) // 2
                        + 30,
                        6,
                    ],
                    EXPLORER_LOGO[1],
                ),
            )
        )
    else:
        print()
        print(it("cyan", center_at(term_size[0] // 2, EXPLORER_LOGO[0])))
        print(it("cyan", center_at(term_size[0] // 2, EXPLORER_LOGO[1])))
        print()


def main(tables: List[str]) -> None:
    """
    Display database in a human-readable manner.
    """
    pterm_size = os.get_terminal_size()
    columns = {table: get_table_columns(table) for table in tables}
    prev_table_data = get_table_data(columns, tables)
    try:
        while True:
            term_size = os.get_terminal_size()
            logo(term_size)

            print_message("purple", f"LAST UPDATED: {time.ctime().upper()}", term_size)
            print_message("orange", "Ctrl + C to exit to menu", term_size)
            print("\n")

            table_data = get_table_data(columns, tables)

            highlight = any(
                [
                    read_table(table, columns[table], table_data[table], term_size)
                    for table in tables
                ]
            )
            print("\033[H")
            start = time.time()

            i = 0
            while True:
                i += 1
                if (
                    (highlight and (time.time() - start > 30))
                    or (term_size != pterm_size)
                    or (table_data != prev_table_data)
                ):
                    break
                if not i % 20:
                    table_data = get_table_data(columns, tables)
                term_size = os.get_terminal_size()
                time.sleep(0.1)

            pterm_size = term_size
            prev_table_data = table_data
    except KeyboardInterrupt:
        return


def menu() -> None:
    """
    Display menu for table selection.
    """
    try:
        while True:
            term_size = os.get_terminal_size()
            logo(term_size)
            print(it(82, "=" * term_size[0]))
            print("\n\n")
            print_message("orange", "Ctrl + C to exit", term_size)
            print(
                "Choose which tables you wish to view: (press 1-3 to toggle, enter to"
                " confirm)\n\n\n\n"
            )

            tables = ["withdrawals", "deposits", "ingots"]
            selected = [0, 0, 0]
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                while True:
                    print(
                        "\033[2F\033[2K"
                        + "".join(
                            it(
                                240 if selected[idx] else 232,
                                i.ljust(15),
                                foreground=False,
                            )
                            for idx, i in enumerate(tables)
                        )
                        + "\n"
                    )
                    char = sys.stdin.read(1)
                    if char == "\n":
                        break
                    if char.isdigit() and 0 < (char := int(char)) < 4:
                        selected[int(char) - 1] = not selected[int(char) - 1]
                    time.sleep(0.01)
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            main([i for idx, i in enumerate(tables) if selected[idx]])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    menu()
