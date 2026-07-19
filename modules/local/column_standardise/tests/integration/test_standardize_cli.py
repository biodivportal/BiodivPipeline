import sys
import os
import json
import subprocess
import pandas as pd


def test_standardize_cli(tmp_path):
    # Setup paths
    input_csv = tmp_path / "input.csv"
    out_csv = tmp_path / "standardised.csv"
    out_map = tmp_path / "column_mapping.json"

    # Create a dummy CSV
    df = pd.DataFrame(
        {"Lat": [1.0, 2.0], "Long": [3.0, 4.0], "Notes": ["test", "test2"]}
    )
    df.to_csv(input_csv, index=False)

    # Run the CLI
    env = os.environ.copy()
    # Ensure PYTHONPATH is set so python -m app.standardize works
    env["PYTHONPATH"] = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.standardize",
            "--input",
            str(input_csv),
            "--out-csv",
            str(out_csv),
            "--out-map",
            str(out_map),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    # Assert successful run
    assert result.returncode == 0, f"CLI failed with error: {result.stderr}"

    # Check outputs exist
    assert out_csv.exists()
    assert out_map.exists()

    # Validate CSV structure
    out_df = pd.read_csv(out_csv)
    # Ensure the headers were mapped (e.g. Lat -> LatitudeDecimal or something similar depending on weights)
    # We just check that the shape is the same
    assert out_df.shape == df.shape

    # Validate mapping JSON structure
    with open(out_map, "r") as f:
        mapping = json.load(f)

    assert isinstance(mapping, dict)
    assert "mapping" in mapping
    assert "metadata" in mapping

    mapping_list = mapping["mapping"]
    assert isinstance(mapping_list, list)
    lat_meta = next((m for m in mapping_list if m["header"] == "Lat"), None)
    assert lat_meta is not None
    assert "predicted_header" in lat_meta
    assert "confidence" in lat_meta
    assert "review_flag" in lat_meta
