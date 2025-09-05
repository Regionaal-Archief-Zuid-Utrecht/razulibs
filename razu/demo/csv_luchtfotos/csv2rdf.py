import os
import pandas as pd
from rdflib import Literal, URIRef

from razu.config import Config
from razu.meta_resource import StructuredMetaResource
from razu.concept_resolver import ConceptResolver
from razu.meta_graph import MetaGraph, RDF, RDFS, LDTO, SCHEMA, GEO, PREMIS, XSD, SKOS

import razu.util
import extra                # Functions specific for this import

"""	
This demo aims to provide a simple example of how  metadata from a CSV file can be transformed to RDF.
The RDF conforms to the MDTO derived model as used by RAZU.
The RDF is displayed on screen and saved to the default output directory (known as "context.default_sip_directory").

Make sure the settings file config.yaml is available, for example in the present working directory.
"""	



def main():
    
    # Initialize RDF concept resolvers, used to convert labels, notations or identifiers
    # in a given vocabulary to their respective URIs.
    actoren = ConceptResolver("actor")
    aggregatieniveaus = ConceptResolver("aggregatieniveau")
    algoritmes = ConceptResolver("algoritme")
    bestandsformaten = ConceptResolver("bestandsformaat")
    betrokkenheden = ConceptResolver("betrokkenheid")
    dekkingintijdtypen = ConceptResolver("dekkingintijdtype")
    beperkinggebruiktypen = ConceptResolver("beperkinggebruiktype")
    locaties = ConceptResolver("locatie")
    soorten = ConceptResolver("soort")
    waarderingen = ConceptResolver("waardering")

    # Initialize global configuration
    context = Config.initialize()

    # Initialize the context with settings for this specific run
    context.add_properties(
        archive_id="661",
        archive_creator_id=actoren.get_concept_value("Gemeente Houten", SKOS.notation),
        sip_directory=context.default_sip_directory
    )
    os.makedirs(context.sip_directory, exist_ok=True)

    # Read the CSV files with metadata and DROID outputs
    script_directory = os.path.dirname(os.path.abspath(__file__))
    meta_path = os.path.join(script_directory, f"./{context.default_metadata_directory}/metadata.csv")
    droid_path = os.path.join(script_directory, f"./{context.default_metadata_directory}/droid.csv")

    meta_df = pd.read_csv(meta_path, delimiter=';')
    droid_df = pd.read_csv(droid_path, index_col='NAME')
    droid_df['SIZE'] = droid_df['SIZE'].fillna(0).astype(int)  # Force this column to be handled as integers
    checksum_date = razu.util.get_last_modified(droid_path)

    graph = MetaGraph()

    # For bookkeeping around series and date range, while going through the csv:
    current_serie = None
    serie = None
    earliest_date = None
    latest_date = None

    # Now process each row of the metadata spreadsheet:
    for index, row in meta_df.iterrows():

        # ARCHIEF
        # The highest level is implictly defined in the metadata, create it when processing the first row:
        if index == 0:
            archive = StructuredMetaResource()
            archive.add_properties({
                RDFS.label: "Luchtfoto's Gemeente Houten",
                LDTO.naam: "Luchtfoto's Gemeente Houten",
                LDTO.omschrijving: "Gedigitaliseerde luchtfoto's Gemeente Houten",
                LDTO.archiefvormer: URIRef(actoren.get_concept("Gemeente Houten").get_uri()),
                LDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept_uri("Archief")),
                LDTO.identificatie: {
                    RDF.type: LDTO.IdentificatieGegevens,    
                    LDTO.identificatieKenmerk: context.archive_id,
                    LDTO.identificatieBron: "Toegangen Regionaal Archief Zuid-Utrecht"
                },
                LDTO.waardering: URIRef(waarderingen.get_concept_uri("Blijvend te bewaren"))
            })
            # Predicates to be added later in the script: ldto:dekkingInTijd en ldto:bevatOnderdeel

        # SERIE
        if current_serie != row['Serie']:
            # Assuming csv is ordered by series, this must be a new series
            current_serie = row['Serie']

            if serie is not None:
                # Store the previous serie, we dealt with that already
                serie.save()
                graph += serie

            serie = StructuredMetaResource()
            serie.add_properties({
                RDFS.label: f"Luchtfoto's Houten serie {row['Serie']}",
                LDTO.naam: f"Luchtfoto's Houten serie {row['Serie']}",
                LDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept_uri("Serie")),
                LDTO.archiefvormer: URIRef(actoren.get_concept_uri("Gemeente Houten")),
                LDTO.identificatie: {
                    RDF.type: LDTO.IdentificatieGegevens,
                    LDTO.identificatieBron: "Gemeente Houten",
                    LDTO.identificatieKenmerk: str(row['Serie']) 
                }
            })

            # Add relations with the upper 'Archief' level
            archive.add(LDTO.bevatOnderdeel, serie.uri)
            serie.add(LDTO.isOnderdeelVan, archive.uri)

        # RECORD / archiefstuk
        record = StructuredMetaResource()
        record.add_properties({
            RDFS.label: f"{row['Titel']}",
            LDTO.naam: f"{row['Titel']}",
            LDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept_uri("Archiefstuk")),
            LDTO.archiefvormer: URIRef(actoren.get_concept_uri("Gemeente Houten")),
            LDTO.omschrijving: row['Beschrijving voorkant'],
            LDTO.classificatie: [
                URIRef(soorten.get_concept_uri(row['Soort'])),
                URIRef(soorten.get_concept_uri(row['Kleurtype']))
            ],
            LDTO.dekkingInRuimte: URIRef(locaties.get_concept_uri(row['Plaats 1'])),
            LDTO.identificatie: [
                {
                    RDF.type: LDTO.IdentificatieGegevens,
                    LDTO.identificatieBron: f"Inventarissen Toegang {context.archive_id} RAZU",
                    LDTO.identificatieKenmerk: str(row['Inventarisnummer']) 
                },
                {
                    RDF.type: LDTO.IdentificatieGegevens,
                    LDTO.identificatieBron: "Gemeente Houten",
                    LDTO.identificatieKenmerk: f"doos: {row['Doos-nummer']} volgnummer: {row['Volgnummer']}" 
                },
            ],
            LDTO.betrokkene: {
                RDF.type: LDTO.BetrokkeneGegevens,
                LDTO.betrokkeneTypeRelatie: URIRef(betrokkenheden.get_concept_uri(row['Betrokkene type'])),
                LDTO.betrokkeneActor: URIRef(actoren.get_concept_uri(row['Fotograaf naam']))
            },
            LDTO.raadpleeglocatie: {
                RDF.type: LDTO.RaadpleeglocatieGegevens,
                LDTO.raadpleeglocatieFysiek: {
                    RDF.type: LDTO.VerwijzingGegevens,
                    LDTO.verwijzingNaam: f"Regionaal Archief Zuid Utrecht {row['Plaats']}" 
                }
            },
            LDTO.dekkingInTijd: { 
                RDF.type: LDTO.DekkingInTijdGegevens,
                LDTO.dekkingInTijdBeginDatum: razu.util.date_type(row['Datering']),
                LDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_concept_uri("Opname"))
            },
            LDTO.beperkingGebruik: [
                { 
                    RDF.type: LDTO.BeperkingGebruikGegevens, 
                    LDTO.beperkingGebruikType: URIRef(beperkinggebruiktypen.get_concept_uri(row['Auteursrecht']))
                },
                { 
                    RDF.type: LDTO.BeperkingGebruikGegevens,     
                    LDTO.beperkingGebruikType: URIRef(beperkinggebruiktypen.get_concept_uri('Openbaar'))
                }
            ],
            GEO.scale: row['Schaal'],
            GEO.hasBoundingBox: {
                RDF.type: GEO.Geometry,
                GEO.asWKT: Literal(extra.create_polygon(row['Coördinaat - Linksonder'], row['Coördinaat Rechtsboven']),
                                   datatype=GEO.wktLiteral),
                GEO.crs: URIRef("http://www.opengis.net/def/crs/OGC/1.3/CRS84")  
            },
            SCHEMA.width: {
                RDF.type: SCHEMA.QuantitativeValue,
                SCHEMA.unitCode: "CMT",
                SCHEMA.value: row['Breedte (cm)']
            },
            SCHEMA.height: {
                RDF.type: SCHEMA.QuantitativeValue,
                SCHEMA.unitCode: "CMT",
                SCHEMA.value: row['Hoogte (cm)']
            } 
        })

        # Optional fields
        if not pd.isna(row['Plaats 2']):
            record.add(LDTO.dekkingInRuimte, URIRef(locaties.get_concept_uri(row['Plaats 2'])))

        if not pd.isna(row['Plaats 3']):
            record.add(LDTO.dekkingInRuimte, URIRef(locaties.get_concept_uri(row['Plaats 3'])))

        if not pd.isna(row['Bijzonderheden']):
            record.add_properties({
                SCHEMA.review:  {
                    RDF.type: SCHEMA.Review,
                    SCHEMA.reviewBody: row['Bijzonderheden']
                }
            })

        # Create links:
        serie.add(LDTO.bevatOnderdeel, record.uri)
        record.add(LDTO.isOnderdeelVan, serie.uri)

        # BESTAND
        original_filename = extra.maak_bestandsnaam(row['Doos-nummer'], row['Inventarisnummer'])
        droid_row = droid_df.loc[original_filename] 

        bestand = StructuredMetaResource(rdf_type=LDTO.Bestand)
        bestand.add_properties({
            LDTO.naam: f"{row['Titel']} {row['Doos-nummer']}:{row['Volgnummer']}",
            PREMIS.originalName: original_filename,
            LDTO.checksum: { 
                RDF.type: LDTO.ChecksumGegevens,
                LDTO.checksumAlgoritme: URIRef(algoritmes.get_concept_uri("MD5")),
                LDTO.checksumDatum: Literal(checksum_date, datatype=XSD.dateTime),
                LDTO.checksumWaarde: f"{droid_row['MD5_HASH']}"  
            },
            LDTO.bestandsformaat: URIRef(bestandsformaten.get_concept_uri(droid_row['PUID'])),
            LDTO.omvang: Literal(int(droid_row['SIZE']), datatype=XSD.integer),
            LDTO.URLBestand: Literal(
                f"https://{context.archive_creator_id.lower()}.{context.storage_base_domain}/{bestand._id_factory.make_s3_path_from_id(bestand.id)}{bestand.uid}"
                f".{bestandsformaten.get_concept_value(droid_row['PUID'], SKOS.notation)}",
                datatype=XSD.anyURI
            )
        })

        # Create links:
        record.add(LDTO.heeftRepresentatie, bestand.uri)
        bestand.add(LDTO.isRepresentatieVan, record.uri)

        # Store and add to graph
        record.save()
        graph += record
        bestand.save()
        graph += bestand

        # Here we determine the date range at archive level:
        # note that this code might go wrong if date not in iso-format
        if earliest_date is None or row['Datering'] < earliest_date:
            earliest_date = row['Datering'] 
        if latest_date is None or row['Datering'] > latest_date:
            latest_date = row['Datering'] 

    # Now we have looped through all rows, we know the archive's coverage in time:
    archive.add_properties({
        LDTO.dekkingInTijd: {
            RDF.type: LDTO.DekkingInTijdGegevens,
            LDTO.dekkingInTijdBeginDatum: razu.util.date_type(earliest_date),
            LDTO.dekkingInTijdEindDatum: razu.util.date_type(latest_date),
            LDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_concept_uri("Opname"))
        }
    })

    archive.save()

    # This is only relevant if we want to see the output of the generated rdf:
    graph += archive
    graph += serie
    print(graph.serialize(format='turtle'))

if __name__ == "__main__":
    main()
