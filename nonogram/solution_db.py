import sqlite3
import contextlib

DB_NAME = "data.sqlite3"


def _get():
    return contextlib.closing(sqlite3.connect(DB_NAME, autocommit=True))


def init():
    with _get() as con:
        con.execute(
            " ".join(
                [
                    "CREATE TABLE IF NOT EXISTS solves(",
                    "probability REAL,size REAL,total INT,uniq INT,seconds REAL,",
                    "PRIMARY KEY (probability, size))",
                    "STRICT",
                ]
            )
        )


def get_solution_count():
    with _get() as con:
        cur = con.cursor()
        res = cur.execute("select sum(total) from solves")
        return res.fetchone()[0]


def add_solution(prob, size, uniq, runtime):
    with _get() as con:
        con.execute(
            " ".join(
                [
                    "INSERT INTO solves",
                    "VALUES(:prob, :size, 1, :uniq, :time)",
                    "ON CONFLICT DO",
                    "UPDATE SET",
                    "total = total + 1,uniq = uniq + :uniq,",
                    "seconds = seconds + :time",
                ]
            ),
            {
                "prob": prob,
                "size": size,
                "uniq": 1 if uniq else 0,
                "time": runtime,
            },
        )


def get_stats():
    with _get() as con:
        cur = con.cursor()
        res = cur.execute(
            "SELECT size, probability, CAST(uniq AS REAL) / CAST(total AS REAL) FROM solves"
        )
        for size, probability, p_unique in res:
            pass
