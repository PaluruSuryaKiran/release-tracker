import pytest

from package_service.versions import parse_version, Version


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1.2.3", Version(1, 2, 3)),
        ("0.0.0", Version(0, 0, 0)),
        ("10.20.30", Version(10, 20, 30)),
    ],
)

def test_parse_valid(text, expected):
    assert parse_version(text) == expected

@pytest.mark.parametrize(
    "text",
    [
        "",
        "1",
        "1.2",
        "1.2.3.4",
        "v1.2.3",
        "1.2.x",
        "01.2.3",
        "1.2.3 ",
        "1.2.3\n",
        "\u0661.\u0662.\u0663",
        "-1.2.3",
        "1..3"
    ],
)
def test_parse_invalid(text):
    with pytest.raises(ValueError):
        parse_version(text)

def test_versions_sort_numerically():
    versions = [parse_version(v) for v in ["1.9.0", "1.10.0", "1.2.0"]]
    assert sorted(versions) == [
        Version(1, 2, 0),
        Version(1, 9, 0),
        Version(1, 10, 0),
    ]

def test_str_round_trip():
    assert str(parse_version("1.2.3")) == "1.2.3"