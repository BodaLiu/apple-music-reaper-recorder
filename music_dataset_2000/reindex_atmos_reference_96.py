#!/usr/bin/env python3
"""Reindex the validated Atmos reference dataset from 100 planned to 96 kept tracks."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import unicodedata
import uuid
from pathlib import Path


# User-editable configuration. Paths are fixed here; no path arguments are needed.
# Edit these two paths for your local recording drive before running.
SOURCE_ROOT = Path.home() / "Atmos_Reference_100_V2"
FINAL_ROOT = Path.home() / "Atmos_Reference_96_V2"
EXCLUDED = {
    4: "recording failed; no formal WAV",
    96: "only channels 1-2 contain signal",
    97: "recording failed; no formal WAV",
    99: "only channels 1-2 contain signal",
}
EXPECTED_SOURCE_ROWS = 100
EXPECTED_SOURCE_WAVS = 98
EXPECTED_FINAL_TRACKS = 96
BACKUP_DIRNAME = "_reindex_backup_20260901"
EXCLUDED_DIRNAME = "_excluded"


def read_metadata(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv_atomic(
    path: Path, fieldnames: list[str], rows: list[dict[str, str]]
) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
    temporary.replace(path)


def sidecar(path: Path) -> Path:
    return path.with_name("._" + path.name)


def validate_and_plan() -> tuple[
    list[str],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    if not SOURCE_ROOT.is_dir():
        raise RuntimeError(f"Source directory not found: {SOURCE_ROOT}")
    if FINAL_ROOT.exists():
        raise RuntimeError(f"Final directory already exists: {FINAL_ROOT}")

    metadata_path = SOURCE_ROOT / "metadata.csv"
    fieldnames, rows = read_metadata(metadata_path)
    if len(rows) != EXPECTED_SOURCE_ROWS:
        raise RuntimeError(f"Expected 100 metadata rows, found {len(rows)}")

    indices = [int(row["playlist_index"]) for row in rows]
    if indices != list(range(1, EXPECTED_SOURCE_ROWS + 1)):
        raise RuntimeError("metadata.csv playlist_index is not exactly 1..100")

    actual_wavs = {
        path.name
        for path in SOURCE_ROOT.glob("*.wav")
        if not path.name.startswith("._")
    }
    if len(actual_wavs) != EXPECTED_SOURCE_WAVS:
        raise RuntimeError(f"Expected 98 formal WAVs, found {len(actual_wavs)}")

    successful_names = {
        row["wav_filename"] for row in rows if row["status"] == "success"
    }
    normalized_actual = {
        unicodedata.normalize("NFC", name): name for name in actual_wavs
    }
    normalized_metadata = {
        unicodedata.normalize("NFC", name): name for name in successful_names
    }
    if len(normalized_actual) != len(actual_wavs):
        raise RuntimeError("Formal WAV names collide after Unicode normalization")
    if len(normalized_metadata) != len(successful_names):
        raise RuntimeError("Metadata WAV names collide after Unicode normalization")
    if normalized_actual.keys() != normalized_metadata.keys():
        missing = sorted(normalized_metadata.keys() - normalized_actual.keys())
        extra = sorted(normalized_actual.keys() - normalized_metadata.keys())
        raise RuntimeError(f"WAV/metadata mismatch; missing={missing}, extra={extra}")

    for index, reason in EXCLUDED.items():
        row = rows[index - 1]
        if int(row["playlist_index"]) != index:
            raise RuntimeError(f"Excluded index mismatch at {index}")
        if index in (4, 97) and row["status"] != "failed":
            raise RuntimeError(f"Expected failed status at {index}: {reason}")
        if index in (96, 99) and row["status"] != "success":
            raise RuntimeError(f"Expected success status at {index}: {reason}")

    kept_source_rows = [
        row
        for row in rows
        if int(row["playlist_index"]) not in EXCLUDED
        and row["status"] == "success"
    ]
    if len(kept_source_rows) != EXPECTED_FINAL_TRACKS:
        raise RuntimeError(
            f"Expected {EXPECTED_FINAL_TRACKS} kept tracks, found {len(kept_source_rows)}"
        )

    final_rows: list[dict[str, str]] = []
    mapping_rows: list[dict[str, str]] = []
    for new_index, source_row in enumerate(kept_source_rows, 1):
        old_index = int(source_row["playlist_index"])
        old_filename = normalized_actual[
            unicodedata.normalize("NFC", source_row["wav_filename"])
        ]
        if "_" not in old_filename:
            raise RuntimeError(f"Unexpected WAV filename: {old_filename}")
        suffix = old_filename.split("_", 1)[1]
        new_filename = f"{new_index:05d}_{suffix}"

        final_row = dict(source_row)
        final_row["playlist_index"] = str(new_index)
        final_row["wav_filename"] = new_filename
        final_rows.append(final_row)

        mapping_rows.append(
            {
                "new_playlist_index": str(new_index),
                "new_wav_filename": new_filename,
                "original_playlist_index": str(old_index),
                "original_wav_filename": old_filename,
                "title": source_row["title"],
                "artist": source_row["artist"],
                "album": source_row["album"],
                "genre": source_row["genre"],
                "duration_seconds": source_row["duration_seconds"],
                "persistent_id": source_row["persistent_id"],
            }
        )

    excluded_rows: list[dict[str, str]] = []
    for index in sorted(EXCLUDED):
        row = dict(rows[index - 1])
        excluded_rows.append(
            {
                "original_playlist_index": row["playlist_index"],
                "original_wav_filename": row["wav_filename"],
                "title": row["title"],
                "artist": row["artist"],
                "status": row["status"],
                "exclusion_reason": EXCLUDED[index],
                "persistent_id": row["persistent_id"],
            }
        )

    return fieldnames, final_rows, mapping_rows, excluded_rows


def move_with_sidecar(source: Path, destination: Path) -> None:
    source.rename(destination)
    source_sidecar = sidecar(source)
    if source_sidecar.exists():
        source_sidecar.rename(sidecar(destination))


def apply_plan(
    fieldnames: list[str],
    final_rows: list[dict[str, str]],
    mapping_rows: list[dict[str, str]],
    excluded_rows: list[dict[str, str]],
) -> None:
    backup_dir = SOURCE_ROOT / BACKUP_DIRNAME
    excluded_dir = SOURCE_ROOT / EXCLUDED_DIRNAME
    if backup_dir.exists() or excluded_dir.exists():
        raise RuntimeError("Backup or excluded directory already exists; refusing to overwrite")
    backup_dir.mkdir()
    excluded_dir.mkdir()

    for name in ("metadata.csv", "capture_config.json"):
        source = SOURCE_ROOT / name
        if source.exists():
            shutil.copy2(source, backup_dir / name)

    mapping_fields = list(mapping_rows[0])
    excluded_fields = list(excluded_rows[0])
    write_csv_atomic(backup_dir / "renumber_mapping.csv", mapping_fields, mapping_rows)
    write_csv_atomic(excluded_dir / "excluded_tracks.csv", excluded_fields, excluded_rows)

    for old_index in (96, 99):
        old_filename = excluded_rows[[4, 96, 97, 99].index(old_index)][
            "original_wav_filename"
        ]
        move_with_sidecar(SOURCE_ROOT / old_filename, excluded_dir / old_filename)

    temporary_moves: list[tuple[Path, Path]] = []
    for mapping in mapping_rows:
        old_path = SOURCE_ROOT / mapping["original_wav_filename"]
        final_path = SOURCE_ROOT / mapping["new_wav_filename"]
        temporary_path = SOURCE_ROOT / (
            f".__reindex_tmp__{uuid.uuid4().hex}__{old_path.name}"
        )
        move_with_sidecar(old_path, temporary_path)
        temporary_moves.append((temporary_path, final_path))

    for temporary_path, final_path in temporary_moves:
        move_with_sidecar(temporary_path, final_path)

    write_csv_atomic(SOURCE_ROOT / "metadata.csv", fieldnames, final_rows)
    write_csv_atomic(SOURCE_ROOT / "playlist_catalog.csv", mapping_fields, mapping_rows)

    config_path = SOURCE_ROOT / "capture_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["playlist"] = "Dataset_Atmos_Reference_96_V2"
        for key in ("output_dir", "metadata_csv"):
            if isinstance(config.get(key), str):
                config[key] = config[key].replace(
                    "Atmos_Reference_100_V2", "Atmos_Reference_96_V2"
                )
        temporary_config = config_path.with_name(
            f".{config_path.name}.tmp-{uuid.uuid4().hex}"
        )
        temporary_config.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_config.replace(config_path)

    SOURCE_ROOT.rename(FINAL_ROOT)


def verify_final() -> None:
    fieldnames, rows = read_metadata(FINAL_ROOT / "metadata.csv")
    del fieldnames
    wavs = sorted(
        path.name
        for path in FINAL_ROOT.glob("*.wav")
        if not path.name.startswith("._")
    )
    expected_names = [row["wav_filename"] for row in rows]
    expected_indices = [f"{index:05d}" for index in range(1, 97)]
    actual_indices = [name.split("_", 1)[0] for name in wavs]
    if len(rows) != 96 or len(wavs) != 96:
        raise RuntimeError(f"Final count mismatch: metadata={len(rows)}, wavs={len(wavs)}")
    if wavs != expected_names or actual_indices != expected_indices:
        raise RuntimeError("Final filenames are not an exact continuous 00001..00096 set")
    if [int(row["playlist_index"]) for row in rows] != list(range(1, 97)):
        raise RuntimeError("Final metadata indices are not exactly 1..96")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true", help="perform the validated rename"
    )
    arguments = parser.parse_args()

    fieldnames, final_rows, mapping_rows, excluded_rows = validate_and_plan()
    print(f"Validated source: {len(final_rows)} tracks will be kept")
    for row in excluded_rows:
        print(
            "EXCLUDE",
            row["original_playlist_index"],
            row["artist"],
            "-",
            row["title"],
            f"({row['exclusion_reason']})",
        )
    print("Boundary mappings:")
    for mapping in mapping_rows[:5] + mapping_rows[-5:]:
        print(
            mapping["original_playlist_index"],
            "->",
            mapping["new_playlist_index"],
            mapping["new_wav_filename"],
        )

    if not arguments.apply:
        print("Dry run only; no files changed")
        return

    apply_plan(fieldnames, final_rows, mapping_rows, excluded_rows)
    verify_final()
    print(f"Applied and verified: {FINAL_ROOT}")


if __name__ == "__main__":
    main()
