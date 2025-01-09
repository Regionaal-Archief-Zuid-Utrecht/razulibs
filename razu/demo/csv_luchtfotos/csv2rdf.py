import os
import pandas as pd
from rdflib import Literal, URIRef

from razu.config import Config
from razu.meta_resource import StructuredMetaResource
from razu.concept_resolver import ConceptResolver
from razu.meta_graph import MetaGraph, RDF, RDFS, MDTO, SCHEMA, GEO, PREMIS, XSD, SKOS

import razu.util
import extra                # Functions specific for this import

"""	
This demo aims to provide a simple example of how  metadata from a CSV file can be transformed to RDF.

The RDF conforms to the MDTO derived model as used by RAZU.
The RDF is displayed on screen and saved to the default output directory (known as "context.default_sip_directory").

Make sure the settings file config.yaml is available, in for example the present working directory.
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
    licenties = ConceptResolver("licentie")
    locaties = ConceptResolver("locatie")
    openbaarheden = ConceptResolver("openbaarheid")
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
                MDTO.naam: "Luchtfoto's Gemeente Houten",
                MDTO.omschrijving: "Gedigitaliseerde luchtfoto's Gemeente Houten",
                MDTO.archiefvormer: URIRef(actoren.get_concept("Gemeente Houten").get_uri()),
                MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept_uri("Archief")),
                MDTO.identificatie: {
                    RDF.type: MDTO.IdentificatieGegevens,    
                    MDTO.identificatieKenmerk: context.archive_id,
                    MDTO.identificatieBron: "Toegangen Regionaal Archief Zuid-Utrecht"
                },
                MDTO.waardering: URIRef(waarderingen.get_concept_uri("Blijvend te bewaren"))
            })
            # Predicates to be added later in the script: mdto:dekkingInTijd en mdt:bevatOnderdeel

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
                MDTO.naam: f"Luchtfoto's Houten serie {row['Serie']}",
                MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept_uri("Serie")),
                MDTO.archiefvormer: URIRef(actoren.get_concept_uri("Gemeente Houten")),
                MDTO.identificatie: {
                    RDF.type: MDTO.IdentificatieGegevens,
                    MDTO.identificatieBron: "Gemeente Houten",
                    MDTO.identificatieKenmerk: str(row['Serie']) 
                }
            })

            # Add relations with the upper 'Archief' level
            archive.add(MDTO.bevatOnderdeel, serie.uri)
            serie.add(MDTO.isOnderdeelVan, archive.uri)

        # RECORD / archiefstuk
        record = StructuredMetaResource()
        record.add_properties({
            RDFS.label: f"{row['Titel']}",
            MDTO.naam: f"{row['Titel']}",
            MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept_uri("Archiefstuk")),
            MDTO.archiefvormer: URIRef(actoren.get_concept_uri("Gemeente Houten")),
            MDTO.omschrijving: row['Beschrijving voorkant'],
            MDTO.classificatie: [
                URIRef(soorten.get_concept_uri(row['Soort'])),
                URIRef(soorten.get_concept_uri(row['Kleurtype']))
            ],
            MDTO.dekkingInRuimte: URIRef(locaties.get_concept_uri(row['Plaats 1'])),
            MDTO.identificatie: [
                {
                    RDF.type: MDTO.IdentificatieGegevens,
                    MDTO.identificatieBron: f"Inventarissen Toegang {context.archive_id} RAZU",
                    MDTO.identificatieKenmerk: str(row['Inventarisnummer']) 
                },
                {
                    RDF.type: MDTO.IdentificatieGegevens,
                    MDTO.identificatieBron: "Gemeente Houten",
                    MDTO.identificatieKenmerk: f"doos: {row['Doos-nummer']} volgnummer: {row['Volgnummer']}" 
                },
            ],
            MDTO.betrokkene: {
                RDF.type: MDTO.BetrokkeneGegevens,
                MDTO.betrokkeneTypeRelatie: URIRef(betrokkenheden.get_concept_uri(row['Betrokkene type'])),
                MDTO.betrokkeneActor: URIRef(actoren.get_concept_uri(row['Fotograaf naam']))
            },
            MDTO.raadpleeglocatie: {
                RDF.type: MDTO.RaadpleeglocatieGegevens,
                MDTO.raadpleeglocatieFysiek: {
                    RDF.type: MDTO.VerwijzingGegevens,
                    MDTO.verwijzingNaam: f"Regionaal Archief Zuid Utrecht {row['Plaats']}" 
                }
            },
            MDTO.dekkingInTijd: { 
                RDF.type: MDTO.DekkingInTijdGegevens,
                MDTO.dekkingInTijdBeginDatum: razu.util.date_type(row['Datering']),
                MDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_concept_uri("Opname"))
            },
            MDTO.beperkingGebruik: [
                { 
                    RDF.type: MDTO.BeperkingGebruikGegevens, 
                    MDTO.beperkingGebruikType: URIRef(licenties.get_concept_uri(row['Auteursrecht']))
                },
                { 
                    RDF.type: MDTO.BeperkingGebruikGegevens,     
                    MDTO.beperkingGebruikType: URIRef(openbaarheden.get_concept_uri('Openbaar'))
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
            record.add(MDTO.dekkingInRuimte, URIRef(locaties.get_concept_uri(row['Plaats 2'])))

        if not pd.isna(row['Plaats 3']):
            record.add(MDTO.dekkingInRuimte, URIRef(locaties.get_concept_uri(row['Plaats 3'])))

        if not pd.isna(row['Bijzonderheden']):
            record.add_properties({
                SCHEMA.review:  {
                    RDF.type: SCHEMA.Review,
                    SCHEMA.reviewBody: row['Bijzonderheden']
                }
            })

        # Create links:
        serie.add(MDTO.bevatOnderdeel, record.uri)
        record.add(MDTO.isOnderdeelVan, serie.uri)

        # BESTAND
        original_filename = extra.maak_bestandsnaam(row['Doos-nummer'], row['Inventarisnummer'])
        droid_row = droid_df.loc[original_filename] 

        bestand = StructuredMetaResource(rdf_type=MDTO.Bestand)
        bestand.add_properties({
            MDTO.naam: f"{row['Titel']} {row['Doos-nummer']}:{row['Volgnummer']}",
            PREMIS.originalName: original_filename,
            MDTO.checksum: { 
                RDF.type: MDTO.ChecksumGegevens,
                MDTO.checksumAlgoritme: URIRef(algoritmes.get_concept_uri("MD5")),
                MDTO.checksumDatum: Literal(checksum_date, datatype=XSD.dateTime),
                MDTO.checksumWaarde: f"{droid_row['MD5_HASH']}"  
            },
            MDTO.bestandsformaat: URIRef(bestandsformaten.get_concept_uri(droid_row['PUID'])),
            MDTO.omvang: Literal(int(droid_row['SIZE']), datatype=XSD.integer),
            MDTO.URLBestand: Literal(
                f"https://{context.archive_creator_id.lower()}.{context.storage_base_domain}/{bestand.uid}"
                f".{bestandsformaten.get_concept_value(droid_row['PUID'], SKOS.notation)}",
                datatype=XSD.anyURI
            )
        })

        # Create links:
        record.add(MDTO.heeftRepresentatie, bestand.uri)
        bestand.add(MDTO.isRepresentatieVan, record.uri)

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
        MDTO.dekkingInTijd: {
            RDF.type: MDTO.DekkingInTijdGegevens,
            MDTO.dekkingInTijdBeginDatum: razu.util.date_type(earliest_date),
            MDTO.dekkingInTijdEindDatum: razu.util.date_type(latest_date),
            MDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_concept_uri("Opname"))
        }
    })

    archive.save()

    # This is only relevant if we want to see the output of the generated rdf:
    graph += archive
    graph += serie
    print(graph.serialize(format='turtle'))

if __name__ == "__main__":
    main()
