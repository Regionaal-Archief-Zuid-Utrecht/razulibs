# RAZU libs voor RDF-gebaseerde SIP en ingest

*Python-bibliotheken ter ondersteuning van een op RDF gebaseerde SIP voor ingest in e-depot*

## Doel

1Deze code wordt ontwikkeld voor gebruik in de pre-ingest voor het [common ground](https://commonground.nl/) digitaal magazijn van het RAZU ([Regionaal Archief Zuid-Utrecht](https://www.razu.nl/)). Het doel is hiermee te komen tot een zo eenvoudig mogelijk te configureren (*scripten*) datatransformatie en -validatie, waarbij zo veel mogelijk standaard Python libraries gebruikt worden. De basis wordt gevormd door [RDFLib](https://rdflib.readthedocs.io/).

Het RAZU werkt hierbij met een op [MDTO](https://www.nationaalarchief.nl/archiveren/mdto) gebaseerd informatiemodel in RDF, maar de brondata kan in principe tot in iedere gewenste RDF-vorm getransformeerd worden.

## Creatie van RDF, een voorbeeld

Een voorbeeldimplementatie waarbij data uit twee csv-bestanden wordt omgezet naar RDF is te vinden in [demo/csv_luchtfotos/csv2rdf.py](./razu/demo/csv_luchtfotos/csv2rdf.py). Centraal voor deze conversie staat de `RDFResource`-class die het makkelijkt maakt om te werken met RDF *resources* en daar eigenschappen aan te toe te kennen. Met de afgeleid class `MetaResource` kan de RDF resource opgeslagen en weer ingelezen worden. Om het maken van RDF en het kunnen benaderen van specifieke eigenschappen van de resource verder te ondersteunen is er tot slot de class `StructuredMetaResource`.

Een voorbeeld van het gebruik van `RDFResource` met een  [pandas dataframe](https://pandas.pydata.org/) als bron:


    actoren = ConceptResolver('actor')
    aggregatieniveaus = ConceptResolver('aggregatieniveau')
    soorten = ConceptResolver('soort')
    
    record = RDFResource()

    record.add_properties({
        RDFS.label: f"{row['Titel']}",
        MDTO.naam: f"{row['Titel']}",
        MDTO.aggregatieniveau: URIRef(aggregatieniveaus.get_concept("Archiefstuk").get_uri()), 
        MDTO.archiefvormer: URIRef(actoren.get_concept("Gemeente Houten").get_uri()) ,
        MDTO.omschrijving: row['Beschrijving voorkant'],
        MDTO.classificatie: [
            URIRef(soorten.get_concept(row['Soort']).get_uri()), 
            URIRef(soorten.get_concept(row['Kleurtype']).get_uri())
        ],
        MDTO.identificatie: [ {
            RDF.type: MDTO.IdentificatieGegevens,
            MDTO.identificatieBron: f"RAZU Toegang {cfg.archive_id}",
            MDTO.identificatieKenmerk: str(row['Inventarisnummer']) 
        }, {
            RDF.type: MDTO.IdentificatieGegevens,
            MDTO.identificatieBron: "Gemeente Houten",
            MDTO.identificatieKenmerk: f"doos: {row['Doos-nummer']} volgnummer: {row['Volgnummer']}" 
        }]
    })

Deze code zal, met gegeven brondata, RDF opleveren die in Turtle als volgt geserialiseerd kan worden:

    @prefix mdto: <http://www.nationaalarchief.nl/mdto#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix premis: <http://www.loc.gov/premis/rdf/v3/> .
    
    <https://data.razu.nl/nl-wbdrazu-g0321-661-3> a mdto:Informatieobject, premis:Object;
        rdfs:label "Luchtfoto gemeente Houten" ;
        mdto:naam "Luchtfoto gemeente Houten" ;
        mdto:aggregatieniveau <https://data.razu.nl/id/aggregatieniveau/96f7399fb1c5d3b7d2acdc48dac3d71e> ;
        mdto:archiefvormer <https://data.razu.nl/id/actor/424280985651f416dfb6a68ee8ee6c6a> ;
        mdto:omschrijving "Een overzicht van het oude stadscentrum." ;
        mdto:classificatie 
            <https://data.razu.nl/id/soort/4494b13ba2a3d7354c3c02b970bc51b6>,
            <https://data.razu.nl/id/soort/d5cd29a63289870be48cf55cbc79ae36> ;
        mdto:identificatie [ 
            a mdto:IdentificatieGegevens ;
            mdto:identificatieBron "RAZU Toegang 661" ;
            mdto:identificatieKenmerk "1" 
        ], [ 
            a mdto:IdentificatieGegevens ;
            mdto:identificatieBron "Gemeente Houten" ;
            mdto:identificatieKenmerk "doos: 1984-1 volgnummer: 1" 
        ] .

De functionaliteit van het `MetaObject` maakt het eenvoudig om in de RDF links te specificeren. Via het MDTO-vocabulaire kopppelen van een record-instantie aan de instantie van een serie, en andersom, kan eenvoudig met:

    serie.add(MDTO.bevatOnderdeel, record.uri)
    record.add(MDTO.isOnderdeelVan, serie.uri)


## Werken met een SIP

Een SIP (*submission informatie package*, volgens *OAIS*) kan aangemaakt, opgebouwd en bewaard worden met de class `Sip`. Een Sip kan bestaan uit de reguliere bestanden van het archief (bijvoorbeeld een .pdf-bestand), metadata-beschrijvingen (in RDF, als json-ld), en één manifest-bestand (TODO: en een PREMIS-eventlog). Via het manifest wordt de integriteit van het SIP bewaakt. Hiervoor is er de class `Manifest`. 


## Pas op
Deze code is nog in ontwikkeling en daarmee nog niet gegarandeerd stabiel.
In toekomstige versies zal naar verwachting gewerkt worden aan oa. het kunnen verwerken van andersoortige bronnen (zoals XML), output-validatie en transformatie RDF volgens de officiële MDTO-standaard.
