import pytest

from package_service.settings import secret


def test_secret_is_read_from_file(tmp_path, monkeypatch):
    path = tmp_path / "api-key"
    path.write_text("from-file\n")  # editors and `echo` add a trailing newline
    monkeypatch.setenv("DEMO_SECRET_FILE", str(path))
    monkeypatch.setenv("DEMO_SECRET", "from-env")
    assert secret("DEMO_SECRET") == "from-file"


def test_secret_falls_back_to_environment(monkeypatch):
    monkeypatch.delenv("DEMO_SECRET_FILE", raising=False)
    monkeypatch.setenv("DEMO_SECRET", "from-env")
    assert secret("DEMO_SECRET") == "from-env"


def test_unreadable_secret_file_fails_clearly(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_SECRET_FILE", str(tmp_path / "missing"))
    with pytest.raises(RuntimeError, match="DEMO_SECRET_FILE"):
        secret("DEMO_SECRET")