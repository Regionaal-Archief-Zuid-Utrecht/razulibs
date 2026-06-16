from src.database import Database
from src.generator import IdentifierGenerator
from razu.config import Config
from rdflib import Namespace, RDF, URIRef, Literal, BNode
from razu.meta_graph import MetaGraph, LDTO, DCT, RAZU, XSD, BAG, SCHEMA, GEO, RDFS, OWL, PICO, PNV, SKOS, PREMIS, PO
import sqlite3
import pandas as pd
from razu.concept_resolver import ConceptBuilder, Concept
from razu.meta_resource import MetaResource, StructuredMetaResource
import os
import json


###############
# load sources
cfg = Config.initialize()

# load metadata path (throu cfg) 
script_directory = os.path.dirname(os.path.abspath(__file__))
metadata_db_path = os.path.join(script_directory, f"./{cfg.metadata_db_path}")
# load technical metadata db path (throu cfg) 
technical_metadata_path = os.path.join(script_directory, f"./{cfg.technical_metadata_path}")
# load identifiers db path (throu cfg) 
identifiers_db_path = os.path.join(script_directory, f"./{cfg.identifiers_db_path}")

id_generator = IdentifierGenerator(identifiers_db_path)

locatie_builder = ConceptBuilder('locatie')
classificate_builder = ConceptBuilder('soort')
format_builder = ConceptBuilder('bestandsformaat')
betrokkenheid_builder = ConceptBuilder('betrokkenheid')
aggregatieniveau_builder = ConceptBuilder("aggregatieniveau")

# graph = MetaGraph() # not needed, initialized with rdf_resource
private_graph = MetaGraph()

# extra
with open("kadnummer_base.json") as f:
    kadnummer_prefix_map = json.load(f)

# MAIS plaatsnamen that don't exist in BAG → map to BAG woonplaats
plaatsnaam_bag_map = {
    "Overlangbroek": "Langbroek",
}

def make_storage_url(gemeente_code, toegang_code, stepped_dir):
    return f"https://{gemeente_code}.opslag.razu.nl/nl-wbdrazu/{gemeente_code}/{toegang_code.zfill(3)}/{stepped_dir}"

###########

def main(gemeente_code, toegang_code):

    cfg = Config.get_instance()
      
    # Initialize the cfg with settings for this specific run
    cfg.add_properties(
        toegang_code=toegang_code,
        gemeente_code=gemeente_code,
        sip_directory=cfg.default_sip_directory
    )
    os.makedirs(cfg.sip_directory, exist_ok=True)

    archiefvormer_concept = ConceptBuilder('actor').get_concept_obj_from_term(gemeente_code)
    print(archiefvormer_concept)
    archiefvormer_uri = archiefvormer_concept.uri
    print(archiefvormer_uri)
    archiefvormer = archiefvormer_concept.get_value(SKOS.prefLabel)
    print(archiefvormer)

    # now call functions to write rdf :)
    create_archief_Informatieobject(toegang_code, gemeente_code, archiefvormer)

if __name__ == "__main__":
    main("g0352", "008")


# ARCHIEF

def create_archief_Informatieobject(toegang_code, gemeente_code, archiefvormer):
    
    cfg = Config.get_instance()
    
    # load metadata db path (throu cfg) 
    # script_directory = os.path.dirname(os.path.abspath(__file__))
    # metadata_db_path = os.path.join(script_directory, f"./{cfg.metadata_db_path}")

    # get node identifier
    identifier, is_new, stepped_dir = id_generator.generate(
    producer=gemeente_code,
    dataset=toegang_code,
    type="Informatieobject",
    aggregationlevel="Archief"
)
    # make subject
    subject = URIRef(f"{RAZU}{identifier}")
    
    # query for additional data
    with sqlite3.connect(metadata_db_path) as conn:
        row = conn.execute(
            "SELECT TITEL, DATERING, INLEIDING_TEKST FROM toegangen WHERE CODE = ?;",
            (toegang_code,),
        ).fetchone()
        naam = " ".join(row[:2]) if row else ""
    #    omschrijving = str(row[2]) if row and row[2] else ""
    omschrijving = input("Enter omschrijving: ")

    # make storage url (instead of identifiers.py)
    storage_url = make_storage_url(gemeente_code, toegang_code, stepped_dir)

    # add triples, initializing StructuredMetaResource
    archief = StructuredMetaResource(id=identifier, uri=subject)
    archief.add_properties({RDF.type: LDTO.Informatieobject,
                            DCT.hasFormat: URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"),
                            LDTO.naam: Literal(naam),
                            LDTO.omschrijving: Literal(omschrijving),
                            LDTO.archiefvormer: URIRef(archiefvormer),
                            LDTO.aggregatieniveau: URIRef(aggregatieniveau_builder.get_concept_obj_from_term("Archief").uri),
                            LDTO.identificatieGegevens: {
                                RDF.type: LDTO.IdentificatieGegevens,
                                LDTO.identificatieBron: Literal("Toegangen collectiebeheersysteem RAZU"),
                                LDTO.identificatieKenmerk: Literal(toegang_code)
                            }
                            })
    
    archief.add_triple(URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"), RDF.type, PREMIS.File)
    
    archief.save() # to change, 

    # we have additional data in db shouldn't we use them?: 
    # toegangen.AUTEUR 'L.C.J.M. Rouppe van der Voort, R.J. Butterman, M.A. van der Eerden-Vonk, K.Th.H. Wildenbeest, E.F.W. Hinders ;
    # toegangen.BEGINJAAR '1974' ;
    # toegangen.EINDJAAR '1961' ;
    # toegangen.DATERING_TOEGANG ' 1972; versie oktober 2021';
    # toegangen.OMVANG '59' ; (59 what? vierkantemeter?)
    # toegangen.OPMERKINGEN '' ;
    # .
    return True