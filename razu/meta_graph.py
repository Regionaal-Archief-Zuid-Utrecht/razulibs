from rdflib import Graph, Namespace, RDF, RDFS, XSD, SKOS, OWL

# Namespaces for RDF properties
MDTO = Namespace("http://www.nationaalarchief.nl/mdto#")
LDTO = Namespace("https://data.razu.nl/def/ldto/")
SCHEMA = Namespace("http://schema.org/") #https://schema.org/docs/developers.html
DCT = Namespace("http://purl.org/dc/terms/")
GEO = Namespace("http://www.opengis.net/ont/geosparql#")
PREMIS = Namespace("http://www.loc.gov/premis/rdf/v3/")
PROV = Namespace("http://www.w3.org/ns/prov#")
EROR = Namespace("http://id.loc.gov/vocabulary/preservation/eventRelatedObjectRole/")
ERAR = Namespace("http://id.loc.gov/vocabulary/preservation/eventRelatedAgentRole/")
EO = Namespace("http://id.loc.gov/vocabulary/preservation/eventOutcome/")
BAG = Namespace("http://bag.basisregistraties.overheid.nl/def/bag#")  # But the incomplete (and incorrect ?) 'labs' LD enviroment for the BAG (https://data.labs.kadaster.nl/bag/lv/) as LD uses https://
PICO = Namespace("https://personsincontext.org/model#")
RAZU = Namespace("https://data.example.org/id/object/") # https://data.razu.nl/id/object/
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
PNV = Namespace("https://w3id.org/pnv#")
PO = Namespace("https://data.razu.nl/id/persoonsvermelding/")
PN = Namespace("https://data.razu.nl/id/persoonsnaam/")

class MetaGraph(Graph):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind("ldto", LDTO)
        self.bind("mdto", MDTO)
        self.bind("schema", SCHEMA)
        self.bind("dct", DCT)
        self.bind("geo", GEO)
        self.bind("premis", PREMIS)
        self.bind("prov", PROV)
        self.bind("eror", EROR)
        self.bind("erar", ERAR)
        self.bind("eo", EO)
        self.bind("owl", OWL)
        self.bind("pico", PICO)
        self.bind("razu", RAZU)
        self.bind("bag", BAG)  #RAZU.identifier, where identifier is a RAZU id like nl-wbdrazu-g0352-002-1 then a URI is generated: https://data.example.org/id/nl-wbdrazu-g0352-002-1
        self.bind("xsd", XSD)
        self.bind("pnv", PNV)
        self.bind("po", PO)
        self.bind("pn", PN)
