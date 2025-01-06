import os, sys
import pandas as pd
from rdflib import Literal, URIRef

from razu.config import Config
from razu.incrementer import Incrementer
from razu.concept_resolver import ConceptResolver
from razu.meta_graph import RDF, RDFS, MDTO, SCHEMA, GEO, PREMIS, XSD, SKOS
from razu.sip import Sip   

import razu.util            # generieke functies
import extra                # code specifiek voor deze import

def main():
    # Create output directory
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Initialize global config
    context = Config.initialize()

    # Initialize concept resolvers
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

    # Initialize sip with archive details
    sip = Sip.create_new(
        archive_creator_id=actoren.get_concept_value("Gemeente Houten", SKOS.notation),
        archive_id="661",
    )

    # CSV-bestanden inlezen
    script_directory = os.path.dirname(os.path.abspath(__file__))
    meta_path = os.path.join(script_directory, './metadata/metadata.csv')
    droid_path = os.path.join(script_directory, './metadata/droid.csv')

    meta_df = pd.read_csv(meta_path, delimiter=';')
    droid_df = pd.read_csv(droid_path, index_col='NAME')
    droid_df['SIZE'] = droid_df['SIZE'].fillna(0).astype(int)  # forceer deze kolom 'SIZE' als integers
    checksum_date = razu.util.get_last_modified(droid_path)

    # voor boekhouding rondom serie en datumrange, bij doorlopen csv:
    current_serie = None
    serie = None
    earliest_date = None
    latest_date = None

    counter = Incrementer(0)

    # behandel nu iedere regel van de metadata csv:
    for index, row in meta_df.iterrows():

        # ARCHIEF
        #  We maken 1x , bij de eerste rij, een resource voor de 'toegang' / het archief aan:
        if index == 0:
            archive = sip.create_meta_resource(id=counter.next())
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
            # wordt verderop dynamisch toegevoegd: mdto:dekkingInTijd en mdt:bevatOnderdeel

        # SERIE
        if current_serie != row['Serie']:
            # we zijn bij een nieuwe serie beland (aanname is csv geordend per serie!):
            current_serie = row['Serie']

            serie = sip.create_meta_resource(id=counter.next())
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

            # maak relaties met bovenliggende archief:
            archive.add(MDTO.bevatOnderdeel, serie.uri)
            serie.add(MDTO.isOnderdeelVan, archive.uri)

        # RECORD / archiefstuk
        record = sip.create_meta_resource(id=counter.next())
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

        # optionele velden voor het archiefstuk:
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

        # relaties archiefstuk en serie:
        serie.add(MDTO.bevatOnderdeel, record.uri)
        record.add(MDTO.isOnderdeelVan, serie.uri)

        # BESTAND
        # original_filename = extra.maak_bestandsnaam(row['Doos-nummer'], row['Inventarisnummer'])
        # droid_row = droid_df.loc[original_filename] 

        # bestand = sip.create_meta_resource(id=counter.next(), rdf_type=MDTO.Bestand)
        # bestand.add_properties({
        #     MDTO.naam: f"{row['Titel']} {row['Doos-nummer']}:{row['Volgnummer']}",
        #     PREMIS.originalName: original_filename,
        #     MDTO.checksum: { 
        #         RDF.type: MDTO.ChecksumGegevens,
        #         MDTO.checksumAlgoritme: URIRef(algoritmes.get_concept_uri("MD5")),
        #         MDTO.checksumDatum: Literal(checksum_date, datatype=XSD.dateTime),
        #         MDTO.checksumWaarde: f"{droid_row['MD5_HASH']}"  
        #     },
        #     MDTO.bestandsformaat: URIRef(bestandsformaten.get_concept_uri(droid_row['PUID'])),
        #     MDTO.omvang: Literal(int(droid_row['SIZE']), datatype=XSD.integer),
        #     MDTO.URLBestand: Literal(
        #         f"https://{context.archive_creator_id.lower()}.{context.storage_base_domain}/{bestand.uid}"
        #         f".{bestandsformaten.get_concept_value(droid_row['PUID'], SKOS.notation)}",
        #         datatype=XSD.anyURI
        #     )
        # })

        # # relaties bestand en archiefstuk:
        # record.add(MDTO.heeftRepresentatie, bestand.uri)
        # bestand.add(MDTO.isRepresentatieVan, record.uri)

        # hiermee bepalen we de datumrange op archive-niveau:
        # NB code gaat mogelijk mis als datum niet in iso-formaat
        if earliest_date is None or row['Datering'] < earliest_date:
            earliest_date = row['Datering'] 
        if latest_date is None or row['Datering'] > latest_date:
            latest_date = row['Datering'] 

    # nu alle rijen doorlopen zijn, weten we de dekking in tijd vh archief:
    archive.add_properties({
        MDTO.dekkingInTijd: {
            RDF.type: MDTO.DekkingInTijdGegevens,
            MDTO.dekkingInTijdBeginDatum: razu.util.date_type(earliest_date),
            MDTO.dekkingInTijdEindDatum: razu.util.date_type(latest_date),
            MDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_concept_uri("Opname"))
        }
    })

    sip.meta_resources.export_rdf()
    sip.save()
    sip.manifest.validate()

if __name__ == "__main__":
    main()
