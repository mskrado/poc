import urllib.request

from browser_benchmark import sites, synth_data

EXPECTED_SITES = {
    "bulk_table",
    "checkout",
    "mfa_gate",
    "multipage_form",
    "soft_paywall",
    "spa_form",
}


def _get(url: str) -> tuple[int, str]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.read().decode("utf-8")


def test_all_fixture_sites_exist():
    assert set(sites.list_sites()) == EXPECTED_SITES


def test_fixture_sites_are_servable():
    with sites.serve() as base_url:
        status, body = _get(base_url + "/")
        assert status == 200
        for name in EXPECTED_SITES:
            status, body = _get(sites.site_url(base_url, name))
            assert status == 200, name
            assert "<html" in body.lower()


def test_spa_fixture_regenerates_testids():
    with sites.serve() as base_url:
        _, body = _get(sites.site_url(base_url, "spa_form"))
    assert "btn-search-" in body
    assert "generation += 1" in body


def test_paywall_keeps_the_table_in_the_dom():
    with sites.serve() as base_url:
        _, body = _get(sites.site_url(base_url, "soft_paywall"))
    assert body.count("<tr>") == 7  # header + 6 lane rows, present behind the gate


def test_synth_data_is_deterministic_and_synthetic():
    first = synth_data.generate("contacts", 50, seed=4242)
    second = synth_data.generate("contacts", 50, seed=4242)
    assert first == second
    assert len(first) == 50
    assert all(row["email"].endswith(("example.com", "example.org", "example.net")) for row in first)

    other = synth_data.generate("contacts", 50, seed=99)
    assert other != first


def test_synth_data_covers_every_kind():
    for kind in synth_data.KINDS:
        records = synth_data.generate(kind, 5)
        assert len(records) == 5
        csv_text = synth_data.to_csv(records)
        assert csv_text.count("\n") == 6  # header + 5 rows
