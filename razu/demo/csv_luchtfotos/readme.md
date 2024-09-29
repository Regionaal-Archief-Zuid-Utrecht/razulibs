# Leesmij demo csv2rdf.py

Script [csv2rdf.py]() biedt een fictief voorbeeld waarbij met de hier geboden libraries RDF gemaakt wordt voor een set met luchtfoto's.


## Bronnen
De bron voor de metadata vormt het csv-bestand [./metadata/metadata.csv](). Dit wordt ingelezen in een *pandas dataframe*, waarna het per regel verwerkt wordt.

Aanvullend wordt er gebruik gemaakt van de output van DROID, eveneens in csv-formaat([./metadata/droid.csv]()). Dit wordt gebruikt als bron voor de checksum, de omvang vam het bestand in bytes en uiteraard het PRONOM PUID. De bestandsnaam ('NAME') wordt daarbij als index gebruikt.

## De output
Alle gegenereerde RDF wordt aan het einde van het script als Turtle getoond. Het script biedt de mogelijkheid om per gegenereerde entiteit de RDF als json-ld weg te schrijven. Dit kan geactiveerd worden door in de instantie van [`RAZUConfig`](../../razuconfig.py) de parameter `save` de waarde `True` te geven. De bestanden verschijnen dan in `save_dir`.

## De datastructuur
Dit script produceert data die gebaseerd in op [MDTO](https://www.nationaalarchief.nl/archiveren/mdto) van het Nationaal Achief, maar die daar niet één-op-één aan conformeert.

De datastructuur biedt per luchtfoto een `MDTO.Bestand` en een `MDTO.Informatieobject`. De informatieobjecten worden geordend per 'serie', die onder een 'archief' vallen.

## Conceptresolvers
Om te voorkomen dat er brondata expliciet URIs opgenomen moeten worden, en ook om dit script zo leesbaar mogelijk te maken, wordt er veel gebruik gemaakt van [`ConceptResolver`s](../../concept_resolver.py) die de benodigde URI kunnen achterhalen door de term in een gegeven waardenlijst op te zoeken.
