## config.yaml

- Changed `razu_file_id` from `"NL-WbDRAZU"` to `"nl-wbdrazu"` (lowercase)
- Changed `razu_base_uri` from `"https://data.razu.nl/"` to `"https://data.razu.nl/id/"` than I can simply what is after the slash in the code (object, perceel, etc. else here I don't know how to specify multiple segments bc it's a singleton and I need more than one at the same time)
- 

## identifiers.py > razu_uris.py
changing with the logic that this class will handle uris, namely:
1. storage base uri (needs gemeentecode) # https://g0352.opslag.razu.nl/ `cdn_base_uri`
2. triply base uri # https://data.razu.nl/id/id/object/ `object_uri_prefix` > but without the uid_base in the end!


- eliminate `uid_base`, `make_uid_from_id` > in *idegenerator* 
- eliminate `make_filename_from_id` > can maybe be in utils 
- eliminate `make_s3_path_from_id` > in *idegenerator* (also creates a stepped path for s3 ID)

## meta_resource.py (MetaResource, StructuredMetaResource) 
they are both subclasses of RDFRsource, why in different files?

I think the whole subclass dependencies are very convoluted. I can ignore the complexity for now, but still I need to change how StructuredMetaResource is initialized as it hard codes values for InformateObject and I need to define those myself.

- eliminate `self._init_rdf_properties(rdf_type)` and related method `def _init_rdf_properties(self, rdf_type) -> None:`. This internal method indirectly called `add_properties` of RDFResource which adds graph triples from a dictionary in input (via the *omonimous* method of StructuredMetaResource which adds a is_new=bool, wrapper to work with load/save)

this method is used in Sip and I did not check yet if I need to reuse it, but I added the same logic into Sip.create_meta_resource so it doesn't break.
- also removed the `rdf_type` param in `StructuredMetaResource.__init__` as it is not used anymore

- added `uri`parameter to `StructuredMetaResource.__init__` to be able to pass the uri directly (it is already inherited via RDFFResource so...)

- in StructuredMetaResource:```load```and ```save``` have looong call chain to create filenames that goes all the way back to the config files:

```
    save() / load()
    ↓
    self.local_file_path  (line 44, 52, 62)
    ↓
    os.path.join(MetaResource._context.sip_directory, self.filename)
    ↓
    self.filename  (line 40)
    ↓
    MetaResource._id_factory.make_filename_from_id(self.id)  (line 76-78 in identifiers.py)
    ↓
    f"{self.uid_base}-{id}.{self.config.metadata_suffix}.{self.config.metadata_extension}"
    ↓
    self.uid_base  (line 12-20 in identifiers.py)
    ↓
    f"{self.config.razu_file_id}-{self.config.archive_creator_id}-{self.config.archive_id}"
```

the result should be something like ```nl-wbdrazu-k50907905-689-965992.meta.json```.
I already have the identifier so I don't need all these complex factory chain calls if I can just use the attribute id of the class. Hence I overrid the `filename` method to use the id directly.

```python
    @property
    def filename(self) -> str:
        """Override parent's filename to use self.id directly without factory call chain."""
        cfg = MetaResource._context
        return f"{self.id}.{cfg.metadata_suffix}.{cfg.metadata_extension}"
```

- eliminated imports and dependencies of ```Identifiers``` and ```Incrementer```

## sip.py
- added `from rdflib import URIRef
- `from razu.meta_graph import MetaGraph, LDTO` adds RDF, DCT, PREMIS
- new ` def create_meta_resource`:
    ```
          meta_resource = StructuredMetaResource(id)
        meta_resource.add_properties({
            RDF.type: rdf_type,
            LDTO.identificatie: {
                RDF.type: LDTO.IdentificatieGegevens,
                LDTO.identificatieBron: "e-Depot RAZU",
                LDTO.identificatieKenmerk: meta_resource.uri
            },
            DCT.hasFormat: URIRef(meta_resource.metadata_file_uri)
        })
        if rdf_type == LDTO.Informatieobject:
            meta_resource.add_properties({
                LDTO.waardering: StructuredMetaResource._waarderingen.get_concept('B').get_uri(),
                LDTO.archiefvormer: StructuredMetaResource._actoren.get_concept(self.cfg.archive_creator_id).get_uri()
            })
        meta_resource.add_triple(URIRef(meta_resource.metadata_file_uri), RDF.type, PREMIS.File)
        self.meta_resources[meta_resource.id] = meta_resource
        return meta_resource
    ```

######################################3

csv2rdf.py (main)
│
├── Config (razu.config)
│   ├── cfg = Config.initialize()
│   │   └── Loads config.yaml → exposes settings as attributes via __getattr__
│   │
│   ├── cfg.add_properties(archive_id, archive_creator_id, sip_directory)
│   │   └── Adds runtime settings to the same _settings dict
│   │
│   └── Accessed for:
│       ├── cfg.default_sip_directory    (from YAML)
│       ├── cfg.default_metadata_directory (from YAML)
│       ├── cfg.archive_id               (added at runtime)
│       ├── cfg.archive_creator_id       (added at runtime)
│       └── cfg.storage_base_domain      (from YAML)
│
├── StructuredMetaResource (razu.meta_resource)
│   │
│   │  # On class load (before any instance is created):
│   ├── _context = Config.get_instance()     ← retrieves the same singleton
│   ├── _id_factory = Identifiers(_context)  ← creates Identifiers with Config
│   │
│   │  # On instantiation (e.g. archive = StructuredMetaResource()):
│   ├── MetaResource.__init__()
│   │   ├── id = Incrementer.next()          ← auto-assigns sequential ID
│   │   ├── uri = Identifiers.make_uri_from_id(id)
│   │   │         └── builds URI like "https://data.razu.nl/id/object/{uid_base}-{id}"
│   │   │             using config.razu_base_uri, config.razu_file_id, etc.
│   │   └── RDFResource.__init__(uri)        ← creates rdflib.Graph + sets self.uri
│   │
│   ├── StructuredMetaResource.__init__()
│   │   └── _init_rdf_properties()
│   │       ├── Sets RDF.type, LDTO.identificatie (using self.uri)
│   │       ├── metadata_file_uri → Identifiers.cdn_base_uri + make_s3_path_from_id()
│   │       └── Sets LDTO.archiefvormer via ConceptResolver
│   │
│   │  # When csv2rdf calls .save():
│   ├── save()
│   │   ├── local_file_path = cfg.sip_directory + Identifiers.make_filename_from_id()
│   │   └── Serializes graph to JSON-LD → writes file
│   │
│   │  # When csv2rdf builds URLBestand:
│   └── bestand._id_factory.make_s3_path_from_id(bestand.id)
│       └── Identifiers uses config.razu_file_id, archive_creator_id, archive_id
│           to build S3 path like "NL-WbDRAZU/g0321/661/000/000/"
│
└── Identifiers (razu.identifiers)   ← used ONLY through MetaResource._id_factory
    │
    ├── Initialized with Config instance
    │
    ├── uid_base (property)
    │   └── "{config.razu_file_id}-{config.archive_creator_id}-{config.archive_id}"
    │       e.g. "NL-WbDRAZU-g0321-661"
    │
    ├── make_uri_from_id(id)      ← called in MetaResource.__init__
    │   └── "https://data.razu.nl/id/object/NL-WbDRAZU-g0321-661-{id}"
    │
    ├── make_uid_from_id(id)      ← used for filenames & URLs
    │   └── "NL-WbDRAZU-g0321-661-{id}"
    │
    ├── make_filename_from_id(id) ← called in MetaResource.save()
    │   └── "NL-WbDRAZU-g0321-661-{id}.meta.json"
    │
    ├── make_s3_path_from_id(id)  ← called in csv2rdf for URLBestand
    │   └── "NL-WbDRAZU/g0321/661/000/000/"
    │
    └── cdn_base_uri (property)   ← used in metadata_file_uri
        └── "https://g0321.opslag.razu.nl/"