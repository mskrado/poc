import os, sys
sys.path.insert(0, os.environ["TWOARM_WORKSPACE"])
import inflection
import pytest

@pytest.mark.parametrize("n,want", [(111, "111th"), (112, "112th"), (113, "113th"), (-112, "-112th"),
                                    (1, "1st"), (2, "2nd"), (3, "3rd"), (21, "21st"), (102, "102nd"), (1012, "1012th")])
def test_ordinalize(n, want):
    assert inflection.ordinalize(n) == want
