#!/usr/bin/env python
"""Implements stratified sampling for Korean.

This produces two lists of 30 words with the same gross properties. For each
list:

* 30 of the words are monosyllables; 30 are disyllables.
* 30 the words are expected to be well-formed; 30 of the words are expected
  to be ill-formed.
"""


import collections
import csv
import random

from typing import Any, Dict, Iterator, Tuple


SEED = 1568
MONOSYLLABLES = "monosyllables-annotated.tsv"
DISYLLABLES = "disyllables-annotated.tsv"
LIST1 = "kor-list-1.tsv"
LIST2 = "kor-list-2.tsv"


def _proc_file(path: str) -> Iterator[Tuple[str, Any]]:
    with open(path, "r") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            if row["lexicality"] != "FALSE":
                continue
            del row["lexicality"]
            del row["memo"]
            shape = row["shape"]
            row["transcription"] = (
                row["onset1"]
                + row["nucleus1"]
                + row["onset2"]
                + row["nucleus2"]
                + row["coda"]
            )
            yield shape, row


def main() -> None:
    random.seed(SEED)  # Same result every time.
    list1 = []
    list2 = []
    by_shape = collections.defaultdict(list)
    for shape, row in _proc_file(MONOSYLLABLES):
        by_shape[shape].append(row)
    for shape, row in _proc_file(DISYLLABLES):
        by_shape[shape].append(row)
    for shape, entries in by_shape.items():
        elist = list(entries)
        # Special cases for sizing.
        if shape in ["CVC", "CwVC", "CNVC", "NCVC"]:
            size = 5
        else:
            size = 10
        assert len(elist) >= size * 2, (shape, len(elist))
        random.shuffle(elist)
        list1.extend(elist[:size])
        list2.extend(elist[size : 2 * size])
    random.shuffle(list1)
    random.shuffle(list2)
    with open(LIST1, "w") as sink:
        writer = csv.DictWriter(sink, delimiter="\t", fieldnames=row.keys())
        writer.writeheader()
        writer.writerows(list1)
    with open(LIST2, "w") as sink:
        writer = csv.DictWriter(sink, delimiter="\t", fieldnames=row.keys())
        writer.writeheader()
        writer.writerows(list2)


if __name__ == "__main__":
    main()
