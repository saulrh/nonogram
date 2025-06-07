#!/usr/bin/env bash

echo "Number of configurations:"
sqlite3 --readonly data.sqlite3 "SELECT COUNT(*) FROM solves"
echo "Total number of solves:"
sqlite3 --readonly data.sqlite3 "SELECT SUM(solves.total) FROM solves"
echo "Core-hours spent solving:"
sqlite3 --readonly data.sqlite3 "SELECT SUM(solves.seconds) / 3600.0 FROM solves"

