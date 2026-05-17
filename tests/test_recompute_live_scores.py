import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sample_scoring_engine_runs(tmp_path):
    out = tmp_path / "enriched.json"
    cmd = [
        "python",
        str(ROOT / "scripts" / "recompute_live_scores.py"),
        "--input",
        str(ROOT / "data" / "sample" / "sample_macro_regime_scanner.json"),
        "--output",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    data = json.loads(out.read_text())
    assets = data["assets"]
    assert assets
    for asset in assets:
        assert "scoreAudit" in asset
        assert "netScore" in asset["scoreAudit"]
        assert "countedRows" in asset["scoreAudit"]
        assert "excludedRows" in asset["scoreAudit"]

    by_symbol = {a["symbol"]: a for a in assets}
    assert by_symbol["SPX500"]["scoreAudit"]["assetClass"] == "us_equity_index"
    assert by_symbol["DXY"]["scoreAudit"]["assetClass"] == "usd_fx"
    assert by_symbol["EURUSD"]["scoreAudit"]["assetClass"] == "foreign_usd_pair"
    assert by_symbol["WTI"]["scoreAudit"]["assetClass"] == "energy_commodity"
    assert by_symbol["WHEAT"]["scoreAudit"]["assetClass"] == "agriculture_commodity"

    # Same macro pressure should not affect all assets the same way.
    assert by_symbol["SPX500"]["scoreAudit"]["netScore"] != by_symbol["DXY"]["scoreAudit"]["netScore"]
    assert by_symbol["WTI"]["scoreAudit"]["countedRows"] >= 1
    assert by_symbol["WHEAT"]["scoreAudit"]["countedRows"] >= 1
