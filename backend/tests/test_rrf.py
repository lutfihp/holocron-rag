from app.services.retrieval.rrf import rrf_fuse


def test_fuses_single_list():
    bm = [("a", 1), ("b", 2), ("c", 3)]
    vec = []
    fused = rrf_fuse(bm, vec, k=60)
    assert [x[0] for x in fused] == ["a", "b", "c"]


def test_boosts_items_in_both_lists():
    bm = [("a", 1), ("b", 2), ("c", 3)]
    vec = [("b", 1), ("a", 2), ("d", 3)]
    fused = rrf_fuse(bm, vec, k=60)
    ranking = [x[0] for x in fused]
    # a and b appear in both → should rank above c and d which appear in one
    assert set(ranking[:2]) == {"a", "b"}


def test_higher_rank_wins_tie():
    bm = [("a", 1), ("b", 2)]
    vec = [("b", 1), ("a", 2)]
    fused = rrf_fuse(bm, vec, k=60)
    assert {x[0] for x in fused} == {"a", "b"}


def test_score_decreases_with_rank():
    bm = [("a", 1), ("b", 2), ("c", 3), ("d", 4)]
    vec = []
    fused = rrf_fuse(bm, vec, k=60)
    scores = [x[1] for x in fused]
    assert scores == sorted(scores, reverse=True)


def test_empty_inputs_returns_empty():
    assert rrf_fuse([], [], k=60) == []
