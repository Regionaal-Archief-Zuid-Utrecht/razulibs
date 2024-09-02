from SPARQLWrapper import SPARQLWrapper, JSON

from .config import Config

class ConceptResolver:

    def __init__(self, base_url):
        self.config = Config()
        self.base_url = base_url
        self.cache = {}

    def _build_query(self, label):
        return f"""
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?uri WHERE {{
            ?uri skos:prefLabel|rdfs:label "{label}".
        }} LIMIT 1
        """

    def _fetch_uri(self, label):
        if label in self.cache:
            return self.cache[label]

        sparql = SPARQLWrapper(f"{self.config.sparql_prefix}{self.base_url}/sparql")
        query = self._build_query(label)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        try:
            response = sparql.query().convert()
            bindings = response.get('results', {}).get('bindings', [])

            if bindings:
                uri = bindings[0]['uri']['value']
            else:
                uri = None

            self.cache[label] = uri
            return uri

        except Exception as e:
            print(f"Error querying the SPARQL endpoint: {e}")
            return None

    def get_uri(self, label):
        return self._fetch_uri(label)
