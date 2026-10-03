import pytest

from booktools.compare import pair

pytestmark = pytest.mark.tier1

A = "The lamp was lit at dusk, and the keeper is not one to waste oil."
B = "She wrote every figure in a large ledger."
C = "The log for March is missing."
B_EDITED = "She wrote every single figure in a large ledger."
X = "A paragraph added in the later save, about nothing above."


def test_identical_saves_pair_every_paragraph_with_itself():
    assert pair([A, B, C], [A, B, C]) == [(0, 0), (1, 1), (2, 2)]
    assert pair([], []) == []


def test_a_paragraph_added_does_not_put_the_later_ones_out_of_step():
    assert pair([A, B, C], [A, X, B, C]) == [(0, 0), (None, 1), (1, 2), (2, 3)]
    assert pair([A, B, C], [X, A, B, C]) == [(None, 0), (0, 1), (1, 2), (2, 3)]
    assert pair([], [A]) == [(None, 0)]


def test_a_paragraph_removed_is_reported_where_it_stood():
    assert pair([A, B, C], [A, C]) == [(0, 0), (1, None), (2, 1)]
    assert pair([A], []) == [(0, None)]


def test_an_edited_paragraph_is_paired_with_its_old_self():
    assert pair([A, B, C], [A, B_EDITED, C]) == [(0, 0), (1, 1), (2, 2)]


def test_an_edited_paragraph_beside_an_added_one_still_finds_its_old_self():
    assert pair([A, B, C], [A, X, B_EDITED, C]) == [(0, 0), (None, 1), (1, 2), (2, 3)]
    assert pair([A, B, C], [A, B_EDITED, X, C]) == [(0, 0), (1, 1), (None, 2), (2, 3)]


def test_a_paragraph_replaced_by_an_unrelated_one_is_removed_and_added():
    assert pair([A, B, C], [A, X, C]) == [(0, 0), (1, None), (None, 1), (2, 2)]


def test_identical_paragraphs_are_paired_in_order():
    assert pair(["", A, "", ""], ["", A, ""]) == [(0, 0), (1, 1), (2, 2), (3, None)]
