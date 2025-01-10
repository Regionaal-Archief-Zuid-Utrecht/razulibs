# Leesmij RAZU classes
*work in progress*

## Classes voor het maken van RDF

### RDFResource :: MetaResource :: StructuredMetaResource
Centrale class voor generatie van RDF is [`StructuredMetaResource`](meta_resource.py). Deze is gericht op het eenvoudig kunnen aanmaken en vullen, opslaan en inladen van RDF-objecten. Het generiekere [`MetaResource`](meta_resource.py) is agnostisch ten aanzien van de inhoud van de RDF, en kent dan ook geen standaarden zoals MDTO. Iedere instantie van `MetaResource` is te herkennen aan een `id` (een integer waarde die uniek is binnen de toegang), een geregelateerde `uid` die wel unieke identifcieert en uiteraard ook de `uri`. De basis-class [RDFResource](rdf_resource.py) biedt enkel voorzieningen om makkelijk RDF aan te maken.

### Config en Identifiers
De class [`Config`](config.py) is een generieke *singleton* class voor het vastleggen en opvragen van configuratie-parameters. Deze worden ingelezen vanuit een YAML-bestand, [`config.yaml`](../config.yaml). De logica voor het maken van identiers op basis van deze configuratie is geimplementeerd in [`Identifiers`](identifiers.py).


### ConceptResolver en Concept
[`ConceptResolver`](concept_resolver.py) kan op basis van termen die gebruikt zijn als naam of label in waardenlijsten een `Concept` teruggeven. Dit `Concept` kan bevraagd worden, bijvoorbeeld voor de waarde van een specifiek predicaat.  Opvragingen gebeuren via SPARQL. Om onnodige belasting van endpoints te vermijden is het een *singleton* class die gebruik maakt van *caching*. Een `Concept` kan ook direct geïnstantieerd worden door een bestaande concept-URI op te geven. Gebruikt [`SparqlEndpointManager`](sparql_endpoint_manager.py).

### Incrementer
[`Incrementer`](incrementer.py) biedt een eenvoudige teller die gebruikt wordt in `MetaObject` om unieke URIs of identifiers te kunnen genereren.

### Util
[`Util`](util.py) is bedoeld voor het bieden van generieke functies voor dataconversies.

## Classes voor datamanagement

### Sip
Het maken van een SIP (*submission information package*) verloopt via class [`Sip`](sip.py). Deze class maakt daarbij o.a. gebruik van [`Manifest`](manifest.py) voor het maken, controleren en aanvullen van een `manifest`-bestand van het SIP. Het manifest geeft aan welke bestanden er in een directorystructuur verwacht worden en wat de checksum van die bestanden is. Het manifest maalt het zo mogelijk om de integriteit van de data in het SIP te kunnen controleren. Via de Sip class wordt een eventlog beheerd (via [`PreservationEvents`](preservation_events.py)).

### Edepot
[`Edepot`](edepot.py) (en het onderliggende [`S3Storage`](s3storage.py)) zijn voor het  ingesten van het SIP naar de S3 storage van het edepot. 