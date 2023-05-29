#!/usr/bin/env python
"""First-pass Korean stimulus generation.

This simply generates potential stimuli and codes their basic properties.
Subsequent steps will remove actual lexical items and balance the stimuli
according to our assumptions about grammaticality.
"""

import csv
import dataclasses
import functools
import itertools
import logging

from typing import Iterator, List, Optional, Set, Tuple

import jamo
import korean_romanizer

# Onsets.
# /c/ <ㅈ>: more precisely /t͡ɕ/.
# /"cʰ/ <ㅊ>: more precisely /t͡ɕʰ/.
PLAIN_STOP_ONSETS = ["p", "t", "c", "k"]
ASPIRATED_STOP_ONSETS = ["pʰ", "tʰ", "cʰ", "kʰ"]
STOP_ONSETS = PLAIN_STOP_ONSETS + ASPIRATED_STOP_ONSETS
NASAL_ONSETS = ["m", "n"]
SIMPLE_ONSETS = STOP_ONSETS + ["s"] + NASAL_ONSETS

# /e/ proposes transcription problems.
FRONT_VOWELS = ["i", "a"]
BACK_VOWELS = ["o", "u"]
VOWELS = FRONT_VOWELS + BACK_VOWELS

NASAL_CODAS = ["m", "n", "ŋ"]
STOP_CODAS = ["p̚", "t̚", "k̚"]
CODAS = NASAL_CODAS + STOP_CODAS

MONOSYLLABLES = "monosyllables.tsv"
DISYLLABLES = "disyllables.tsv"
LEXICON = "kor_hang_narrow.tsv"

HANGUL_ONSET = {
    "p": "ㅂ",
    "t": "ㄷ",
    "c": "ㅈ",
    "k": "ㄱ",
    "pʰ": "ㅍ",
    "tʰ": "ㅌ",
    "cʰ": "ㅊ",
    "kʰ": "ㅋ",
    "s": "ᄉ",  # Has an allophone [ʃ] before /i/.
    "m": "ᄆ",
    "n": "ᄂ",
}
HANGUL_NUCLEUS = {
    "a": "ㅏ",
    "o": "ㅗ",
    "u": "ㅜ",
    "i": "ㅣ",
    "wa": "ㅘ",
    "wi": "ㅟ",  # More precisely /ɰi/.
}
HANGUL_CODA = {"p̚": "ᆸ", "t̚": "ᆮ", "k̚": "ᆨ", "m": "ᆷ", "n": "ᆫ", "ŋ": "ᆼ"}


class Error(Exception):
    pass


def _romanize(hangul: str) -> str:
    return korean_romanizer.Romanizer(hangul).romanize()


@dataclasses.dataclass
class Monosyllable:
    onset: str
    nucleus: str
    coda: Optional[str] = None
    shape: Optional[str] = None

    def jamo_tuple(self) -> Tuple[str, str, str]:
        if self.shape in ["CV", "CVC", "CwV", "CwVC"]:
            spelled_onset = HANGUL_ONSET[self.onset]
        elif self.shape.startswith("NCV"):
            spelled_onset = (
                HANGUL_ONSET[self.onset[0]] + HANGUL_ONSET[self.onset[1:]]
            )
        elif self.shape.startswith("CNV"):
            spelled_onset = (
                HANGUL_ONSET[self.onset[:-1]] + HANGUL_ONSET[self.onset[-1]]
            )
        else:
            raise Error(f"Unknown shape: {self.shape}")
        spelled_nucleus = HANGUL_NUCLEUS[self.nucleus]
        spelled_coda = HANGUL_CODA[self.coda] if self.coda else ""
        return spelled_onset, spelled_nucleus, spelled_coda

    @property
    def jamo(self) -> str:
        return "".join(self.jamo_tuple())

    @functools.cached_property
    def hangul(self) -> str:
        spelled_onset, spelled_nucleus, spelled_coda = self.jamo_tuple()
        try:
            return jamo.jamo_to_hangul(
                spelled_onset, spelled_nucleus, spelled_coda
            )
        except TypeError:
            return ""

    # TODO: maybe should be a mixin so I don't have to repeat.

    @functools.cached_property
    def romanization(self) -> str:
        return _romanize(self.hangul)

    @property
    def line(self) -> List[str]:
        return [
            self.onset,
            self.nucleus,
            self.coda,
            self.shape,
            self.jamo,
            self.hangul,
            self.romanization,
        ]


@dataclasses.dataclass
class Bisyllable:
    syl1: Monosyllable
    syl2: Monosyllable
    shape: str

    @property
    def jamo(self) -> str:
        return self.syl1.jamo + self.syl2.jamo

    @functools.cached_property
    def hangul(self) -> str:
        hangul1 = self.syl1.hangul
        hangul2 = self.syl2.hangul
        if not hangul1 or not hangul2:
            return ""
        return hangul1 + hangul2

    @functools.cached_property
    def romanization(self) -> str:
        return _romanize(self.hangul)

    @property
    def line(self) -> List[str]:
        return [
            self.syl1.onset,
            self.syl1.nucleus,
            self.syl2.onset,
            self.syl2.nucleus,
            self.syl2.coda,
            self.shape,
            self.jamo,
            self.hangul,
            self.romanization,
        ]


def _monosyllables() -> Iterator[Monosyllable]:
    # The checks on coda inoculate us against things like /mpip̚/.
    # Plain.
    for onset in SIMPLE_ONSETS:
        for vowel in VOWELS:
            for coda in CODAS:
                if coda.startswith(onset[0]):
                    continue
                yield Monosyllable(onset, vowel, coda, "CVC")
    # Cw. I am treating this as part of the nucleus because that's how it's
    # spelled.
    for onset in STOP_ONSETS:
        for vowel in FRONT_VOWELS:
            for coda in CODAS:
                if coda.startswith(onset[0]):
                    continue
                yield Monosyllable(onset, "w" + vowel, coda, "CwVC")
    # Prenasal.
    for stop in STOP_ONSETS:
        for nasal in NASAL_ONSETS:
            onset = nasal + stop
            for vowel in VOWELS:
                for coda in STOP_CODAS:
                    if coda.startswith(stop[0]):
                        continue
                    yield Monosyllable(onset, vowel, coda, "NCVC")
    # Postnasal.
    for stop in STOP_ONSETS:
        for nasal in NASAL_ONSETS:
            onset = stop + nasal
            for vowel in VOWELS:
                for coda in STOP_CODAS:
                    if coda.startswith(stop[0]):
                        continue
                    yield Monosyllable(onset, vowel, coda, "CNVC")


def _disyllables() -> Iterator[Bisyllable]:
    # The checks on coda inoculate us against things like /mpip̚/.
    # We avoid similar onsets or vowels in back-to-back syllables too.
    # Plain.
    for onset1, onset2 in itertools.permutations(SIMPLE_ONSETS, 2):
        if onset1.startswith(onset2) or onset2.startswith(onset1):
            continue
        for vowel1, vowel2 in itertools.permutations(VOWELS, 2):
            syl1 = Monosyllable(onset1, vowel1, shape="CV")
            for coda in CODAS:
                if coda.startswith(onset2[0]):
                    continue
                syl2 = Monosyllable(onset2, vowel2, coda, shape="CVC")
            yield Bisyllable(syl1, syl2, "CVCVC")
    # Cw. I am treating this as part of the nucleus because that's how it's
    # spelled.
    for onset1, onset2 in itertools.permutations(SIMPLE_ONSETS, 2):
        if onset1.startswith(onset2) or onset2.startswith(onset1):
            continue
        for vowel1, vowel2 in itertools.product(FRONT_VOWELS, VOWELS):
            syl1 = Monosyllable(onset1, "w" + vowel1, shape="CwV")
            for coda in CODAS:
                if coda.startswith(onset2[0]):
                    continue
                syl2 = Monosyllable(onset2, vowel2, coda, shape="CVC")
                yield Bisyllable(syl1, syl2, "CwVCVC")
    # Prenasal.
    for stop in STOP_ONSETS:
        for nasal in NASAL_ONSETS:
            onset1 = nasal + stop
            for vowel1, vowel2 in itertools.permutations(VOWELS, 2):
                syl1 = Monosyllable(onset1, vowel1, shape="NCV")
                for onset2 in SIMPLE_ONSETS:
                    if onset2.startswith(stop):
                        continue
                    for coda in CODAS:
                        if coda.startswith(onset2[0]):
                            continue
                        syl2 = Monosyllable(onset2, vowel2, coda, shape="CVC")
                        yield Bisyllable(syl1, syl2, "NCVCVC")
    # Postnasal.
    for stop in STOP_ONSETS:
        for nasal in NASAL_ONSETS:
            onset1 = stop + nasal
            for vowel1, vowel2 in itertools.permutations(VOWELS, 2):
                syl1 = Monosyllable(onset1, vowel1, shape="CNV")
                for onset2 in SIMPLE_ONSETS:
                    if onset2.startswith(stop):
                        continue
                    for coda in CODAS:
                        if coda.startswith(onset2[0]):
                            continue
                        syl2 = Monosyllable(onset2, vowel2, coda, shape="CVC")
                        yield Bisyllable(syl1, syl2, "CNVCVC")


def main():
    with open(MONOSYLLABLES, "w") as sink:
        tsv_writer = csv.writer(sink, delimiter="\t")
        tsv_writer.writerow(
            [
                "onset",
                "nucleus",
                "coda",
                "shape",
                "jamo",
                "hangul",
                "romanization",
            ]
        )
        for entry in _monosyllables():
            tsv_writer.writerow(entry.line)
    # This probably could be cleverer and focus just on disyllables.
    lexicon: Set[str] = set()
    with open(LEXICON, "r") as source:
        tsv_reader = csv.reader(source, delimiter="\t")
        for word, _ in tsv_reader:
            try:
                lexicon.add(_romanize(word))
            except (KeyError, AttributeError):  # Raised by the romanizer.
                pass
    logging.info(f"{len(lexicon):,} lexicon entries")
    with open(DISYLLABLES, "w") as sink:
        tsv_writer = csv.writer(sink, delimiter="\t")
        tsv_writer.writerow(
            [
                "onset1",
                "nucleus1",
                "onset2",
                "nucleus2",
                "coda",
                "shape",
                "jamo",
                "hangul",
                "romanization",
            ]
        )
        filtered = 0
        for entry in _disyllables():
            # Filters based on the lexicon.
            if entry.romanization and entry.romanization in lexicon:
                logging.info(
                    f"{entry.hangul} ({entry.romanization}) is lexical"
                )
                filtered += 1
                continue
            tsv_writer.writerow(entry.line)
    logging.info(f"{filtered:,} disyllables filtered")


if __name__ == "__main__":
    logging.basicConfig(format="%(levelname)s: %(message)s", level="INFO")
    main()
