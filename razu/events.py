import os
from datetime import datetime, timezone

from rdflib import URIRef

from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, PREMIS, EROR, ERO
import razu.util as util


# NL-WbDRAZU-K50907905-500.premis.json
# https://data.razu.nl/id/event/NL-WbDRAZU-K50907905-500-e17676


#  


# https://data.razu.nl/id/event/NL-WbDRAZU-{archiefvormer}-{toegang}-{timestamp}


class Events:

    _cfg = RazuConfig()

    def __init__(self, sip_directory, eventlog_filename=None):
        """
        Initialize the Events object. 
        Load the eventlog file, if it exists.
        """
        self.directory = sip_directory
        self.filepath = os.path.join(sip_directory, eventlog_filename or Events._cfg.eventlog_filename)
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
 
    def _add(self, properties, timestamp=None):
        timestamp = self._timestamp() if timestamp is None else timestamp
        event = RDFResource(self._next_uri())
        event.add_properties({
            RDF.type: PREMIS.Event,
            PREMIS.eventDateTime: self._timestamp()
        })
        event.add_properties(properties)
        self.graph += event
        self.is_modified = True

    def _next_uri(self) -> str:
        self.current_id += 1
        return f"{Events._cfg.event_uri_prefix}-e{self.current_id}"
    
    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()


class RazuEvents(Events):

    def __init__(self, sip_directory, eventlog_filename=None):
        super().__init__(sip_directory, eventlog_filename)

    # eventtypes : https://id.loc.gov/vocabulary/preservation/eventType.html
    # & see https://developer.meemoo.be/docs/metadata/knowledge-graph/0.0.1/events/en/

    def filename_change(self, subject, original_filename, new_filename):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/fil'),
            EROR.sou: URIRef(subject),
            PREMIS.originalName: original_filename,
            PREMIS.objectIdentifier: {
                PREMIS.objectIdentifierType: "filename",
                PREMIS.objectIdentifierValue: new_filename
            }
        })

    def message_digest_calculation(self, subject, timestamp, outcome, detail):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/mes'),
            EROR.sou: URIRef(subject),
            PREMIS.outcome: outcome
        }, timestamp)

    def fixity_check(self, subject, is_succesful, detail, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/fix'),
            EROR.sou: URIRef(subject),
            PREMIS.outcome: self._outcome_uri(is_succesful)
        }, timestamp)

    def format_identification(self, subject, timestamp, format):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/for'),
            EROR.sou: URIRef(subject)
        }, timestamp)

    def _outcome_uri(self, is_succesful) -> URIRef:
        return URIRef("http://id.loc.gov/vocabulary/preservation/eventOutcome/suc") if is_succesful else URIRef("http://id.loc.gov/vocabulary/preservation/eventOutcome/fail")
