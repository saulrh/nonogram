import sqlite3
import csv

con = sqlite3.connect("data.sqlite3")
cur = con.cursor()

with open("data.csv") as data_f:
    reader = csv.DictReader(data_f)
    for row in reader:
        cur.execute(
            " ".join(
                [
                    "INSERT INTO solves",
                    "VALUES(:prob, :size, :total, :uniq, :time)",
                    "ON CONFLICT DO",
                    "UPDATE SET",
                    "total = total + :total,uniq = uniq + :uniq,",
                    "seconds = seconds + :time",
                ]
            ),
            {
                "prob": float(row["p_filled"]),
                "size": int(row["size"]),
                "total": 1000,
                "uniq": int(1000 * float(row["p_unique"])),
                "time": float(row["seconds"]) * 1000.0,
            },
        )
        con.commit()
