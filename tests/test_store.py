import time
from store import write_state, delete_state, load_sessions


def test_write_and_load(tmp_path):
    now = time.time()
    write_state("s1", "proj", "green", "Stop", now, directory=tmp_path)
    sessions = load_sessions(now, directory=tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "s1"
    assert sessions[0]["project"] == "proj"
    assert sessions[0]["state"] == "green"
    assert sessions[0]["reason"] == "Stop"


def test_delete_is_safe_when_missing(tmp_path):
    now = time.time()
    write_state("s1", "proj", "green", "x", now, directory=tmp_path)
    delete_state("s1", directory=tmp_path)
    assert load_sessions(now, directory=tmp_path) == []
    delete_state("nope", directory=tmp_path)  # no error


def test_load_skips_bad_files(tmp_path):
    (tmp_path / "bad.json").write_text("{not json")
    now = time.time()
    write_state("good", "p", "green", "x", now, directory=tmp_path)
    sessions = load_sessions(now, directory=tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "good"


def test_load_deletes_stale(tmp_path):
    now = time.time()
    write_state("old", "p", "red", "x", now - 90000, directory=tmp_path)
    assert load_sessions(now, directory=tmp_path, stale=86400) == []
    assert not (tmp_path / "old.json").exists()


def test_load_skips_wrong_shape_json(tmp_path):
    (tmp_path / "scalar.json").write_text('"hello"')
    (tmp_path / "array.json").write_text('[1, 2, 3]')
    (tmp_path / "nullupdated.json").write_text('{"updated": null}')
    now = time.time()
    write_state("good", "p", "green", "x", now, directory=tmp_path)
    sessions = load_sessions(now, directory=tmp_path)
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "good"
