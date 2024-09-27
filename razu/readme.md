# Leesmij RAZU classes

## Manifest
[`Manifest`](manifest.py) biedt een class met methods voor het maken, controleren en aanvullen van een `manifest`-bestand. Het manifest geeft aan welke bestanden er in een directorystructuur verwacht worden en wat de checksum van die bestanden is. Het manifest makat het zo mogelijk om de integriteit van de data te kunnen controleren. 

## MDTOObject
Centrale class voor generatie van RDF is [`MDTOObject`](mdto_object.py). Deze is gericht op het eenvoudig kunnen aanmaken en vullen van MDTO-objecten, zoals het creëren van een object met een dictionary. Het is hierbij gebaseerd op generiekere classes die geen directe relatie hebben met MDTO of een ander model. Dit zijn `RDFBase` (een abstracte class), `BlankNode` en `Entity` (zie [rdf_structures.py](rdf_structures.py)). 

## Config en RAZUConfig
De class [`Config`](config.py) is een generieke *singleton* class voor het vastleggen en opvragen van configuratie-parameters. De subclass hiervan genaamd [`RAZUConfig`](razuconfig.py) vult deze aan met parameter gebaseerde bedrijfslogica (zoals het combineren van parameters tot een nieuwe property) en parameters met *default*  waarden.

## ConceptResolver en Concept
[`ConceptResolver`](conceptresolver.py) kan op basis van termen die gebruikt zijn als naam of label in waardenlijsten een `Concept` teruggeven. Dit `Concept` kan bevraagd worden, bijvoorbeeld voor de waarde van een specifiek predicaat.  Opvragingen gebeuren via SPARQL. Om onnodige belasting van endpoints te vermijden gebruikt het daarbij *caching* in de vorm van een *dictionary*.
Een `Concept` kan ook direct geïnstantieerd worden door een bestaande concept-URI op te geven. Gebruikt [`SparqlEndpointManager`](sparql_endpoint_manager.py).

## Incrementer
[`Incrementer`](incrementer.py) biedt een eenvoudige teller die gebruikt wordt in `MDTOObject` om unieke URIs of identifiers te kunnen genereren.

## Util
[`Util`](util.py) is bedoeld voor het bieden van generieke functies voor dataconversies.
