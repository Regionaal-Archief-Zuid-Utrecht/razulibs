import os
from datetime import datetime, timezone

from rdflib import URIRef

from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, PREMIS
import razu.util as util


# NL-WbDRAZU-K50907905-500.premis.json
# https://data.razu.nl/id/event/NL-WbDRAZU-K50907905-500-e17676


#  


# https://data.razu.nl/id/event/NL-WbDRAZU-{archiefvormer}-{toegang}-{timestamp}



class Events:

    _cfg = RazuConfig()

    def __init__(self, sip_directory, eventlog_filename):
        """
        Initialize the Events object. 
        Load the eventlog file, if it exists.
        """
        self.directory = sip_directory
        self.filepath = os.path.join(sip_directory, eventlog_filename)
        self.current_id = 0

        self.graph = MetaGraph()
        self.is_modified = False

        if os.path.exists(self.filepath):
            self.graph.parse(self.filepath, format="json-ld")

            for s in self.graph.subjects():
                if isinstance(s, URIRef):
                    extracted_id = util.extract_id_str_from_filepath(s)
                    event_id = int(extracted_id[1:])
                    self.current_id = max(self.current_id, event_id)


    def save(self):
        if self.is_modified:
            try:
                with open(self.filepath, 'w') as file:
                    file.write(self.graph.serialize(format='json-ld'))
                self.is_modified = False
            except IOError as e:
                print(f"Error saving file {self.filepath}: {e}")

    def add(self, subject, event_type, outcome, details):
        self.current_id += 1
        event = RDFResource(f"{Events._cfg.event_uri_prefix}-e{self.current_id}")
        event.add_properties({
            RDF.type: PREMIS.Event
        })
        self.graph += event
        self.is_modified = True

