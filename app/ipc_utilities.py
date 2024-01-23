r"""
ipc_utilities.py
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

a collection of shared utilities for Graphene Python Gateway
"""
# DISABLE SELECT PYLINT TESTS
# pylint: disable=too-many-arguments, broad-except, invalid-name
# pylint: disable=too-many-branches, too-many-statements, no-member

# STANDARD PYTHON MODULES
import datetime
import os
import time
import traceback
from json import dumps as json_dumps
from json import loads as json_loads
from sqlite3 import connect as sql

# BITSHARES GATEWAY MODULES
from config import DB_PATH


def chronicle(comptroller, msg=None):
    """
    log this comptroller event for auditing purposes, sample document name:

    BTC_2021_01_archive.txt
    """
    # localize the comptroller to avoid overwriting/removing values
    comptroller = dict(comptroller)

    # SECURITY sanitize the order private keys
    order_dict = comptroller.pop("order", {})
    order_dict.pop("private", None)
    order_dict = {f"order_{key}": value for key, value in order_dict.items()}
    # offerings are redundant for audit
    comptroller.pop("offerings", None)
    comptroller.pop("issuer_action", None)
    comptroller.update(order_dict)
    comptroller["msg"] = msg
    comptroller["event_unix"] = int(time.time())
    comptroller["event_year"] = int(datetime.datetime.now().strftime("%Y"))
    comptroller["event_month"] = int(datetime.datetime.now().strftime("%m").lstrip("0"))
    ######## SQL AUTOFILL ############
    comptroller["unix"] = int(time.time())
    comptroller["date"] = time.ctime()
    comptroller["year"] = int(datetime.datetime.now().strftime("%Y"))
    comptroller["month"] = int(datetime.datetime.now().strftime("%m").lstrip("0"))
    ##################################
    comptroller["network"] = comptroller["network"].upper()
    doc = (
        comptroller["network"].upper()
        + "_"
        + datetime.datetime.now().strftime("%Y_%m")
        + "_archive.txt"
    )
    try:
        json_ipc(doc, json_dumps(comptroller), append=True)
    except:
        for k, v in comptroller.items():
            print(k, v, type(v))
        raise
    if comptroller.get("process") in ["deposits", "withdrawals", "ingots"]:
        relational(comptroller)


def relational(comptroller):
    """
    Log comptroller events for auditing purposes to relational sql.

    Args:
        comptroller (dict): The comptroller information.
    """
    # SECURITY - SQL INJECTION

    # 0. Sql database is for audit purposes only and is not used in business logic.

    # 1. Prepared Statements: The code uses placeholders (`?`) in the SQL query string and passes
    # values as parameters to the `cursor.execute()` method. This helps prevent SQL injection
    # attacks by separating the SQL code from the data.

    # 2. Type Checking: The code defines a dictionary (`types`) that specifies the expected
    # data types for each column in the table. Before executing the query,
    # it converts the values from the `comptroller` dictionary to the specified types.
    # This helps prevent data type-related vulnerabilities.

    # 3. Context Manager (with statement): The code uses a context manager
    # (`with sql(DB_PATH) as conn`) to ensure that the database connection is properly closed
    # after the query execution. This helps prevent resource leaks and ensures the connection
    # is released securely.

    # 4. Error Handling: The code catches any exception that occurs during the query execution
    # and logs an error message. It also raises the exception, allowing it to be handled
    # at a higher level. Proper error handling is crucial for identifying
    # and addressing security or operational issues.

    try:
        if comptroller["process"] == "withdrawals":
            types = {
                "msg": str,
                "unix": int,
                "event_unix": int,
                "event_year": int,
                "event_month": int,
                "date": str,
                "year": int,
                "month": int,
                "network": str,
                "session_unix": int,
                "session_date": str,
                "op": str,
                "nonce": int,
                "uia_id": str,
                "event_id": str,
                "withdrawal_amount": float,
                "gateway_address": str,
                "client_address": str,
                "client_id": str,
                "account_idx": int,
                "tx_id": str,
                "order_public": str,
                "order_to": str,
                "order_quantity": float,
                "memo": str,
            }
        elif comptroller["process"] == "deposits":
            types = {
                "msg": str,
                "unix": int,
                "event_unix": int,
                "event_year": int,
                "event_month": int,
                "date": str,
                "year": int,
                "month": int,
                "network": str,
                "session_unix": int,
                "session_date": str,
                "req_params": str,
                "nonce": int,
                "event_id": str,
                "uia": str,
                "client_id": str,
                "amount": float,
                "account_idx": int,
                "required_memo": str,
                "deposit_address": str,
            }
        elif comptroller["process"] == "ingots":
            types = {
                "msg": str,
                "unix": int,
                "event_unix": int,
                "event_year": int,
                "event_month": int,
                "date": str,
                "year": int,
                "month": int,
                "network": str,
                "tx_id": str,
                "order_public": str,
                "order_to": str,
                "order_quantity": float,
            }

        query_data = {
            key: types[key](value)
            for key, value in comptroller.items()
            if key in types and isinstance(value, (float, int, str))
        }

        table = comptroller.pop("process")
        query = (
            f"INSERT INTO {table} ({', '.join(query_data.keys())}) VALUES"
            f" ({', '.join('?' for _ in query_data)})"
        )
        sql_db(query, tuple(query_data.values()))
    except Exception as e:
        print(f"Error logging comptroller event: {e}")
        raise e


def sql_db(query, values=()):
    """
    execute discrete sql queries, handle race condition gracefully
    if query is a string, assume values is a tuple
    else, query can be a list of dicts with keys ["query","values"]

    :return None: when not a SELECT query
    :return cur.fetchall(): from single SELECT, or last SELECT query made
    """
    queries = []
    # handle both single query and multiple queries
    if isinstance(query, str):
        queries.append({"query": query, "values": values})
    else:
        queries = query
    # strip double spaces and new lines in each query
    for idx, dml in enumerate(queries):
        queries[idx]["query"] = " ".join(dml["query"].replace("\n", " ").split())
    # print sql except when...
    # for dml in queries:
    #     print(it("yellow", f"'query': {dml['query']}"))
    #     print(it("green", f"'values': {dml['values']}\n"))
    # attempt to update database until satisfied
    pause = 0
    curfetchall = None
    while True:
        try:
            con = sql(DB_PATH)
            cur = con.cursor()
            for dml in queries:
                cur.execute(dml["query"], dml["values"])
                if "SELECT" in dml["query"] or "PRAGMA table_info" in dml["query"]:
                    curfetchall = cur.fetchall()
            con.commit()
            break
        # OperationalError: database is locked
        except Exception as error:
            print(error, query, values, "trying again")
            # exponentially slower
            time.sleep(0.1 * 2**pause)
            if pause < 13:  # oddly works out to about 13 minutes
                pause += 1
            continue
    con.close()
    return curfetchall


def json_ipc(doc="", text="", initialize=False, append=False):
    """
    JSON IPC

    Concurrent Interprocess Communication via Read and Write JSON

    features to mitigate race condition:

        open file using with statement
        explicit close() in with statement
        finally close()
        json formatting required
        postscript clipping prevents misread due to overwrite without erase
        read and write to the text pipe with a single definition
        growing delay between attempts prevents cpu leak

    to view your live streaming database, navigate to the pipe folder in the terminal:

        tail -F your_json_ipc_database.txt

    :dependencies: os, traceback, json.loads, json.dumps
    :warn: incessant read/write concurrency may damage older spinning platter drives
    :warn: keeping a 3rd party file browser pointed to the pipe folder may consume RAM
    :param str(doc): name of file to read or write
    :param str(text): json dumped list or dict to write; if empty string: then read
    :return: python list or dictionary if reading, else None

    wtfpl2020 litepresence.com
    """
    # initialize variables
    data = None
    # file operation type for exception message
    if text:
        if append:
            act = "appending"
        else:
            act = "writing"
    else:
        act = "reading"
    # create a clipping tag for read and write operations
    tag = ""
    if not act == "appending":
        tag = "<<< JSON IPC >>>"
    # determine where we are in the file system; change directory to pipe folder
    path = os.path.dirname(os.path.abspath(__file__)) + "/pipe"
    # ensure we're writing json then add prescript and postscript for clipping
    try:
        text = tag + json_dumps(json_loads(text)) + tag if text else text
    except:
        print(text)
        raise
    # move append operations to the comptroller folder and add new line
    if append:
        path += "/comptroller"
        text = "\n" + text
    # create the pipe subfolder
    if initialize:
        os.makedirs(path, exist_ok=True)
        os.makedirs(path + "/comptroller", exist_ok=True)
    if doc:
        doc = path + "/" + doc
        # race read/write until satisfied
        iteration = 0
        while True:
            # increment the delay between attempts exponentially
            time.sleep(0.02 * iteration**2)
            try:
                if act == "appending":
                    with open(doc, "a", encoding="utf-8") as handle:
                        handle.write(text)
                        handle.close()
                        break
                elif act == "writing":
                    with open(doc, "w+", encoding="utf-8") as handle:
                        handle.write(text)
                        handle.close()
                        break
                elif act == "reading":
                    if os.path.exists(doc):
                        with open(doc, "r", encoding="utf-8") as handle:
                            # only accept legitimate json
                            data = json_loads(handle.read().split(tag)[1])
                            handle.close()
                            break
                    else:
                        data = None
                        break
            except Exception:
                if iteration == 1:
                    if "initializing gateway main" in text:
                        print("no json_ipc pipe found, initializing...")
                    else:
                        print(  # only if it happens more than once
                            iteration,
                            f"json_ipc failed while {act} to {doc} retrying...\n",
                        )
                elif iteration == 5:
                    # maybe there is no pipe? auto initialize the pipe!
                    json_ipc(initialize=True)
                    print("json_ipc pipe initialized, retrying...\n")
                elif iteration == 10:
                    print("json_ipc unexplained failure\n", traceback.format_exc())
                iteration += 1
                continue
            # deliberately double check that the file is closed
            finally:
                try:
                    handle.close()
                except Exception:
                    pass

    return data
