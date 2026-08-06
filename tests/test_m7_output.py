from keiba.m6_scoring import ScoreResult
from keiba.m7_output import recommend_bets


def _result(rank, horse_number):
    return ScoreResult("R1", horse_number, f"H{horse_number}", total_score=100 - rank, breakdown={}, rank=rank)


def test_recommend_bets_shapes():
    results = [_result(1, 3), _result(2, 1), _result(3, 5), _result(4, 2)]
    bets = recommend_bets(results)

    assert bets["単勝"] == [3]
    assert bets["複勝"] == [3, 1]
    assert sorted(tuple(sorted(c)) for c in bets["馬連(BOX)"]) == [(1, 3), (1, 5), (3, 5)]
