#!/usr/bin/env python3
import argparse
import sys
from rdflib import Graph

COMMON_FORMATS = [
    None,           # Let rdflib guess from file extension
    "turtle",
    "xml",        # RDF/XML
    "n3",
    "nt",
    "trig",
    "nquads",
    "json-ld",
    "trix",
]

def parse_rdf_file(path: str) -> Graph:
    g = Graph()
    last_err = None
    for fmt in COMMON_FORMATS:
        try:
            # rdflib will guess by file extension if format=None
            g.parse(path, format=fmt)
            return g
        except Exception as e:
            last_err = e
            # Clear graph before next attempt
            g = Graph()
            continue
    # If all attempts failed, raise the last error
    raise last_err if last_err else RuntimeError("Unable to parse RDF file.")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Print RDF content of a file as Turtle serialization"
    )
    parser.add_argument(
        "input",
        help="Path to the input file containing RDF. Format will be auto-detected; common RDF formats are tried."
    )
    args = parser.parse_args(argv)

    try:
        g = parse_rdf_file(args.input)
    except Exception as e:
        sys.stderr.write(f"Kon bestand niet als RDF parsen: {e}\n")
        return 1

    try:
        turtle = g.serialize(format="turtle")
        # rdflib serialize returns str in recent versions, bytes in some older ones
        if isinstance(turtle, bytes):
            turtle = turtle.decode("utf-8")
        sys.stdout.write(turtle)
        sys.stdout.flush()
    except Exception as e:
        sys.stderr.write(f"Kon RDF niet als Turtle serialiseren: {e}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
