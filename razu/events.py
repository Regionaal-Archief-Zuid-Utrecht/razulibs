import os
from datetime import datetime, timezone

from rdflib import URIRef

from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, PREMIS, EROR, ERAR, PROV
import razu.util as util


# NL-WbDRAZU-K50907905-500.premis.json
# https://data.razu.nl/id/event/NL-WbDRAZU-K50907905-500-e17676

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
            PROV.endedAtTime: self._timestamp()
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
    # https://id.loc.gov/vocabulary/preservation.html
    # https://www.loc.gov/standards/premis/ontology/pdf/premis3-owl-guidelines-20180924.pdf
    # & see https://developer.meemoo.be/docs/metadata/knowledge-graph/0.0.1/events/en/

    def filename_change(self, subject, original_filename, new_filename, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/fil'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PREMIS.outcomeNote: f"renamed {original_filename} to {new_filename}",
            PROV.generated: new_filename
        })

    def fixity_check(self, subject, is_succesful, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/fix'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(is_succesful)
        }, timestamp)

    def format_identification(self, subject, format, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/for'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PROV.generated: format
        }, timestamp)

    def ingestion_end(self, subject, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/ine'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True)
        }, timestamp)

    def ingestion_start(self, subject, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/ins'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True)
        }, timestamp)

    def message_digest_calculation(self, subject, hash, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/mes'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PROV.generated: hash            # TODO: als DROID de tool is, hoe maken we dan expliciet dat het een md5hash is?
        }, timestamp)

    def virus_check(self, subject, is_succesful, note, tool, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/vir'),
            EROR.sou: URIRef(subject),
            ERAR.exe: URIRef('https://data.razu.nl/id/tools/TODO'),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PREMIS.outcomeNote: note,
        }, timestamp)


    def _outcome_uri(self, is_succesful) -> URIRef:
        return URIRef("http://id.loc.gov/vocabulary/preservation/eventOutcome/suc") if is_succesful else URIRef("http://id.loc.gov/vocabulary/preservation/eventOutcome/fail")
