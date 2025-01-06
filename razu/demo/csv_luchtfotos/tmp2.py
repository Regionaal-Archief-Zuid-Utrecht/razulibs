from razu.sip import Sip   

# cfg = Config.get_instance()

sip = Sip.load_existing("sip", "bestanden")

sip.meta_resources.export_rdf()

sip.manifest.validate()