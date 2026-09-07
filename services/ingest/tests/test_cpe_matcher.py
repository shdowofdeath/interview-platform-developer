from src.services import cpe_matcher

ROUTEROS_6_47_3 = "cpe:2.3:o:mikronet:routeros:6.47.3:*:*:*:*:*:*:*"


def test_known_asset_returns_its_cves():
    cves = cpe_matcher.applicable_cves(ROUTEROS_6_47_3)
    assert len(cves) == 9
    assert "CVE-2026-13290" in cves


def test_unknown_asset_returns_empty():
    assert cpe_matcher.applicable_cves("cpe:2.3:a:acme:nothing:1.0:*:*:*:*:*:*:*") == []


def test_build_cpe_uri_shape():
    uri = cpe_matcher.build_cpe_uri("mikronet", "routeros", "6.47.3")
    assert uri.count(":") == 12
    assert "mikronet" in uri
