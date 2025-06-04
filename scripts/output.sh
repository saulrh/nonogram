#!/usr/bin/env bash

sqlite3 --readonly data.sqlite3 -csv "select size, probability, cast(uniq as real)/cast(total as real) from solves" | wl-copy
