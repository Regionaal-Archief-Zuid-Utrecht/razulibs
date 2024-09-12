# Leesmij RAZU classes

## MDTOObject
Centrale class vorm [`MDTOObject`](mdto_object.py).  Deze in gericht op het eenvoudig aanmaken van MDTO-objecten, zoals het creeeren van een object met een dictionary. Het is hierbij gebaseerde op generiekere classes die geen relatie hebben met MDTO. Dit zijn `RDFBase` (abstract), `BlankNode` en `Entity` (zie [rdf_structures.py](rdf_structures.py))

## Config en RAZUConfig
De class [`Config`](config.py) is een generieke singleton class voor het vastleggen van configuratie-parameters. De subclass hiervan genaamd [`RAZUConfig`](razuconfig.py) vult deze aan met parameter gebaseerde bedrijfslogica (zoals het combineren van parameters tot een nieuwe property) en parameters met *default*  waarden.

## ConceptResolver
[`ConceptResolver`](conceptresolver.py) kan termen gebruikt als naam of label in waardenlijsten vertalen naar de bijbehorende URI. Dit gebeurt via SPARQL. Om de belasting van endpoints te vermijden gebruikt het daarbij *caching* in de vorm van een *dictionary*.

## Incrementer
[`Incrementer`](incrementer.py) biedt een eenvoudige teller die gebruikt wordt in `MDTOObject` om unieke URIs of identifiers te genereren. 

## Util
[`Util`](util.py) is bedoeld voor het bieden van generieke functies voor dataconversies.