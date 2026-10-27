from patchmate.models import Connection, Guest
from patchmate.patches import Feeling, form_patches

A, N = Feeling.AGAIN, Feeling.NOT


def guests(*ids, **open_to):
    return [Guest(i, i, open_to=open_to.get(i, {Connection.CONVERSATION})) for i in ids]


def groups(patches):
    return [sorted(p.members) for p in patches]


def test_mutual_pair_forms_a_patch():
    marks = {("a", "b"): A, ("b", "a"): A}
    assert groups(form_patches(guests("a", "b"), marks)) == [["a", "b"]]


def test_one_way_interest_is_not_enough():
    assert form_patches(guests("a", "b"), {("a", "b"): A}) == []


def test_group_grows_through_mutual_marks():
    marks = {("a", "b"): A, ("b", "a"): A, ("b", "c"): A, ("c", "b"): A}
    assert groups(form_patches(guests("a", "b", "c"), marks)) == [["a", "b", "c"]]


def test_a_single_not_keeps_people_apart():
    marks = {("a", "b"): A, ("b", "a"): A, ("b", "c"): A, ("c", "b"): A, ("a", "c"): N}
    patches = groups(form_patches(guests("a", "b", "c"), marks))
    assert ["a", "b", "c"] not in patches
    assert not any("a" in p and "c" in p for p in patches)


def test_no_patch_across_connection_types():
    gs = guests("a", "b", b={Connection.PROFESSIONAL})
    assert form_patches(gs, {("a", "b"): A, ("b", "a"): A}) == []


def test_size_cap_and_everyone_once():
    ids = "abcdef"
    marks = {(x, y): A for x in ids for y in ids if x != y}
    patches = form_patches(guests(*ids), marks, max_size=3)
    assert all(len(p.members) <= 3 for p in patches)
    seen = [m for p in patches for m in p.members]
    assert len(seen) == len(set(seen)) == 6
