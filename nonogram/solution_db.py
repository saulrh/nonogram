import sqlite3
import dataclasses
from typing import Iterable
import math

from nonogram import generate

DB_NAME = "data.sqlite3"


@dataclasses.dataclass
class Solution:
    config: generate.Configuration
    is_unique: bool
    runtime: float


class SolutionDb:
    def __init__(self):
        self.con = sqlite3.connect(DB_NAME)
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

    def infer_config(self) -> tuple[generate.Configuration, int, int]:
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
        best_score = (math.inf, math.inf)
        for p_steps in range(3 * len(probs)):
            hypothesis = generate.SampleConfig(0.0, 1.0, p_steps, s_min, s_max)
            hyp_probs = set(hypothesis.all_probs())
            unmatched = probs - hyp_probs
            extra = hyp_probs - probs
            score = (len(unmatched), len(extra))
            if score < best_score:
                best = hypothesis
                best_score = score
        return best, best_score[0], best_score[1]

    def close(self):
        self.con.commit()
        self.con.close()

    def get_solution_count(self) -> int:
        cur = self.con.cursor()
        res = cur.execute("select sum(total) from solves")
        return res.fetchone()[0] or 0

    def add_solutions(
        self,
        solns: Iterable[Solution],
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
                    "time": s.runtime,
                }
                for s in solns
            ),
        )

    def get_stats(self) -> dict[generate.Configuration, float]:
        result: dict[generate.Configuration, float] = {}
        cur = self.con.cursor()
        res = cur.execute(
            "SELECT size, probability, CAST(uniq AS REAL) / CAST(total AS REAL) FROM solves"
        )
        return {
            generate.Configuration(size=size, prob=probability): p_unique
            for size, probability, p_unique in res
        }
