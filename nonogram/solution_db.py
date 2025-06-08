import sqlite3
from typing import Iterable
import datetime
import sys
import pathlib

from nonogram import data


class SolutionDb:
    def __init__(self, db_path: pathlib.Path):
        self.con = sqlite3.connect(db_path)
        self.con.execute(
            " ".join(
                [
                    "CREATE TABLE IF NOT EXISTS solves(",
                    "probability REAL,size INT,total INT,uniq INT,seconds REAL,",
                    "PRIMARY KEY (probability, size))",
                    "STRICT",
                ]
            )
        )

    def infer_config(self) -> tuple[data.SamplerConfig, int, int]:
        cur = self.con.cursor()

        res = cur.execute("SELECT DISTINCT size FROM solves")
        sizes = [s for (s,) in res.fetchall()]
        s_min = min(sizes)
        s_max = max(sizes)

        res = cur.execute("SELECT DISTINCT probability FROM solves")
        probs = set()
        for (res,) in res.fetchall():
            probs.add(res)
        best = None
        best_score = (sys.maxsize, sys.maxsize)
        for p_steps in range(3 * len(probs)):
            hypothesis = data.SamplerConfig(0.0, 1.0, p_steps, s_min, s_max)
            hyp_probs = set(hypothesis.all_probs())
            unmatched = probs - hyp_probs
            extra = hyp_probs - probs
            score = (len(unmatched), len(extra))
            if score < best_score:
                best = hypothesis
                best_score = score
        assert best is not None, "no data in database, infer_config failed"
        return best, best_score[0], best_score[1]

    def close(self):
        self.con.commit()
        self.con.close()

    def get_solution_count(self) -> int:
        cur = self.con.cursor()
        res = cur.execute("select sum(total) from solves")
        return res.fetchone()[0] or 0

    def get_total_runtime(self) -> datetime.timedelta:
        cur = self.con.cursor()
        res = cur.execute("select sum(seconds) from solves")
        s = res.fetchone()[0] or 0
        return datetime.timedelta(seconds=s)

    def add_solutions(
        self,
        solutions: Iterable[data.Solution],
    ):
        self.con.executemany(
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
            (
                {
                    "prob": s.config.prob,
                    "size": s.config.size,
                    "uniq": 1 if s.is_unique else 0,
                    "time": s.solve_time.total_seconds(),
                }
                for s in solutions
            ),
        )
        self.con.commit()

    def get_stats(self) -> dict[data.InstanceConfig, data.SolutionStatistics]:
        result: dict[data.InstanceConfig, data.SolutionStatistics] = {}
        cur = self.con.cursor()
        res = cur.execute("SELECT size, probability, uniq, total, seconds FROM solves")
        result = {}
        for size, probability, unique, total, seconds in res.fetchall():
            conf = data.InstanceConfig(size=size, prob=probability)
            d = data.SolutionStatistics(
                unique=unique, total=total, runtime=datetime.timedelta(seconds=seconds)
            )
            result[conf] = d
        return result
