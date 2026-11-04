#!/usr/bin/env python3
"""Download and verify the upstream Zenodo v1 archive on demand.

The 200 MB archive is deliberately excluded from Git. By default this script
downloads the ZIP into ``external/archives`` without extracting it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path


RECORD_ID = "17400964"
API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
EXPECTED_NAME = "correa-et-al-neurips2025.zip"
EXPECTED_SIZE = 200_032_733
EXPECTED_MD5 = "8e20619169553ec6eb8b5f10e262a2d9"
DOWNLOAD_URL = f"https://zenodo.org/records/{RECORD_ID}/files/{EXPECTED_NAME}?download=1"


def md5(path: Path) -> str:
    digest = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "external" / "archives",
    )
    parser.add_argument("--extract", action="store_true", help="Extract after checksum verification.")
    args = parser.parse_args()

    with urllib.request.urlopen(API_URL) as response:
        metadata = json.load(response)
    files = {item["key"]: item for item in metadata["files"]}
    item = files.get(EXPECTED_NAME)
    if item is None:
        raise SystemExit(f"Zenodo record no longer exposes {EXPECTED_NAME}")
    if item["size"] != EXPECTED_SIZE or item["checksum"] != f"md5:{EXPECTED_MD5}":
        raise SystemExit("Zenodo metadata differs from the frozen v1 provenance record")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / EXPECTED_NAME
    if destination.is_file() and destination.stat().st_size == EXPECTED_SIZE and md5(destination) == EXPECTED_MD5:
        print(f"Using verified existing archive {destination}.")
    else:
        temporary = destination.with_suffix(".zip.part")
        print(f"Downloading {DOWNLOAD_URL} -> {destination}", flush=True)
        with urllib.request.urlopen(DOWNLOAD_URL, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if temporary.stat().st_size != EXPECTED_SIZE or md5(temporary) != EXPECTED_MD5:
            temporary.unlink(missing_ok=True)
            raise SystemExit("downloaded archive failed size or MD5 verification")
        temporary.replace(destination)
        print(f"Verified {destination} ({EXPECTED_SIZE} bytes, MD5 {EXPECTED_MD5}).")

    if args.extract:
        extraction_dir = args.output_dir / "correa-et-al-neurips2025"
        extraction_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(destination) as archive:
            root = extraction_dir.resolve()
            for member in archive.infolist():
                target = (root / member.filename).resolve()
                if not target.is_relative_to(root):
                    raise SystemExit(f"unsafe archive member path: {member.filename}")
            archive.extractall(extraction_dir)
        print(f"Extracted to {extraction_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
