"""
Testing conversion of the HETUS data into an sqlite database and working with that.
"""

import load_data as load_data

import sqlite3
import sqlalchemy


def setup_table():
    con = sqlite3.connect("hetus.db")
    cur = con.cursor()

    data = load_data.load_hetus_file("DE")

    colums = ",".join(data.columns)
    cur.execute(f"CREATE TABLE if not exists hetus({colums})")

    d = list(data.itertuples(index=False))
    paramstring = ",".join("?" * len(d[0]))
    cur.executemany(f"insert into hetus values({paramstring})", d)
    con.commit()


con = sqlite3.connect("hetus.db")
cur = con.cursor()

# cur.execute("SELECT TOP 1 HHC1 FROM hetus GROUPBY COUNTRY, HID ")
