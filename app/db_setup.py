r"""
db_setup.py
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

Create an Empty Database with Correct Schema
"""

# STANDARD MODULES
import os
import time
from subprocess import call
from sys import version as python_version
from typing import List

# GATEWAY MODULES
from config import DB_PATH
from ipc_utilities import sql_db
from utilities import it

# GLOBAL CONSTANTS
PATH: str = os.path.dirname(os.path.abspath(__file__)) + "/database"


def reset_database() -> None:
    """
    Delete any existing database and initialize a new SQL database.

    :return: None
    """
    # Ensure the correct Python version
    if float(".".join(python_version.split(".")[:2])) < 3.8:
        raise AssertionError("Bitshares Gateway Requires Python 3.8+")

    # Create the database folder
    os.makedirs(PATH, exist_ok=True)

    # User input with warning
    print("\033c")
    print(
        it("red", "WARNING: THIS SCRIPT WILL RESTART THE DATABASE AND ERASE ALL DATA\n")
    )
    choice: str = input(
        "Erase database? Enter 'y' + Enter to continue or Enter to cancel\n"
    )

    # Erase and recreate the database
    if choice == "y":
        # FIXME: Back up instead of remove
        command: str = (
            f"mv {DB_PATH} {DB_PATH.split('.', maxsplit=1)[0]}_{int(time.time())}.db"
        )
        print("\033c", it("red", command), "\n")
        call(command.split())
        print("Creating SQLite3:", it("green", DB_PATH), "\n")

        # Batch database creation queries and process atomically
        queries: List[dict] = []

        # Withdrawal table
        query = """
            CREATE TABLE withdrawals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg TEXT,
                unix INTEGER,
                event_unix INTEGER,
                event_year INTEGER,
                event_month INTEGER,
                date TEXT,
                year INTEGER,
                month INTEGER,
                network TEXT,
                session_unix INTEGER,
                session_date TEXT,
                op TEXT,
                nonce INT,
                uia_id TEXT,
                event_id TEXT,
                withdrawal_amount REAL,
                gateway_address TEXT,
                client_address TEXT,
                client_id TEXT,
                account_idx INTEGER,
                tx_id TEXT,
                order_public TEXT,
                order_to TEXT,
                order_quantity REAL,
                memo TEXT
            );
        """
        print(query)
        dml = {"query": query, "values": ()}
        queries.append(dml)

        # Deposits table
        query = """
            CREATE TABLE deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg TEXT,
                unix INTEGER,
                event_unix INTEGER,
                event_year INTEGER,
                event_month INTEGER,
                date TEXT,
                year INTEGER,
                month INTEGER,
                network TEXT,
                session_unix INTEGER,
                session_date TEXT,
                req_params TEXT,
                nonce INTEGER,
                event_id TEXT,
                uia TEXT,
                client_id TEXT,
                amount REAL,
                account_idx INTEGER,
                required_memo TEXT,
                deposit_address TEXT
            );
        """
        print(query)
        dml = {"query": query, "values": ()}
        queries.append(dml)

        # Ingots table
        query = """
            CREATE TABLE ingots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                msg TEXT,
                unix INTEGER,
                event_unix INTEGER,
                event_year INTEGER,
                event_month INTEGER,
                date TEXT DEFAULT(getdate()),
                year INTEGER,
                month INTEGER,
                network TEXT,
                tx_id TEXT,
                order_public TEXT,
                order_to TEXT,
                order_quantity REAL
            );
        """
        print(query)
        dml = {"query": query, "values": ()}
        queries.append(dml)
        sql_db(queries)

        # Display the tables' info
        query = """
            PRAGMA table_info (withdrawals)
        """
        for col in sql_db(query):
            print(col)

        query = """
            PRAGMA table_info (deposits)
        """
        for col in sql_db(query):
            print(col)

        query = """
            PRAGMA table_info (ingots)
        """
        for col in sql_db(query):
            print(col)


if __name__ == "__main__":
    reset_database()
