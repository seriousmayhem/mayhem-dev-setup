import json

import pytest

from conftest import write
from mayhem.probe import load_tiers, match_tier

TIERS = [
    {"id": "8gb", "requires": {"vram_mb": 7000, "ram_mb": 60000}},
    {"id": "6gb", "requires": {"vram_mb": 5500, "ram_mb": 30000}},
    {"id": "4gb", "requires": {"vram_mb": 3500, "ram_mb": 30000}},
]


@pytest.mark.parametrize(("vram", "ram", "tier"), [
    (7000, 60000, "8gb"),   # exactly on the floor
    (6999, 64000, "6gb"),   # one MiB short of the best tier
    (7204, 59999, "6gb"),   # VRAM fits, RAM doesn't
    (5500, 30000, "6gb"),
    (5499, 30000, "4gb"),
    (3499, 64000, None),
    (32768, 16000, None),   # big card, too little RAM for any tier
])
def test_first_tier_whose_floors_are_met(vram, ram, tier):
    assert match_tier(TIERS, vram, ram) == tier


def test_last_root_with_tiers_wins(tmp_path):
    write(tmp_path / "a" / "inference" / "tiers.json", json.dumps({"tiers": [{"id": "public"}]}))
    write(tmp_path / "b" / "inference" / "tiers.json", json.dumps({"tiers": [{"id": "fleet"}]}))
    (tmp_path / "c").mkdir()
    assert load_tiers([tmp_path / "a", tmp_path / "b", tmp_path / "c"]) == [{"id": "fleet"}]
    assert load_tiers([tmp_path / "c"]) == []
