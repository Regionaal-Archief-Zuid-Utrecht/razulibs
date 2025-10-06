import argparse
import sys
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPOSITORY_ID = "nl-wbdrazu"
LOCAL_EDEPOT_DIR = "/mnt/nas/edepot/"

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=("Synchronizes files from a SIP directory to the local e-depot instance using manifest checksums.")
    )
    p.add_argument("sipsdir", type=Path, help="Path of directory containing SIPs")
    p.add_argument(
        "--edepot-basedir",
        dest="edepot_basedir",
        type=Path,
        default=Path(LOCAL_EDEPOT_DIR),
        help="Base directory of local e-depot instance (default: %(default)s)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="More verbose output")
    return p.parse_args()


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
        force=True,  
    )


def find_sip_manifests(sipsdir: Path) -> Iterable[Path]:
    pattern = f"*/{REPOSITORY_ID}/*/*/*.manifest.json"
    yield from sipsdir.glob(pattern)


def extract_bucket_and_collection(manifest_path: Path) -> Tuple[str, str]:
    """
    Extract 'bucket' and 'collection' names from the path:
      .../{REPOSITORY_ID}/{bucket}/{collection}/<manifest>
    Returns (bucket, collection).
    """
    parts = manifest_path.parts
    try:
        idx = parts.index(REPOSITORY_ID)
        bucket = parts[idx + 1]
        collection = parts[idx + 2]
        return bucket, collection
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Unexpected manifest path structure: {manifest_path}") from exc


def corresponding_local_edepot_manifest(manifest_path: Path, bucket: str, collection: str) -> Path:
    """
    Construct correspondig local edepot instance manifest path:
      {LOCAL_EDEPOT_BASEDIR}/{bucket}/{REPOSITORY_ID}/{bucket}/{collection}/<manifest>
    """
    local_edepot_base = Path(LOCAL_EDEPOT_DIR)
    filename = manifest_path.name
    return local_edepot_base / bucket / REPOSITORY_ID / bucket / collection / filename


def read_manifest(path: Path) -> Dict[str, Dict[str, str]]:
    """Read a manifest file (JSON) and return as dict."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def differing_files(
    sip_manifest_data: Dict[str, Dict[str, str]],
    local_edepot_manifest_data: Dict[str, Dict[str, str]] | None,
) -> List[str]:
    """
    Compare MD5Hash per filename (key). Return list of file names
    (keys) where the hash differs or is missing in the local manifest.
    If local_edepot_manifest_data is None (missing), then all filenames (keys) are returned.
    """
    diffs: List[str] = []

    if local_edepot_manifest_data is None:
        return list(sip_manifest_data.keys())

    for relpath, meta in sip_manifest_data.items():
        sip_hash = meta.get("MD5Hash")
        local_hash = (local_edepot_manifest_data.get(relpath) or {}).get("MD5Hash")
        if not sip_hash or sip_hash != local_hash:
            diffs.append(relpath)
    return diffs


def process_manifest(sip_manifest_path: Path) -> List[str]:
    """
    Process one SIP manifest and return list of differing files.
    """
    bucket, collection = extract_bucket_and_collection(sip_manifest_path)
    local_edepot_manifest = corresponding_local_edepot_manifest(sip_manifest_path, bucket, collection)

    try:
        sip_data = read_manifest(sip_manifest_path)
    except Exception as e:
        logging.error("Cannot read SIP manifest: %s (%s)", sip_manifest_path, e)
        return []

    local_edepot_data = None
    if local_edepot_manifest.is_file():
        try:
            local_edepot_data = read_manifest(local_edepot_manifest)
        except Exception as e:
            logging.warning(
                "Cannot read local manifest, consider all files as different: %s (%s)",
                local_edepot_manifest,
                e,
            )
            local_edepot_data = None
    else:
        logging.error(
            "Local manifest missing: %s (all files are considered different)",
            local_edepot_manifest,
        )

    return differing_files(sip_data, local_edepot_data)


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    global REPOSITORY_ID, LOCAL_EDEPOT_DIR
    LOCAL_EDEPOT_DIR = str(args.edepot_basedir)

    sipsdir: Path = args.sipsdir
    if not sipsdir.is_dir():
        logging.error("SIP directory does not exist: %s", sipsdir)
        return 1

    if not Path(LOCAL_EDEPOT_DIR).is_dir():
        logging.error("Local e-depot directory does not exist: %s", LOCAL_EDEPOT_DIR)
        return 1

    manifests = list(find_sip_manifests(sipsdir))
    if not manifests:
        logging.error("No manifest files found under: %s", sipsdir)
        return 1

    total_diffs = 0
    for sip_manifest in sorted(manifests):
        try:
            bucket, collection = extract_bucket_and_collection(sip_manifest)
        except ValueError as e:
            logging.error(str(e))
            return 1

        logging.info(
            "Processing manifest: %s (bucket=%s, collection=%s)",
            sip_manifest,
            bucket,
            collection,
        )
        diffs = process_manifest(sip_manifest)
        if diffs:
            try:
                # Determine subcollection base (path up to REPOSITORY_ID)
                parts = sip_manifest.parts
                idx_repo = parts.index(REPOSITORY_ID)
                subcollection_dir = Path(*parts[:idx_repo])

                # Copy each new or differing file:
                for relpath in diffs:
                    src = subcollection_dir / relpath
                    dst = Path(LOCAL_EDEPOT_DIR) / bucket / relpath
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

                # Copy the manifest
                local_manifest_dst = corresponding_local_edepot_manifest(sip_manifest, bucket, collection)
                local_manifest_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sip_manifest, local_manifest_dst)
            except Exception as e:
                logging.error("Copy failed for manifest %s: %s", sip_manifest, e)
        total_diffs += len(diffs)

    logging.info("Done. Number of files synchronized: %d", total_diffs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())