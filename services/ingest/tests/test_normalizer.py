from src.models.indicator import IndicatorType
from src.services.normalizer import detect_type, matches, normalize_value


def test_strips_surrounding_whitespace():
    assert normalize_value("  198.51.100.7 \n") == "198.51.100.7"


def test_detects_ipv4():
    assert detect_type("198.51.100.7") == IndicatorType.IPV4


def test_detects_domain():
    assert detect_type("login-portal.nightjar-lab.test") == IndicatorType.DOMAIN


def test_detects_url():
    assert detect_type("http://cdn-update.nightjar-lab.test/pkg/loader.bin") == IndicatorType.URL


def test_detects_sha256():
    value = "a9eee02b61b8f0dd0b1b9a1f8b2c7d4e6f0a1b2c3d4e5f60718293a4b5c6d7e8"
    assert detect_type(value) == IndicatorType.SHA256


def test_detects_md5():
    assert detect_type("d41d8cd98f00b204e9800998ecf8427e") == IndicatorType.MD5


def test_matches_ignores_whitespace():
    assert matches(" 198.51.100.7", "198.51.100.7 ")
