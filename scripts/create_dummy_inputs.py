#!/usr/bin/env python3
import argparse
import csv
import hashlib
import os
from pathlib import Path

import numpy as np
import soundfile as sf

RATE = 16000


def parse_args():
    parser = argparse.ArgumentParser(
        description="Create small synthetic inputs for debugging the LibriDEMAND pipeline."
    )
    parser.add_argument(
        "--storage_dir",
        required=True,
        help="Storage directory to populate with dummy LibriSpeech and demand_noise files.",
    )
    parser.add_argument(
        "--metadata_root",
        default="metadata",
        help="Repository metadata directory. Defaults to ./metadata.",
    )
    parser.add_argument(
        "--max_seconds",
        type=float,
        default=1.0,
        help="Maximum duration per generated file. Lower values make the debug run faster.",
    )
    return parser.parse_args()


def read_csv_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_audio(path, num_samples, tone_hz, noise=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.arange(num_samples, dtype=np.float32)
    if noise:
        seed = int(hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        audio = rng.normal(0, 0.03, num_samples).astype(np.float32)
    else:
        audio = 0.05 * np.sin(2 * np.pi * tone_hz * samples / RATE)
        audio = audio.astype(np.float32)
    sf.write(path, audio, RATE)


def create_librispeech(storage_dir, metadata_root, max_samples):
    md_dir = metadata_root / "LibriSpeech" / "for_demand"
    created = set()
    for csv_path in sorted(md_dir.glob("*.csv")):
        for row in read_csv_rows(csv_path):
            rel_path = row["origin_path"]
            if rel_path in created:
                continue
            length = min(int(row["length"]), max_samples)
            spk = int(row["speaker_ID"])
            tone_hz = 180 + (spk % 50) * 4
            write_audio(storage_dir / "LibriSpeech" / rel_path, length, tone_hz)
            created.add(rel_path)
    return len(created)


def create_demand_noise(storage_dir, metadata_root, max_samples):
    md_dir = metadata_root / "Demand_noise"
    created = set()
    for csv_path in sorted(md_dir.glob("*.csv")):
        for row in read_csv_rows(csv_path):
            rel_path = row["origin_path"]
            if rel_path in created:
                continue
            length = min(int(row["length"]), max_samples)
            write_audio(storage_dir / "demand_noise" / rel_path, length, 0, noise=True)
            created.add(rel_path)
    return len(created)


def main():
    args = parse_args()
    storage_dir = Path(args.storage_dir)
    metadata_root = Path(args.metadata_root)
    max_samples = max(1, int(args.max_seconds * RATE))

    librispeech_count = create_librispeech(storage_dir, metadata_root, max_samples)
    demand_count = create_demand_noise(storage_dir, metadata_root, max_samples)

    print(f"Created {librispeech_count} dummy LibriSpeech files")
    print(f"Created {demand_count} dummy DEMAND noise files")
    print(f"Dummy storage is ready: {storage_dir}")


if __name__ == "__main__":
    main()
