# config first
from razu.config import Config
cfg = Config.initialize(config_file="config/config.yaml")

from src.database import Database # need tro install pip install -e /home/madda/coding/idgenerator
from src.generator import IdentifierGenerator
from rdflib import Namespace, RDF, URIRef, Literal, BNode
from razu.meta_graph import MetaGraph, LDTO, DCT, RAZU, XSD, BAG, SCHEMA, GEO, RDFS, OWL, PICO, PNV, SKOS, PREMIS, PN, PROV
import sqlite3
import pandas as pd
from razu.concept_resolver import ConceptBuilder, Concept
from razu.meta_resource import MetaResource, StructuredMetaResource
import os
import json
from tqdm import tqdm
import uuid
import re
from datetime import datetime


###############
# load sources

_bag_csv = pd.read_csv("metadata/bag-adresses-new.csv", dtype=str)

class DBConnection:
    """Manages sqlite database connections. Use as context manager."""
    def __init__(self, db_path: str): # a cfg.path obj?

        base = os.path.dirname(os.path.abspath(__file__))
        self.conn = sqlite3.connect(os.path.join(base, f"./{db_path}"))

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        

metadata_db = DBConnection(cfg.metadata_db_path)
bag_db = DBConnection(cfg.bag_metadata_path)
identifiers_db = Database(cfg.identifiers_db_path)

id_generator = IdentifierGenerator(identifiers_db)

locatie_builder = ConceptBuilder('locatie')
classificate_builder = ConceptBuilder('soort')
format_builder = ConceptBuilder('bestandsformaat')
betrokkenheid_builder = ConceptBuilder('betrokkenheid')
aggregatieniveau_builder = ConceptBuilder("aggregatieniveau")
actor_builder = ConceptBuilder("actor")

graph = MetaGraph() # here only for final whole graph save in turtle format
private_graph = MetaGraph() # here only for final whole graph save in turtle format

woonplaats_cache = {}

# MAIS plaatsnamen that don't exist in BAG → map to BAG woonplaats
plaatsnaam_bag_map = {
    "Overlangbroek": "Langbroek",
}

def make_storage_url(gemeente_code, toegang_code, stepped_dir):
    return f"https://{gemeente_code}.opslag.razu.nl/nl-wbdrazu/{gemeente_code}/{toegang_code.zfill(3)}/{stepped_dir}"


#####################################
# ARCHIEF

def create_rdf(toegang_code, gemeente_code, archiefvormer):
    global graph
    
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
    row = metadata_db.conn.execute(
            "SELECT TITEL, DATERING, INLEIDING_TEKST FROM toegangen WHERE CODE = ?;",
            (toegang_code,),
        ).fetchone()
    naam = " ".join(row[:2]) if row else ""
    #    omschrijving = str(row[2]) if row and row[2] else ""
    omschrijving = "tmp"
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
    graph += archief.graph

    # we have additional data in db shouldn't we use them?: 
    # toegangen.AUTEUR 'L.C.J.M. Rouppe van der Voort, R.J. Butterman, M.A. van der Eerden-Vonk, K.Th.H. Wildenbeest, E.F.W. Hinders ;
    # toegangen.BEGINJAAR '1974' ;
    # toegangen.EINDJAAR '1961' ;
    # toegangen.DATERING_TOEGANG ' 1972; versie oktober 2021';
    # toegangen.OMVANG '59' ; (59 what? vierkantemeter?)
    # toegangen.OPMERKINGEN '' ;
    # .

########################################
    # DOSSIER - ARCHIEFSTUK - BESTAND

    # import data (provisional method here)
    data = pd.read_csv("metadata/mf-008-adresses.csv", dtype=str)
    technical_metadata = pd.read_csv("metadata/8_bestand.csv", dtype=str)
    
    prev_nummer = None
    dossier = None
    for i, row in tqdm(data.iterrows(), total=len(data), desc="Writing dossiers"): # (each row one file)
        invnummer = str(row['INVNUMMER'])
        if invnummer != prev_nummer:
            
            # save previous dossier before starting a new one
            if dossier is not None:
                dossier.save()
                graph += dossier.graph

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

            # CREATE ARCHIEFSTUK AND BESTAND FOR THIS DOSSIER ########################
            archiefstuk_metadata = technical_metadata[technical_metadata['INVNUMMER'] == invnummer] # already filtered per toegang
            create_archiefstuk_Informatieobject(archiefstuk_metadata, invnummer, dossier, toegang_code, gemeente_code, archiefvormer_uri)

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
            dossier.add_triple(URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"), RDF.type, PREMIS.File)

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
        graph += dossier.graph

    return graph, private_graph


def create_archiefstuk_Informatieobject(archiefstuk_metadata, invnummer, dossier, toegang_code, gemeente_code, archiefvormer_uri):
    global graph
    cfg = Config.get_instance()

    # get classifications:
    bouwvergunning = classificate_builder.get_concept_obj_from_term('Bouwvergunning').uri
    aanvraag_vergunning = classificate_builder.get_concept_obj_from_term('Aanvraag vergunning').uri
    tekening = classificate_builder.get_concept_obj_from_term('Bouwtekening').uri
    overig = classificate_builder.get_concept_obj_from_term('Document - niet nader gespecificeerd').uri

    archiefstuk = None

    for i, row in archiefstuk_metadata.iterrows():
        filepath = row["FILE_PATH"]

        # check if filepath contains a specific classification
        has_classification = any(kw in filepath for kw in
            ["TAB", "AANVRAAG-EN-VERGUNNING", "TEKENINGEN", "OVERIGE-DOCUMENTEN", "Overig", "Tekeningen", "Aanvraag_vergunning"])

        # create new archiefstuk if: first iteration (no archiefstuk yet) OR has classification
        need_new_archiefstuk = (archiefstuk is None) or has_classification

        if need_new_archiefstuk:
            # get archiefstuk identifier
            identifier, is_new, stepped_dir = id_generator.generate(
                producer=gemeente_code,
                dataset=toegang_code,
                type="Informatieobject",
                aggregationlevel="Archiefstuk",
                inventarisnummer=invnummer,
                filepath=filepath
            )
            # make subject
            subject = URIRef(f"{RAZU}{identifier}")

            # make storage url
            storage_url = make_storage_url(gemeente_code, toegang_code, stepped_dir)

            # Create new archiefstuk MetaResource
            archiefstuk = StructuredMetaResource(id=identifier, uri=subject)

            # add triples
            archiefstuk.add_properties({RDF.type: LDTO.Informatieobject,
                                DCT.hasFormat: URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"),
                                LDTO.aggregatieniveau: URIRef(aggregatieniveau_builder.get_concept_obj_from_term("Archiefstuk").uri),
                                LDTO.isOnderdeelVan: dossier.uri,
                                LDTO.archiefvormer: URIRef(archiefvormer_uri),
                                })

            archiefstuk.add_triple(URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}"), RDF.type, PREMIS.File)

            if has_classification:
                # OPTIONAL triples
                # get archiefstuk classification from filepath

                if "TAB" in filepath:
                    archiefstuk.add_property(LDTO.classificatie, URIRef("https://data.razu.nl/id/soort/tab"))
                    archiefstuk.add_property(LDTO.naam, Literal("tab"))

                elif "AANVRAAG-EN-VERGUNNING" in filepath or "Aanvraag_vergunning" in filepath:
                    archiefstuk.add_property(LDTO.classificatie, URIRef(bouwvergunning))
                    archiefstuk.add_property(LDTO.classificatie, URIRef(aanvraag_vergunning))
            

                elif "TEKENINGEN" in filepath or "Tekeningen" in filepath:
                    archiefstuk.add_property(LDTO.classificatie, URIRef(tekening)) 
                # archiefstuk.add_property(LDTO.naam, Literal("tekeningen"))

                elif "OVERIGE-DOCUMENTEN" in filepath or "Overig" in filepath:
                    archiefstuk.add_property(LDTO.classificatie, URIRef(overig))
                    archiefstuk.add_property(LDTO.naam, Literal("overige documenten"))

            else:
                archiefstuk.add_property(LDTO.naam, Literal("[geen naam vastgelegd]"))
                archiefstuk.add_property(LDTO.classificatie, URIRef(tekening))
                archiefstuk.add_property(LDTO.classificatie, URIRef(bouwvergunning))
                archiefstuk.add_property(LDTO.classificatie, URIRef(aanvraag_vergunning))
                archiefstuk.add_property(LDTO.classificatie, URIRef(overig))

            archiefstuk.save()
            graph += archiefstuk.graph

        # BESTAND: always created, linked to current archiefstuk
        identifier, is_new, stepped_dir = id_generator.generate(
            producer=gemeente_code,
            dataset=toegang_code,
            type="Bestand",
            inventarisnummer=invnummer,
            filepath=filepath
        )

        subject = URIRef(f"{RAZU}{identifier}")
        bestand = StructuredMetaResource(id=identifier, uri=subject)

        # get bestandsformaat
        if pd.notna(row['id']) and row['id'] != 'UNKNOWN':
            bestandsformaat_concept = format_builder.get_concept_obj_from_term(row['id'])
            file_extension = bestandsformaat_concept.get_value(SKOS.notation)
            bestand.add_property(LDTO.bestandsformaat, URIRef(bestandsformaat_concept.uri))
        else:
            file_extension = filepath.split(".")[-1].lower()

        # make storage url for metadata and file
        storage_url = make_storage_url(gemeente_code, toegang_code, stepped_dir)
        file_storage_url = URIRef(f"{storage_url}{identifier}.{file_extension}")
        metadata_storage_url = URIRef(f"{storage_url}{identifier}.{cfg.metadata_suffix}.{cfg.metadata_extension}")

        bestand.add_properties({
            RDF.type: LDTO.Bestand,
            DCT.hasFormat: metadata_storage_url,
            LDTO.isRepresentatieVan: archiefstuk.uri,
            LDTO.naam: Literal(f"{identifier}.{file_extension}"),
            LDTO.URLBestand: file_storage_url
        })
        
        # TECHNICAL TRIPLES 
        if pd.notna(row['ImageHeight']):
            bestand.add_property(SCHEMA.height, Literal(int(float(row['ImageHeight'])), datatype=XSD.integer))
        if pd.notna(row['ImageWidth']):
            bestand.add_property(SCHEMA.width, Literal(int(float(row['ImageWidth'])), datatype=XSD.integer))    
        if pd.notna(row['filesize']):
            bestand.add_property(LDTO.omvang, Literal(int(float(row['filesize'])), datatype=XSD.integer))
        if pd.notna(row['md5']):
            bestand.add_properties({ LDTO.checksum: {
                RDF.type: LDTO.ChecksumGegevens,
                LDTO.checksumAlgoritme: URIRef("https://data.razu.nl/id/algoritme/7f138a09169b250e9dcb378140907378"),
                LDTO.checksumWaarde: Literal(row['md5']),
                LDTO.checksumDatum: Literal(datetime.now().isoformat(), datatype=XSD.dateTime)
            }})

        # original name part
        bestand.add_triple(file_storage_url, RDF.type, PREMIS.File)
        bestand.add_triple(file_storage_url, PREMIS.originalName, Literal(f"./{filepath}"))
        bestand.add_triple(metadata_storage_url, RDF.type, PREMIS.File)

        bestand.save()
        graph += bestand.graph

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
    cursor = bag_db.conn.execute('''select OpenbareRuimte.bagID, OpenbareRuimte.naam from OpenbareRuimte join WPL on OpenbareRuimte.ligtIn == WPL.identificatie where OpenbareRuimte.naam = ? and WPL.naam = ?''', (adrs_data['STRAATNAAM'], bag_plaatsnaam(adrs_data['PLAATSNAAM'])))
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
            GEO.crs: URIRef("http://www.opengis.net/def/crs/OGC/1.3/CRS84")
        }
    return None

def get_actors_from_db(row: pd.Series) -> list | None: # returns a list of dictionaries
    cursor = metadata_db.conn.execute('''select piv.ROL, piv.VOORLETTERS, piv.TUSSENVOEGSEL, piv.ACHTERNAAM, rpiv.ROL as ROL_RPIV, rpiv.ORGANISATIENAAM from bd left join toegangen on bd.TOEGANG_ID == toegangen.ID left join piv on bd.ID == piv.BD_ID left join rpiv on bd.ID == rpiv.BD_ID where toegangen.CODE == ? and bd.ID == ?;''', (row['CODE'], row['BD_ID']))
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

def make_personname_uri(actor_dict):
    """Generate a unique URI for each actor instance using a UUID."""
    uid = uuid.uuid4().hex
    if actor_dict["type"] == PNV.PersonName:
        return URIRef(f"{PN}{uid}")

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
        geo_dict[GEO.crs] = URIRef("http://www.opengis.net/def/crs/OGC/1.3/CRS84")
        geo_dict[RDF.type] = GEO.Geometry
        geo_dict[RDFS.label] = Literal("Geen geometrie beschikbaar")


    # woonplaats (it's already in our thesaurus, hence get it from there)
    plaatsnaam = row['PLAATSNAAM']
    if plaatsnaam not in woonplaats_cache:
        woonplaats_cache[plaatsnaam] = locatie_builder.get_concept_obj_from_term(plaatsnaam) # Concept object
            
    woonplaats = woonplaats_cache[plaatsnaam] 
    
    if woonplaats:
        nummeraanduiding_dict[BAG.ligtIn] = woonplaats.uri
          
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
            pname_uri = make_personname_uri(actor_dict)

            if actor_dict["type"] == PNV.PersonName: 
                pname = StructuredMetaResource(uri=pname_uri)
                subject.add_properties({
                    LDTO.betrokkene: {
                        RDF.type: LDTO.BetrokkeneGegevens,
                        LDTO.betrokkeneTypeRelatie: URIRef(betrokkenheid_builder.get_concept_obj_from_term(actor_dict["rol"]).uri),
                        LDTO.betrokkeneActor: { 
                            RDF.type: [PICO.PersonObservation, LDTO.Actor],
                            PROV.hadPrimarySource: subject.uri,
                            PNV.hasName: pname_uri
                        }}                   
                })  

                # make separate graph
                pname.add_properties(actor_dict["data"])
                pname.add_property(SCHEMA.isPartOf, URIRef("https://data.razu.nl/id/persoonsnaam/2bcd801b0ba9d094d79f0e11d4d30baf"))

                private_graph += pname.graph


            elif actor_dict["type"] == SCHEMA.Organisation:
                subject.add_properties({
                    LDTO.betrokkene: {
                        RDF.type: LDTO.BetrokkeneGegevens,
                        LDTO.betrokkeneTypeRelatie: URIRef(betrokkenheid_builder.get_concept_obj_from_term(actor_dict["rol"]).uri),
                        LDTO.betrokkeneActor: actor_dict["data"]
                    }
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
    graph, private_graph = create_rdf(toegang_code, gemeente_code, archiefvormer)

    print(graph.serialize(format='turtle', destination=f"{cfg.default_sip_directory}/{toegang_code}.ttl"))
    print(private_graph.serialize(format='turtle', destination=f"{cfg.default_sip_directory}/{toegang_code}_private.ttl"))

if __name__ == "__main__":
    main("g0352", "008")


