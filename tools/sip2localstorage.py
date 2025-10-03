import argparse
import sys
import json
import shutil
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


# Constantes (aanpasbaar via CLI)
REPOSITORY_ID = "nl-wbdrazu"
LOCAL_EDEPOT_DIR = "/mnt/nas/edepot/"

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Vergelijk SIP-manifesten met lokale e-depot-manifesten en print afwijkende bestanden."
        )
    )
    p.add_argument("sipsdir", type=Path, help="Pad naar directory met SIP-subcollecties")
    p.add_argument(
        "--edepot-basedir",
        dest="edepot_basedir",
        type=Path,
        default=Path(LOCAL_EDEPOT_DIR),
        help="Basismap lokale e-depot (default: %(default)s)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Meer loguitvoer")
    return p.parse_args()


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stdout,
        force=True,  # overschrijf bestaande logging-configuratie zodat output zichtbaar is
    )


def find_sip_manifests(sipsdir: Path) -> Iterable[Path]:
    """
    Vind alle manifest-bestanden onder:
      {sipsdir}/*/{REPOSITORY_ID}/*/*/*.manifest.json
    """
    pattern = f"*/{REPOSITORY_ID}/*/*/*.manifest.json"
    yield from sipsdir.glob(pattern)


def extract_bucket_en_toegang(manifest_path: Path) -> Tuple[str, str]:
    """
    haal 'bucket' en 'toegang' uit het pad:
      .../{REPOSITORY_ID}/{bucket}/{toegang}/<manifest>
    Retourneert (bucket, toegang).
    """
    parts = manifest_path.parts
    try:
        idx = parts.index(REPOSITORY_ID)
        bucket = parts[idx + 1]
        toegang = parts[idx + 2]
        return bucket, toegang
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Onverwachte padstructuur voor manifest: {manifest_path}") from exc


def corresponding_local_edepot_manifest(manifest_path: Path, bucket: str, toegang: str) -> Path:
    """
    Construeer pad naar corresponderend lokaal manifest:
      {LOCAL_EDEPOT_BASEDIR}/{bucket}/{REPOSITORY_ID}/{bucket}/{toegang}/<bestandsnaam>
    """
    local_edepot_base = Path(LOCAL_EDEPOT_DIR)
    filename = manifest_path.name
    return local_edepot_base / bucket / REPOSITORY_ID / bucket / toegang / filename


def read_manifest(path: Path) -> Dict[str, Dict[str, str]]:
    """Lees een manifestbestand (JSON) en retourneer als dict."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def differing_files(
    sip_manifest_data: Dict[str, Dict[str, str]],
    local_edepot_manifest_data: Dict[str, Dict[str, str]] | None,
) -> List[str]:
    """
    Vergelijk MD5Hash per bestandssleutel. Retourneer lijst met bestandsnamen
    (sleutels) waar de hash afwijkt of ontbreekt in het lokale manifest.
    Als local_edepot_manifest_data None is (ontbreekt), dan worden alle sleutels geretourneerd.
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
    Verwerk één SIP-manifest en geef de lijst met afwijkende bestanden terug.
    """
    bucket, toegang = extract_bucket_en_toegang(sip_manifest_path)
    local_edepot_manifest = corresponding_local_edepot_manifest(sip_manifest_path, bucket, toegang)

    try:
        sip_data = read_manifest(sip_manifest_path)
    except Exception as e:
        logging.error("Kan SIP-manifest niet lezen: %s (%s)", sip_manifest_path, e)
        return []

    local_edepot_data = None
    if local_edepot_manifest.is_file():
        try:
            local_edepot_data = read_manifest(local_edepot_manifest)
        except Exception as e:
            logging.warning(
                "Kan lokaal manifest niet lezen, neem alle bestanden op als afwijkend: %s (%s)",
                local_edepot_manifest,
                e,
            )
            local_edepot_data = None
    else:
        logging.info(
            "Lokaal manifest ontbreekt: %s (alle bestanden worden als afwijkend beschouwd)",
            local_edepot_manifest,
        )

    return differing_files(sip_data, local_edepot_data)


def build_copy_commands(
    sipsdir: Path,
    sip_manifest_path: Path,
    bucket: str,
    toegang: str,
    differing_relpaths: List[str],
) -> List[str]:
    """
    Genereer shell-commando's (zonder uit te voeren) om gewijzigde bestanden te kopiëren
    van de SIP-structuur naar de lokale e-depot-structuur. Als er wijzigingen zijn,
    wordt ook een commando geprint om het manifest-bestand zelf te kopiëren.

    - Bronbestand:  {subcollectie_dir}/{relpath}
    - Doelbestand:  {LOCAL_EDEPOT_DIR}/{bucket}/{relpath}
    - Manifest-doel: {LOCAL_EDEPOT_DIR}/{bucket}/{REPOSITORY_ID}/{bucket}/{toegang}/{manifestname}
    """
    if not differing_relpaths:
        return []

    # Bepaal subcollectie-basis (pad tot aan REPOSITORY_ID)
    parts = sip_manifest_path.parts
    try:
        idx_repo = parts.index(REPOSITORY_ID)
    except ValueError as exc:
        raise ValueError(f"REPOSITORY_ID niet gevonden in pad: {sip_manifest_path}") from exc
    subcollectie_dir = Path(*parts[:idx_repo])

    commands: List[str] = []

    # Commando's voor alle gewijzigde bestanden
    for relpath in differing_relpaths:
        src = subcollectie_dir / relpath
        dst = Path(LOCAL_EDEPOT_DIR) / bucket / relpath
        dst_dir = dst.parent
        commands.append(f'mkdir -p "{dst_dir}"')
        commands.append(f'cp -p "{src}" "{dst}"')

    # Ook het manifest zelf kopiëren
    local_manifest_dst = corresponding_local_edepot_manifest(sip_manifest_path, bucket, toegang)
    commands.append(f'mkdir -p "{local_manifest_dst.parent}"')
    commands.append(f'cp -p "{sip_manifest_path}" "{local_manifest_dst}"')

    return commands
def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    # Werk met eventuele overrides voor constante waarden
    global REPOSITORY_ID, LOCAL_EDEPOT_DIR
    LOCAL_EDEPOT_DIR = str(args.edepot_basedir)

    sipsdir: Path = args.sipsdir
    if not sipsdir.is_dir():
        logging.error("Directory bestaat niet: %s", sipsdir)
        return 1

    if not Path(LOCAL_EDEPOT_DIR).is_dir():
        logging.error("Lokale e-depot directory bestaat niet: %s", LOCAL_EDEPOT_DIR)
        return 1

    manifests = list(find_sip_manifests(sipsdir))
    if not manifests:
        logging.warning("Geen manifest-bestanden gevonden onder: %s", sipsdir)
        return 0

    total_diffs = 0
    for sip_manifest in sorted(manifests):
        try:
            bucket, toegang = extract_bucket_en_toegang(sip_manifest)
        except ValueError as e:
            logging.warning(str(e))
            continue

        logging.info(
            "Vergelijk manifest: %s (bucket=%s, toegang=%s)",
            sip_manifest,
            bucket,
            toegang,
        )
        diffs = process_manifest(sip_manifest)
        if diffs:
            try:
                # Bepaal subcollectie-basis (pad tot aan REPOSITORY_ID)
                parts = sip_manifest.parts
                idx_repo = parts.index(REPOSITORY_ID)
                subcollectie_dir = Path(*parts[:idx_repo])

                # Kopieer elk gewijzigd bestand
                for relpath in diffs:
                    src = subcollectie_dir / relpath
                    dst = Path(LOCAL_EDEPOT_DIR) / bucket / relpath
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

                # Kopieer het manifest zelf
                local_manifest_dst = corresponding_local_edepot_manifest(sip_manifest, bucket, toegang)
                local_manifest_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sip_manifest, local_manifest_dst)
            except Exception as e:
                logging.error("Kopiëren mislukt voor manifest %s: %s", sip_manifest, e)
        total_diffs += len(diffs)

    logging.info("Gereed. Aantal afwijkende bestanden: %d", total_diffs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())