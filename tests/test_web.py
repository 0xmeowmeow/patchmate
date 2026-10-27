def test_tap_counts_and_redirects(tmp_path, monkeypatch):
    import patchmate.web as web
    monkeypatch.setattr(web, "DATA", tmp_path)
    c = web.create_app().test_client()
    r = c.get("/tap")
    assert r.status_code == 302 and r.headers["Location"] == "/?via=tap"
    assert len((tmp_path / "taps.log").read_text().splitlines()) == 1
    assert b"tapped" in c.get("/?via=tap").data
    assert b"tapped" not in c.get("/").data
