import os
import pandas as pd
from rdflib import Graph, Literal, RDF, RDFS, URIRef
from rdflib.namespace import XSD

from razu.mdto_object import MDTOObject, MDTO, SCHEMA, GEO
from razu.razuconfig import RazuConfig
from razu.conceptresolver import ConceptResolver

import razu.util            # generieke functies
import extra                # code specifiek voor deze import

if __name__ == "__main__":

    cfg = RazuConfig(archive_creator_id="G321", archive_id="661", save_dir="output", save=False)

    # CSV-bestanden inlezen, we combineren hier een metadata-csv met de output van DROID
    # voor oa. checksum en omvang bestand; TODO beter als dit al aangeleverd is in de metadata
    # en we het in deze stap controleren.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    meta_df = pd.read_csv(os.path.join(script_dir, './metadata/metadata.csv'), delimiter=';')
    droid_df = pd.read_csv(os.path.join(script_dir, './metadata/droid.csv'), index_col='NAME')
    droid_df['SIZE'] = droid_df['SIZE'].fillna(0).astype(int)  # forceer deze kolom 'SIZE' als integers

    graph = Graph()
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)
    graph.bind("mdto", MDTO)
    graph.bind("schema", SCHEMA)
    graph.bind("geo", GEO)

    # voor boekhouding rondom serie en datumrange, bij doorlopen csv:
    current_serie = None
    serie = None
    earliest_date = None
    latest_date = None

    # resolvers, voor vervangen van conceptlabels door URIs:
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

    # behandel nu iedere regel van de metadata csv:
    for index, row in meta_df.iterrows():

        ## ARCHIEF
        #  We maken 1x , bij de eerste rij, een object voor de 'toegang' / het archief aan:
        if index == 0:
            archive = MDTOObject()
            archive.add_properties({
                RDFS.label: "Luchtfoto's Gemeente Houten",
                MDTO.naam: "Luchtfoto's Gemeente Houten",
                MDTO.omschrijving: "Gedigitaliseerde luchtfoto's Gemeente Houten",
                MDTO.archiefvormer: URIRef(actoren.get_uri("Gemeente Houten")),
                MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_uri("Archief")), 
                MDTO.identificatie: {
                    RDF.type: MDTO.IdentificatieGegevens,    
                    MDTO.identificatieKenmerk: cfg.archive_id,
                    MDTO.identificatieBron: "Toegangen Regionaal Archief Zuid-Utrecht"
                },
                MDTO.waardering: URIRef(waarderingen.get_uri("Blijvend te bewaren"))
            })
            # wordt verderop dynamisch toegevoegd: mdto:dekkingInTijd en mdt:bevatOnderdeel

        ## SERIE
        if current_serie != row['Serie'] :
            # we zijn bij een nieuwe serie beland (aanname is csv geordend per serie!):
            current_serie = row['Serie']

            if serie is not None:
                # bewaar de vorige serie in de graph
                serie.save()
                graph += serie

            serie = MDTOObject()
            serie.add_properties({
                RDFS.label: f"Luchtfoto's Houten serie {row['Serie']}",
                MDTO.naam: f"Luchtfoto's Houten serie {row['Serie']}",
                MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_uri("Serie")),
                MDTO.archiefvormer: URIRef(actoren.get_uri("Gemeente Houten")),
                MDTO.identificatie: {
                    RDF.type: MDTO.IdentificatieGegevens,
                    MDTO.identificatieBron: "Gemeente Houten",
                    MDTO.identificatieKenmerk: str(row['Serie']) 
                }
            })

            # maak relaties met bovenliggende archief:
            archive.add(MDTO.bevatOnderdeel, serie.uri)
            serie.add(MDTO.isOnderdeelVan, archive.uri)

        ## RECORD / archiefstuk
        record = MDTOObject()

        record.add_properties({
            RDFS.label: f"{row['Titel']}",
            MDTO.naam: f"{row['Titel']}",
            MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_uri("Archiefstuk")), 
            MDTO.archiefvormer: URIRef(actoren.get_uri("Gemeente Houten")) ,
            MDTO.omschrijving: row['Beschrijving voorkant'],
            MDTO.classificatie: [
                URIRef(soorten.get_uri(row['Soort'])), 
                URIRef(soorten.get_uri(row['Kleurtype']))
            ],
            MDTO.dekkingInRuimte: URIRef(locaties.get_uri(row['Plaats 1'])),
            MDTO.identificatie: [
                {
                    RDF.type: MDTO.IdentificatieGegevens,
                    MDTO.identificatieBron: f"RAZU Toegang {cfg.archive_id}",
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
                MDTO.betrokkeneTypeRelatie: URIRef(betrokkenheden.get_uri(row['Betrokkene type'])),
                MDTO.betrokkeneActor: URIRef(actoren.get_uri(row['Fotograaf naam']))
            },
            MDTO.raadpleeglocatie: {
                RDF.type: MDTO.RaadpleeglocatieGegevens,
                MDTO.raadpleeglocatieFysiek: {
                    RDF.type: MDTO.VerwijzingGegevens ,
                    MDTO.verwijzingNaam: f"Regionaal Archief Zuid Utrecht {row['Plaats']}" 
                }
            } ,
            MDTO.dekkingInTijd: { 
                RDF.type: MDTO.DekkingInTijdGegevens,
                MDTO.dekkingInTijdBeginDatum: razu.util.date_type(row['Datering']) ,
                MDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_uri("Opnamedatum"))
            },
            MDTO.beperkingGebruik: [
                { 
                    RDF.type: MDTO.BeperkingGebruikGegevens, 
                    MDTO.beperkingGebruikType: URIRef(licenties.get_uri(row['Auteursrecht']))
                },
                { 
                    RDF.type: MDTO.BeperkingGebruikGegevens,     
                    MDTO.beperkingGebruikType: URIRef(openbaarheden.get_uri('Openbaar'))
                }
            ],
            GEO.scale: row['Schaal'],
            GEO.hasBoundingBox: {
                RDF.type: GEO.Geometry,
                GEO.asWKT: Literal(extra.create_polygon(row['Coördinaat - Linksonder'], row['Coördinaat Rechtsboven']), datatype=GEO.wktLiteral),
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
            record.add(MDTO.dekkingInRuimte, URIRef(locaties.get_uri(row['Plaats 2'])))

        if not pd.isna(row['Plaats 3']):
            record.add(MDTO.dekkingInRuimte, URIRef(locaties.get_uri(row['Plaats 3'])))

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

        ## BESTAND
        original_filename = extra.maak_bestandsnaam(row['Doos-nummer'], row['Inventarisnummer'])
        droid_row = droid_df.loc[f"{original_filename}.jpg"]  # TODO: die jpg wordt er bij verzonnen, zou eigenlijk via waardenlijst moeten

        bestand = MDTOObject(type = MDTO.Bestand)
        bestand.add_properties({
            MDTO.naam: f"{row['Titel']} {row['Doos-nummer']}:{row['Volgnummer']}",
            MDTO.identificatie: {
                RDF.type: MDTO.IdentificatieGegevens,
                MDTO.identificatieBron: "Gemeente Houten",
                MDTO.identificatieKenmerk: f"{original_filename}.jpg" 
            },
            MDTO.checksum: { 
                RDF.type: MDTO.ChecksumGegevens,
                MDTO.checksumAlgoritme: URIRef(algoritmes.get_uri("MD5")),
                MDTO.checksumDatum: Literal("2024-08-02T00:00:00", datatype=XSD.dateTime),   #TODO: waar halen we deze vandaan?
                MDTO.checksumWaarde: f"{droid_row['MD5_HASH']}"  
            },
            MDTO.bestandsformaat: URIRef(bestandsformaten.get_uri(droid_row['PUID'])),
            MDTO.omvang: Literal(int(droid_row['SIZE']), datatype=XSD.integer),
            # MDTO.omvang: Literal(droid_row['SIZE']),
            MDTO.URLBestand: Literal(f"https://htn.opslag.razu.nl/{bestand.mdto_identificatiekenmerk()}.jpg", datatype=XSD.anyURI)  # TODO: weer die .jpg !
          })

        # relaties bestand en archiefstuk:
        record.add(MDTO.heeftRepresentatie, bestand.uri)
        bestand.add(MDTO.isRepresentatieVan, record.uri)

        # bewaar & voeg archiefstuk & bestand toe aan graph
        record.save()
        graph += record
        bestand.save()
        graph += bestand

        # hiermee bepalen we de datumrange op archive-niveau:
        # NB code gaat mogelijk mis als datum niet in iso-formaat
        if earliest_date is None or row['Datering'] < earliest_date:
            earliest_date = row['Datering'] 
        if latest_date is None or row['Datering'] > latest_date:
            latest_date = row['Datering'] 

    # nu alle rijen doorlopen zijn, weten we de dekking in tijd vh archief:
    archive.add_properties( {
        MDTO.dekkingInTijd: {
            RDF.type: MDTO.DekkingInTijdGegevens ,
            MDTO.dekkingInTijdBeginDatum: razu.util.date_type(earliest_date) ,
            MDTO.dekkingInTijdEindDatum: razu.util.date_type(latest_date) ,
            MDTO.dekkingInTijdType: URIRef(dekkingintijdtypen.get_uri("Opnamedatum"))
        }
    })

    archive.save()

    # dit is alleen relevant als we output willen zien van de gemaakte rdf:
    graph += archive
    graph += serie
    print(graph.serialize(format='turtle'))
