import os
import sys
from rdflib import Graph

from razu.meta_resource import MDTO, PREMIS
from razu.manifest import Manifest 
from razu.concept_resolver import ConceptResolver 
import razu.util as util


def enrich_manifest(manifest_file, rdf_directory):

    actoren = ConceptResolver("actor")
    manifest = Manifest(rdf_directory, manifest_file)

    for rdf_file in os.listdir(rdf_directory):
        if rdf_file.endswith('.json') and rdf_file != os.path.basename(manifest_file):

            object_uid = util.filename_without_extensions(rdf_file)
            source = actoren.get_concept(util.extract_source_from_filename(rdf_file)).get_uri()
            dataset = util.extract_archive_from_filename(rdf_file)

            manifest.update_entry(rdf_file, {
                "ObjectUID": object_uid,
                "Source": source,
                "Dataset": dataset
            })

            rdf_path = os.path.join(rdf_directory, rdf_file)

            # RDF-bestand inlezen
            g = Graph()
            g.parse(rdf_path, format='json-ld')

            # SPARQL-query om de URLBestand en FileFormat op te halen
            query = """
            SELECT ?subject ?urlbestand ?bestandsformaat ?original_filename WHERE {
                ?subject mdto:URLBestand ?urlbestand .
                ?subject mdto:bestandsformaat ?bestandsformaat .
                ?subject premis:originalName ?original_filename
            }
            """
            results = g.query(query, initNs={'mdto': MDTO, 'premis': PREMIS})

            # Resultaten verwerken en manifest verrijken
            for row in results:
                filename = os.path.basename(str(row['urlbestand']))

                # Als de filenaam voorkomt in het manifest, voeg de FileFormat toe
                if filename in manifest.files:
                    file_format_data = {
                        "ObjectUID": object_uid,
                        "Source": source,
                        "Dataset": dataset,
                        "FileFormat": str(row['bestandsformaat']),
                        "OriginalFilename": str(row['original_filename'])
                    }
                    manifest.update_entry(filename, file_format_data)

    manifest.save()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Gebruik: python enrich_manifest.py <sip_directory> <manifest.json> ")
        sys.exit(1)

    sip_directory = sys.argv[1]
    manifest_file = sys.argv[2]

    enrich_manifest(manifest_file, sip_directory)
