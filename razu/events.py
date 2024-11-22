import os
from datetime import datetime, timezone

from rdflib import URIRef, Literal

from razu.razuconfig import RazuConfig
from razu.rdf_resource import RDFResource
from razu.meta_graph import MetaGraph, RDF, XSD, PREMIS, EROR, ERAR, PROV
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
        self.file_path = os.path.join(sip_directory, eventlog_filename or Events._cfg.eventlog_filename)
        self.current_id = 0

        self.graph = MetaGraph()
        self.queue = []
        self.is_modified = False

        if os.path.exists(self.file_path):
            # Use explicit UTF-8 encoding when parsing the JSON-LD file
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.graph.parse(data=f.read(), format="json-ld")

            for s in self.graph.subjects():
                if isinstance(s, URIRef):
                    extracted_id = util.extract_id_str_from_filepath(s)
                    event_id = int(extracted_id[1:])
                    self.current_id = max(self.current_id, event_id)

        self.is_locked = any(self.graph.triples((None, URIRef("http://www.loc.gov/premis/rdf/v3/eventType"), URIRef("http://id.loc.gov/vocabulary/preservation/eventType/ine"))))

    def to_queue(self, event, *args, **kwargs):
        """Voegt een event toe aan de queue voor uitgesteld uitvoeren."""
        # Sla args en kwargs op met lambda voor uitgestelde evaluatie waar nodig
        deferred_args = [arg if callable(arg) else lambda: arg for arg in args]
        deferred_kwargs = {k: (v if callable(v) else lambda: v) for k, v in kwargs.items()}
        self.queue.append((event, deferred_args, deferred_kwargs))

    def process_queue(self):
        """Verwerkt de queue en voert elke functie uit met actuele waarden."""
        for event, args, kwargs in self.queue:
            func = getattr(self, event)
            # Voer elke lambda uit om de actuele waarden op te halen
            resolved_args = [arg() if callable(arg) else arg for arg in args]
            resolved_kwargs = {k: (v() if callable(v) else v) for k, v in kwargs.items()}
            func(*resolved_args, **resolved_kwargs)
        self.queue.clear()

    def save(self):
        if self.is_locked:
            raise AssertionError("Sip is locked. Cannot save eventlog.")
        if self.is_modified:
            try:
                with open(self.file_path, 'w', encoding='utf-8') as file:
                    file.write(self.graph.serialize(format='json-ld'))
                self.is_modified = False
            except IOError as e:
                print(f"Error saving file {self.file_path}: {e}")
 
    def _add(self, properties, tool=None, timestamp=None, started_at=None):
        if self.is_locked:
            raise AssertionError("Sip is locked. Cannot store resource.")
        timestamp = self._timestamp() if timestamp is None else timestamp
        event = RDFResource(self._next_uri())
        event.add_properties({
            RDF.type: PREMIS.Event,
            PROV.endedAtTime: Literal(timestamp,  datatype=XSD.dateTime)
        })
        if tool is not None:
            event.add_properties({
                ERAR.exe: URIRef(tool)
            })
        if started_at is not None:
            event.add_properties({
                PROV.startedAtTime: Literal(started_at,  datatype=XSD.dateTime)
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

    # eventtypes : https://id.loc.gov/vocabulary/preservation/eventType.html
    # https://id.loc.gov/vocabulary/preservation.html
    # https://www.loc.gov/standards/premis/ontology/pdf/premis3-owl-guidelines-20180924.pdf
    # & see https://developer.meemoo.be/docs/metadata/knowledge-graph/0.0.1/events/en/

    def filename_change(self, subject, original_filename, new_filename, tool=None, timestamp=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/fil'),
            EROR.sou: URIRef(subject),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PREMIS.outcomeNote: f"renamed {original_filename} to {new_filename}"
        }, tool=tool)

    def fixity_check(self, subject, is_succesful, tool=None, timestamp=None, started_at=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/fix'),
            EROR.sou: URIRef(subject),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(is_succesful)
        }, tool, timestamp, started_at)

    def format_identification(self, subject, format, tool=None, timestamp=None, started_at=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/for'),
            EROR.sou: URIRef(subject),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PREMIS.outcomeNote: format
        }, tool, timestamp, started_at)

    def ingestion_end(self, subject, tool=None, timestamp=None):
        subject_value = [URIRef(s) for s in subject] if isinstance(subject, list) else URIRef(subject)
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/ine'),
            EROR.sou: subject_value,
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True)
        }, tool, timestamp)

    def ingestion_start(self, subject, tool=None, timestamp=None):
        subject_value = [URIRef(s) for s in subject] if isinstance(subject, list) else URIRef(subject)
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/ins'),
            EROR.sou: subject_value,
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True)
        }, tool, timestamp)

    def message_digest_calculation(self, subject, hash, tool=None, timestamp=None, started_at=None):
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/mes'),
            EROR.sou: URIRef(subject),
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PREMIS.outcomeNote: hash            # TODO: als DROID de tool is, hoe maken we dan expliciet dat het een md5hash is?
        }, tool, timestamp, started_at)

    def metadata_modification(self, subject, result, tool=None, timestamp=None):
        subject_value = [URIRef(s) for s in subject] if isinstance(subject, set) else URIRef(subject)
        self._add({ 
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/mem'),
            EROR.sou: subject_value,
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PROV.generated: URIRef(result)
        }, tool, timestamp)

    def virus_check(self, subject, is_successful, note, tool=None, timestamp=None, started_at=None):
        subject_value = [URIRef(s) for s in subject] if isinstance(subject, list) else URIRef(subject)
        self._add({
            PREMIS.eventType: URIRef('http://id.loc.gov/vocabulary/preservation/eventType/vir'),
            EROR.sou: subject_value,
            ERAR.imp: URIRef('https://data.razu.nl/id/actor/2bdb658a032a405d71c19159bd2bbb3a'),
            PREMIS.outcome: self._outcome_uri(True),
            PREMIS.outcomeNote: note,
        }, tool, timestamp, started_at)

    def _outcome_uri(self, is_successful) -> URIRef:
        return URIRef("http://id.loc.gov/vocabulary/preservation/eventOutcome/suc") if is_successful else URIRef("http://id.loc.gov/vocabulary/preservation/eventOutcome/fail")
