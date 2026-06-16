# config first
from razu.config import Config
cfg = Config.initialize(config_file="config/config.yaml")

from src.database import Database # need tro install pip install -e /home/madda/coding/idgenerator
from src.generator import IdentifierGenerator
from rdflib import Namespace, RDF, URIRef, Literal, BNode
from razu.meta_graph import MetaGraph, LDTO, DCT, RAZU, XSD, BAG, SCHEMA, GEO, RDFS, OWL, PICO, PNV, SKOS, PREMIS, PO
import sqlite3
import pandas as pd
from razu.concept_resolver import ConceptBuilder, Concept
from razu.meta_resource import MetaResource, StructuredMetaResource
import os
import json
from tqdm import tqdm
import uuid
import re


###############
# load sources

_bag_csv = pd.read_csv("metadata/bag-adresses-new.csv", dtype=str)

# load metadata path (throu cfg) 
script_directory = os.path.dirname(os.path.abspath(__file__))
metadata_db_path = os.path.join(script_directory, f"./{cfg.metadata_db_path}")
bag_metadata_path = os.path.join(script_directory, f"./{cfg.bag_metadata_path}")

# load technical metadata db path (throu cfg) 
technical_metadata_path = os.path.join(script_directory, f"./{cfg.technical_metadata_path}")
# load identifiers db path (throu cfg) 
identifiers_db_path = Database(os.path.join(script_directory, f"./{cfg.identifiers_db_path}"))

id_generator = IdentifierGenerator(identifiers_db_path)

locatie_builder = ConceptBuilder('locatie')
classificate_builder = ConceptBuilder('soort')
format_builder = ConceptBuilder('bestandsformaat')
betrokkenheid_builder = ConceptBuilder('betrokkenheid')
aggregatieniveau_builder = ConceptBuilder("aggregatieniveau")
actor_builder = ConceptBuilder("actor")

graph = MetaGraph() # here only for final whole graph save in turtle format
private_graph = MetaGraph() # here only for final whole graph save in turtle format

woonplaats_cache = {}

# extra
with open("kadnummer_base.json") as f:
    kadnummer_prefix_map = json.load(f)

# MAIS plaatsnamen that don't exist in BAG → map to BAG woonplaats
plaatsnaam_bag_map = {
    "Overlangbroek": "Langbroek",
}

def make_storage_url(gemeente_code, toegang_code, stepped_dir):
    return f"https://{gemeente_code}.opslag.razu.nl/nl-wbdrazu/{gemeente_code}/{toegang_code.zfill(3)}/{stepped_dir}"


# ARCHIEF

def create_rdf(toegang_code, gemeente_code, archiefvormer):
    
    cfg = Config.get_instance()

    archiefvormer_uri = actor_builder.get_concept_obj_from_term(archiefvormer).uri

    # ARCHIEF

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
    with sqlite3.connect(metadata_db_path) as md_conn:
        row = md_conn.execute(
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
                            LDTO.archiefvormer: URIRef(archiefvormer_uri),
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

    # DOSSIER

    # import data
    data = pd.read_csv("metadata/mf-008-adresses-new.csv", dtype=str)
    
    prev_nummer = None
    dossier = None
    for i, row in tqdm(data.iterrows(), total=len(data), desc="Writing dossiers"): # (each row one file)
        invnummer = str(row['INVNUMMER'])
        if invnummer != prev_nummer:
            
            # save previous dossier before starting a new one
            if dossier is not None:
                dossier.save()

            # move on to new node
            # make node identifier
            identifier, is_new, stepped_dir = id_generator.generate(
                producer=gemeente_code,
                dataset=toegang_code,
                type="Informatieobject",
                aggregationlevel="Dossier",
                inventarisnummer=invnummer
            )

            # make subject
            subject = URIRef(f"{RAZU}{identifier}")

            # make storage url (instead of identifiers.py) OCCHIO THIS IS DOUBLED AND STORAGE URL OUTSIDE LOOP IS STH ELSE
            storage_url = make_storage_url(gemeente_code, toegang_code, stepped_dir)

            # Create new dossier MetaResource
            dossier = StructuredMetaResource(id=identifier, uri=subject)

            dossier.add_properties({RDF.type: LDTO.Informatieobject,
                                    DCT.hasFormat: URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"),
                                    LDTO.isOnderdeelVan: archief.uri,
                                    LDTO.archiefvormer: URIRef(archiefvormer_uri),
                                    LDTO.aggregatieniveau: URIRef(aggregatieniveau_builder.get_concept_obj_from_term("Dossier").uri), 
                                    LDTO.classificatie: URIRef("https://data.razu.nl/id/soort/83f5430a921350f53972970595d2790c"), # always "Bouwdossier" for now
                                    LDTO.identificatie: {
                                        RDF.type: LDTO.IdentificatieGegevens,
                                        LDTO.identificatieBron: Literal(f"RAZU, inventarisnummer toegang {toegang_code}"),
                                        LDTO.identificatieKenmerk: Literal(invnummer)
                                    },
                                    LDTO.dekkingInTijd: {
                                        RDF.type: LDTO.DekkingInTijdGegevens,
                                        LDTO.dekkingInTijdType: URIRef("https://data.razu.nl/id/dekkingintijdtype/70a06aa707497017b24a599d24a4f9c9"), # Tijdsbestek
                                        LDTO.dekkingInTijdBeginDatum: Literal(row['DATERING'], datatype=XSD.gYear)
                                    }
                                    })
            archief.add_triple(URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"), RDF.type, PREMIS.File)

            # logic for LDTO.naam
            # Dossier - toegang - invnummer + bouwerk + street name + placename (+perceel) (at dossier level, kinda better to leave out the address, we can always index in es the adress name!)
            bouwwerk = row['BOUWWERK'] if pd.notna(row['BOUWWERK']) else ""
            straatnaam = row['STRAATNAAM'] if pd.notna(row['STRAATNAAM']) else ""
            plaatsnaam = row['PLAATSNAAM'] if pd.notna(row['PLAATSNAAM']) else ""
            omschrijving = " - ".join(part for part in ["Dossier", f"toegang {toegang_code}", f"invnummer {invnummer}", bouwwerk, straatnaam, plaatsnaam] if part)

            dossier.add_property(LDTO.naam, Literal(omschrijving))

            # add adres data
            write_adres_graph(graph, dossier, row)

            # add actor data
            write_actor_graph(graph, dossier, row)

            prev_nummer = invnummer

        else:
            # same node, add new adress only and actor only
            write_adres_graph(graph, dossier, row)

    # save the last dossier
    if dossier is not None:
        dossier.save()

    return True

######## helpers ################

def get_nummeraanduiding_from_csv(adrs_data: pd.Series) -> dict | None:
    huisnummers = adrs_data['HUISNUMMERS'] if pd.notna(adrs_data['HUISNUMMERS']) else ""
    straatnaam = adrs_data['STRAATNAAM'] if pd.notna(adrs_data['STRAATNAAM']) else ""
    plaatsnaam = bag_plaatsnaam(adrs_data['PLAATSNAAM']) if pd.notna(adrs_data['PLAATSNAAM']) else ""

    match = _bag_csv[
        (_bag_csv['huisnummer'] == huisnummers) &
        (_bag_csv['straatnaam'] == straatnaam) &
        (_bag_csv['plaatsnaam'] == plaatsnaam)
    ]

    if match.empty:
        return None

    result = match.iloc[0]
    raw_huisnummer = result['huisnummer']
    nummer, letter = split_huisnummer(raw_huisnummer)
    label_huisnummer = f"{nummer}{letter}" if letter else str(nummer)
    d = {
        RDFS.label: Literal(f"{result['straatnaam']} {label_huisnummer}, {result['plaatsnaam']}"),
        BAG.huisnummer: Literal(nummer, datatype=XSD.integer),
    }
    if letter:
        d[BAG.huisletter] = Literal(letter)
    return d

def get_openbareruimte_from_db(adrs_data: pd.Series) -> dict | None:
    with sqlite3.connect(bag_metadata_path) as bag_conn:
        cursor = bag_conn.cursor()
        cursor.execute('''select OpenbareRuimte.bagID, OpenbareRuimte.naam from OpenbareRuimte join WPL on OpenbareRuimte.ligtIn == WPL.identificatie where OpenbareRuimte.naam = ? and WPL.naam = ?''', (adrs_data['STRAATNAAM'], bag_plaatsnaam(adrs_data['PLAATSNAAM'])))
        result = cursor.fetchall()
        if result:
            return { 
                RDF.type: BAG.OpenbareRuimte,
                BAG.naam: Literal(adrs_data['STRAATNAAM']),
                BAG.bagID: Literal(result[0][0]),
                OWL.sameAs: URIRef(f"https://bag.basisregistraties.overheid.nl/bag/id/openbare-ruimte/{result[0][0]}") # ! N.B. in Woonplaats from the thesaurus the bag uri uses property skos:exactMatch
                }
        return None

def get_geometry_from_csv(adrs_data: pd.Series) -> dict | None:
    huisnummers = adrs_data['HUISNUMMERS'] if pd.notna(adrs_data['HUISNUMMERS']) else ""
    straatnaam = adrs_data['STRAATNAAM'] if pd.notna(adrs_data['STRAATNAAM']) else ""
    plaatsnaam = bag_plaatsnaam(adrs_data['PLAATSNAAM']) if pd.notna(adrs_data['PLAATSNAAM']) else ""

    match = _bag_csv[
        (_bag_csv['huisnummer'] == huisnummers) &
        (_bag_csv['straatnaam'] == straatnaam) &
        (_bag_csv['plaatsnaam'] == plaatsnaam)
    ]

    if match.empty:
        return None

    result = match.iloc[0]
    if pd.notna(result['longitude']) and pd.notna(result['latitude']):
        asWKT = f"POINT({result['longitude']} {result['latitude']})"
        return {
            RDF.type: GEO.Geometry,
            RDFS.label: Literal("Representatief punt"),
            GEO.asWKT: Literal(asWKT, datatype=GEO.wktLiteral),
            GEO.crs: URIRef("http://www.opengis.net/example")
        }
    return None

def get_actors_from_db(row: pd.Series) -> list | None: # returns a list of dictionaries
    with sqlite3.connect(metadata_db_path) as actor_conn:
        cursor = actor_conn.cursor()
        cursor.execute('''select piv.ROL, piv.VOORLETTERS, piv.TUSSENVOEGSEL, piv.ACHTERNAAM, rpiv.ROL as ROL_RPIV, rpiv.ORGANISATIENAAM from bd left join toegangen on bd.TOEGANG_ID == toegangen.ID left join piv on bd.ID == piv.BD_ID left join rpiv on bd.ID == rpiv.BD_ID where toegangen.CODE == ? and bd.ID == ?;''', (row['CODE'], row['BD_ID']))
        result = cursor.fetchall()
        if result: # [('404', '1038518', 'Ring-vlamoven', '', '1935', '1935-1', None, None, None, None, None, None)]
            actor_list = []
            for actor_row in result:
                if actor_row[3]:  # ACHTERNAAM
                    name = f"{actor_row[1] or ''} {actor_row[2] or ''} {actor_row[3] or ''}".strip()
                    actor_list.append({
                        "type": PNV.PersonName,
                        "rol": actor_row[0],  # piv.ROL
                        "data": {
                            RDF.type: PNV.PersonName,
                            PNV.literalName: Literal(name),
                            # PNV.givenName: Literal(actor_row[1] if actor_row[1] else ""),
                            # PNV.baseSurname: Literal(actor_row[2] if actor_row[2] else ""),
                            PNV.baseSurname: Literal(actor_row[3] if actor_row[3] else "")
                        }
                    })
                if actor_row[5]:  # ORGANISATIENAAM
                    actor_list.append({
                        "type": SCHEMA.Organisation,
                        "rol": actor_row[4],  # rpiv.ROL
                        "data": {
                            RDF.type: [SCHEMA.Organisation, LDTO.Actor],
                            RDFS.label: Literal(actor_row[5])
                        }
                    })

            return actor_list if actor_list else None
        return None

def make_actor_uri(actor_dict):
    """Generate a unique URI for each actor instance using a UUID."""
    uid = uuid.uuid4().hex
    if actor_dict["type"] == PNV.PersonName:
        return URIRef(f"{PO}{uid}")
    else:
        return URIRef(f"{SCHEMA}organization/{uid}")

def bag_plaatsnaam(plaatsnaam):
    """Map MAIS plaatsnaam to BAG woonplaats name if needed."""
    return plaatsnaam_bag_map.get(plaatsnaam, plaatsnaam)

def split_huisnummer(value):
    """Split '116B' into (116, 'b') or '23' into (23, None)."""
    match = re.match(r"(\d+)([A-Za-z]*)$", str(value).strip())
    if match:
        nummer = int(match.group(1))
        letter = match.group(2).lower() if match.group(2) else None
        return nummer, letter
    return None, None

def write_adres_graph(graph, subject, row): # N.B. skipping perceelen data for now

    # make nummeraanduiding dictionary
    nummeraanduiding_dict = get_nummeraanduiding_from_csv(row)  

    if not nummeraanduiding_dict:
        # make dict from mais flexis data
        nummeraanduiding_dict = {}
        straatnaam = row['STRAATNAAM'] if pd.notna(row['STRAATNAAM']) else ""
        huisnummers = row['HUISNUMMERS'] if pd.notna(row['HUISNUMMERS']) else ""
        plaatsnaam = row['PLAATSNAAM'] if pd.notna(row['PLAATSNAAM']) else ""
        if huisnummers:
            nummer, letter = split_huisnummer(huisnummers)
            label_huisnummer = f"{nummer}{letter}" if letter else str(nummer) if nummer else huisnummers
            street_part = f"{straatnaam} {label_huisnummer}".strip()
            if nummer:
                nummeraanduiding_dict[BAG.huisnummer] = Literal(nummer, datatype=XSD.integer)
            if letter:
                nummeraanduiding_dict[BAG.huisletter] = Literal(letter)
        else:
            street_part = straatnaam

        label = ", ".join(part for part in [street_part, plaatsnaam] if part)
        nummeraanduiding_dict[RDFS.label] = Literal(label)

        nummeraanduiding_dict[RDF.type] = [SCHEMA.PostalAddress, BAG.Nummeraanduiding]
        type_adres = row['ROL_ADRES']
        if type_adres == 'Oud adres':
            nummeraanduiding_dict[RDFS.comment] = Literal("Historisch adres")
    
    # make openbareruimte dictionary
    openbareruimte_dict = get_openbareruimte_from_db(row)    # openbareruimte

    if openbareruimte_dict:
        nummeraanduiding_dict[BAG.ligtAan] = openbareruimte_dict

    # make geometry dictionary
    geo_dict = get_geometry_from_csv(row)

    if not geo_dict:
        geo_dict = {}
        geo_dict[GEO.asWKT] = Literal("POINT EMPTY", datatype=GEO.wktLiteral)
        geo_dict[GEO.crs] = URIRef("http://www.opengis.net/example")
        geo_dict[RDF.type] = GEO.Geometry
        geo_dict[RDFS.label] = Literal("Geen geometrie beschikbaar")


    # woonplaats (it's already in our thesaurus, hence get it from there)
    plaatsnaam = row['PLAATSNAAM']
    if plaatsnaam not in woonplaats_cache:
        woonplaats_cache[plaatsnaam] = locatie_builder.get_concept_obj_from_term(plaatsnaam) # Concept object
            
    woonplaats = woonplaats_cache[plaatsnaam] 
    
    if woonplaats:
        nummeraanduiding_dict[BAG.ligtIn] = woonplaats.uri

        # add woonplaats triples to graph
        # for match in woonplaats.get_values(SKOS.exactMatch):
        #     dossier.add_triple(woonplaats.uri, SKOS.exactMatch, URIRef(match))
        # for scheme in woonplaats.get_values(SKOS.inScheme):
        #     dossier.add_triple(woonplaats.uri, SKOS.inScheme, URIRef(scheme))
        
    
    # add adress triples!! finally

    subject.add_properties({
        LDTO.dekkingInRuimte: {
            RDF.type: [LDTO.Locatie, BAG._AdresseerbaarObject],
            SCHEMA.address: nummeraanduiding_dict,
            GEO.hasGeometry: geo_dict
        }     
    })

    return 'adres graph created: for subject ' + str(subject)

def write_actor_graph(graph, subject, row):
    global private_graph
    actors = get_actors_from_db(row) 

    # N.B. actors = list, actors_dict = dict
    if actors:
        for actor_dict in actors:
            actor_uri = make_actor_uri(actor_dict)

            subject.add_properties({
                LDTO.betrokkene: {
                    RDF.type: LDTO.BetrokkeneGegevens,
                    LDTO.betrokkeneTypeRelatie: URIRef(betrokkenheid_builder.get_concept_obj_from_term(actor_dict["rol"]).uri), 
                }
            })

            if actor_dict["type"] == PNV.PersonName: # make separate graph
                actor = StructuredMetaResource(uri=actor_uri)
                actor.add_properties({
                    RDF.type: [PICO.PersonObservation, LDTO.Actor],
                    PNV.hasName: actor_dict["data"]
                })  

                private_graph += actor.graph

                # add to public:
                subject.add_properties({
                    LDTO.betrokkeneActor: actor_uri
                })
                subject.add_triple(actor_uri, RDF.type, LDTO.Actor)
                subject.add_triple(actor_uri, RDF.type, PICO.PersonObservation)

            elif actor_dict["type"] == SCHEMA.Organisation:
                subject.add_properties({
                    LDTO.betrokkeneActor: actor_dict["data"]
                })

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

    archiefvormer_concept = actor_builder.get_concept_obj_from_term(gemeente_code)
    archiefvormer = archiefvormer_concept.get_value(SKOS.prefLabel)

    # now call functions to write rdf :)
    create_rdf(toegang_code, gemeente_code, archiefvormer)

if __name__ == "__main__":
    main("g0352", "008")


