"""Validate the deterministic web replay pitch/heading scenario."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse the environment root whose viewer parser should be validated."""
    parser = argparse.ArgumentParser(
        description="Validate the web log viewer pitch/heading replay scenario."
    )
    parser.add_argument(
        "--env-root",
        type=Path,
        required=True,
        help="MyTrainEnv or Release directory containing tools/web_log_viewer.",
    )
    return parser.parse_args()


def main() -> None:
    """Load the scenario through the selected environment and check contracts."""
    args = parse_args()
    env_root = args.env_root.expanduser().resolve()
    tools_dir = env_root / "tools"
    if not (tools_dir / "web_log_viewer" / "log_data.py").is_file():
        raise SystemExit(f"Invalid environment root: {env_root}")
    sys.path.insert(0, str(tools_dir))

    from web_log_viewer.log_data import (  # noqa: PLC0415
        build_viewer_data,
        discover_log_pairs,
        forward_vector,
    )

    scenario_dir = Path(__file__).resolve().parent
    ownship_path = scenario_dir / (
        "pitch_rotation_validation_ownship_(F-16)[Blue].csv"
    )
    target_path = scenario_dir / (
        "pitch_rotation_validation_target_(F-16)[Red].csv"
    )
    summary_path = scenario_dir / "pitch_rotation_validation_summary.json"

    pairs = discover_log_pairs(scenario_dir)
    assert pairs == [(ownship_path, target_path)], pairs
    data = build_viewer_data(ownship_path, target_path, summary_path)

    assert len(data.ownship.time) == 25
    assert len(data.target.time) == 25
    assert data.end_condition == (
        "pitch_rotation_validation_complete (manual_visual_check)"
    )

    expected_blue = {
        2: (0.0, 1000.0),
        7: (30.0, 1100.0),
        12: (0.0, 1250.0),
        17: (-30.0, 1150.0),
        22: (0.0, 1000.0),
    }
    for index, (expected_pitch, expected_altitude) in expected_blue.items():
        assert math.isclose(data.ownship.pitch_deg[index], expected_pitch)
        assert math.isclose(data.ownship.position[index][2], expected_altitude)

    assert data.ownship.position[-1][1] > data.ownship.position[0][1]
    assert data.target.position[-1][1] < data.target.position[0][1]

    north_climb = forward_vector(yaw_deg=0.0, pitch_deg=30.0)
    north_dive = forward_vector(yaw_deg=0.0, pitch_deg=-30.0)
    south_level = forward_vector(yaw_deg=180.0, pitch_deg=0.0)
    assert math.isclose(north_climb[0], 0.0, abs_tol=1e-9)
    assert math.isclose(north_climb[1], math.sqrt(3.0) / 2.0)
    assert math.isclose(north_climb[2], 0.5)
    assert math.isclose(north_dive[2], -0.5)
    assert math.isclose(south_level[1], -1.0)

    print(f"PASS env_root={env_root}")
    print("frames=25 checkpoints=5 pair_count=1")
    print(f"north_climb={north_climb}")
    print(f"north_dive={north_dive}")
    print(f"south_level={south_level}")


if __name__ == "__main__":
    main()