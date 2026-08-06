import pytest

from keiba.m4_paddock_eval import make_score


def test_make_score_valid():
    score = make_score("R1", 1, {"毛艶": 1, "発汗": -1, "歩くリズム": 1})
    assert score.total == 1


def test_make_score_rejects_unknown_item():
    with pytest.raises(ValueError):
        make_score("R1", 1, {"未知の項目": 1})


def test_make_score_rejects_out_of_range():
    with pytest.raises(ValueError):
        make_score("R1", 1, {"毛艶": 3})
