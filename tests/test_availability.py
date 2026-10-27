from datetime import datetime, timedelta

from patchmate.availability import Availability, Kind, Signal

NOW = datetime(2026, 11, 2, 18, 0)


def test_only_patchmates_see_signals_and_expired_ones_go():
    av = Availability()
    av.signal(Signal("a", Kind.CALL, NOW + timedelta(hours=2), note="walking the dog"))
    av.signal(Signal("b", Kind.MEET, NOW + timedelta(hours=1), area="Braddon"))
    av.signal(Signal("c", Kind.CALL, NOW - timedelta(minutes=1)))
    assert [s.guest_id for s in av.open_now("z", {"a", "c"}, NOW)] == ["a"]
    assert "c" not in av.signals


def test_you_dont_see_yourself_and_clear_works():
    av = Availability()
    av.signal(Signal("a", Kind.CALL, NOW + timedelta(hours=1)))
    assert av.open_now("a", {"a"}, NOW) == []
    av.clear("a")
    assert av.open_now("b", {"a"}, NOW) == []
