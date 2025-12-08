"""
Collects RDF of all metadata files from a manifest into a single file, ensuring that all bnodes are unique.
"""

import sys
import json
import re
import argparse
from pathlib import Path
from rdflib import Graph, Literal, URIRef, BNode
from rdflib.namespace import XSD

def _manifest_base_dir_from_arg(manifest_path: Path) -> Path:
    # The files mentioned in the manifest are relative to the directory above 'nl-wbdrazu' in the manifest path.
    parts = manifest_path.parts
    if 'nl-wbdrazu' in parts:
        idx = parts.index('nl-wbdrazu')
        return Path(*parts[:idx])
    else:
        print(f"Error: Could not determine base directory, 'nl-wbdrazu' not found in path '{manifest_path}'.")
        sys.exit(1)

def _manifest_path_from_arg(path_arg: str) -> Path:
    path = Path(path_arg).resolve()
    if path.is_dir():
        path = path / 'manifest.json'
    if not path.exists():
        print(f"Manifest not found: {path}")
        sys.exit(1)
    return path

def _output_path_from_arg(outfile: str) -> Path:
    if outfile:
        return Path(outfile)
    return Path.cwd() / 'out.ttl'

def _remap_bnodes(graph, suffix) -> Graph:
    mapping = {}
    new_graph = Graph()
    for s, p, o in graph:
        if isinstance(s, BNode):
            if s not in mapping:
                mapping[s] = BNode(f"{str(s)}_{suffix}")
            s2 = mapping[s]
        else:
            s2 = s
        if isinstance(o, BNode):
            if o not in mapping:
                mapping[o] = BNode(f"{str(o)}_{suffix}")
            o2 = mapping[o]
        else:
            o2 = o
        new_graph.add((s2, p, o2))
    return new_graph


def _is_valid_integer_lexical(lex: str) -> bool:
    if lex is None:
        return False
    return bool(re.fullmatch(r"[+-]?\d+", str(lex)))


def collect_rdf(manifest_path_arg, outfile=None):
    manifest_path = _manifest_path_from_arg(manifest_path_arg)
    output_path = _output_path_from_arg(outfile)
    manifest_base_dir = _manifest_base_dir_from_arg(manifest_path)

    print(f"Manifest file: {manifest_path}")
    print(f"Base directory: {manifest_base_dir}")
    print(f"Output file: {output_path}")

    # Read manifest
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_data = json.load(f)

    # Collect all meta.json files
    meta_files = [fname for fname in manifest_data.keys() if fname.endswith('meta.json')]
    print(f"Found {len(meta_files)} meta.json files in manifest.")

    g = Graph()
    for i, fname in enumerate(meta_files, 1):
        meta_path = manifest_base_dir / fname
        if not meta_path.exists():
            print(f"  [{i}/{len(meta_files)}] File not found: {meta_path}")
            continue
        try:
            temp_g = Graph()
            # read json-ld
            with open(meta_path, 'rb') as f_meta:
                temp_g.parse(file=f_meta, format='json-ld')
            
            # Validate integer-literals in this file to prevent crashes during serialization
            invalids = []
            replacements = []
            for s, p, o in list(temp_g):
                if isinstance(o, Literal) and o.datatype == XSD.integer:
                    lex = str(o)
                    if not _is_valid_integer_lexical(lex):
                        invalids.append((s, p, o))
                        # Convert to plain string literal to prevent serialization crashes
                        replacements.append((s, p, Literal(lex)))
            if invalids:
                print(f"  [{i}/{len(meta_files)}] Invalid xsd:integer values found in: {fname}")
                for s, p, o in invalids[:10]:  # show max 10
                    print(f"    - {p.split('/')[-1] if isinstance(p, URIRef) else p}: '{str(o)}' bij subject {s}")
                if len(invalids) > 10:
                    print(f"    ... en {len(invalids) - 10} meer in {fname}")
                # 
                for (s, p, o_old), (_, _, o_new) in zip(invalids, replacements):
                    temp_g.remove((s, p, o_old))
                    temp_g.add((s, p, o_new))
            
            suffix = meta_path.name.replace('.meta.json', '')
            temp_g = _remap_bnodes(temp_g, suffix)
            g += temp_g
            print(f"\r  [{i}/{len(meta_files)}] Read: {fname}".ljust(100), end="", flush=True)
        except Exception as e:
            print(f"  [{i}/{len(meta_files)}] Error reading {fname}: {e}")

    print()
    # Check for invalid triples before serializing
    invalid_triples = []
    for triple in g:
        s, p, o = triple
        if not (isinstance(s, (URIRef, BNode)) and isinstance(p, URIRef) and isinstance(o, (URIRef, BNode, Literal))):
            invalid_triples.append(triple)
    if invalid_triples:
        print(f"Warning: {len(invalid_triples)} invalid triples found. Removing them:")
        for t in invalid_triples:
            print(f"  Invalid triple: {t}")
        for t in invalid_triples:
            g.remove(t)
            
    # Graph save as turtle
    g.serialize(destination=output_path, format='turtle')
    print(f"Merged RDF saved as: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect RDF data from a manifest to a single file.")
    parser.add_argument("manifest", help="Path to manifest file or directory containing manifest.json")
    parser.add_argument("outfile", nargs="?", help="Optional output file (default: out.ttl in current directory)")
    
    args = parser.parse_args()
    
    collect_rdf(args.manifest, args.outfile)
