import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from scripts.hotkey import MOD_ALT, MOD_CONTROL, parse_hotkey
from scripts.search import best_score, score, switch_layout


def test_switch_layout():
    assert switch_layout("ср") == "ch"
    assert switch_layout("ch") == "ср"


def test_ranking_prefix_beats_substring_beats_subsequence():
    prefix = score("goo", "Google Chrome")
    word = score("chr", "Google Chrome")
    sub = score("ogl", "Google Chrome")
    seq = score("gce", "Google Chrome")
    assert prefix > word > sub > seq > 0


def test_subsequence_abbreviation():
    assert score("vsc", "Visual Studio Code") is not None
    assert score("vsc", "Google Chrome") is None


def test_all_tokens_must_match():
    assert score("git push", "git: push master") is not None
    assert score("git pull", "git: push master") is None


def test_russian_layout_finds_english_title():
    assert best_score("ср", "Chrome") is not None       # набрано "ch" в русской раскладке
    assert best_score("ср", "Notepad") is None


def test_empty_query_matches_everything():
    assert score("", "anything") == 0


def test_parse_hotkey():
    assert parse_hotkey("ctrl+space") == (MOD_CONTROL, 0x20)
    assert parse_hotkey("Ctrl+Alt+K") == (MOD_CONTROL | MOD_ALT, ord("K"))
    assert parse_hotkey("alt+f2") == (MOD_ALT, 0x71)


@pytest.mark.parametrize("bad", ["", "space", "ctrl+", "foo+space", "ctrl+ё"])
def test_parse_hotkey_errors(bad):
    with pytest.raises(ValueError):
        parse_hotkey(bad)


def test_no_fuzzy_on_long_text():
    long_text = "lorem ipsum dolor sit amet " * 10
    assert score("zzqq", long_text) is None
    assert score("vsc", long_text, fuzzy=False) is None
