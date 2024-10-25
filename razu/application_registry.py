import subprocess
import re
import shutil

from razu.concept_resolver import ConceptResolver

class ApplicationRegistry:

    _applicaties = ConceptResolver('applicatie')

    def __init__(self, app_name, executable, signature_func):
        self.app_name = app_name
        self.executable = shutil.which(executable)
        self.signature_func = signature_func 

        if self.executable is None:
            raise FileNotFoundError(f"Executable for {self.app_name} not found in PATH or specified location")
        
        self.signature = self.signature_func(self)
        self.uri = ApplicationRegistry._applicaties.get_concept_uri(self.signature)
        self.is_registered = True if self.uri else False

    def get_command_output(self, command_args):
        try:
            result = subprocess.run([self.executable] + command_args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command for {self.app_name}: {e}")
            return ""
        

# Specifieke signature-functie voor DROID
def droid_signature_func(appregistry: ApplicationRegistry) -> str:
    version = appregistry.get_command_output(['-v'])
    detailed_output = appregistry.get_command_output(['-x'])
    versions = '/'.join(re.findall(r"Version:\s+(\S+)", detailed_output))
    return f"{appregistry.app_name} {version}/{versions}"

# Specifieke signature-functie voor ClamAV
def clamav_signature_func(appregistry: ApplicationRegistry) -> str:
    version = appregistry.get_command_output(['--version']).lower()
    parts = version.split("/")
    version = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
    return version.strip() if version else "unknown-version"


# Voorbeeldgebruik:
if __name__ == "__main__":
    droid = ApplicationRegistry("droid", "/home/rene/bin/droid/droid.sh", droid_signature_func)
    clamav = ApplicationRegistry("clamav", "clamscan", clamav_signature_func)

    if droid.is_registered:
        print(f"Current version of {droid.app_name} is registered at {droid.uri}.")
    else:
        print(f"{droid.signature} is not yet registered.")

    if clamav.is_registered:
        print(f"Current version of {clamav.app_name} is registered at {clamav.uri}.")
    else:
        print(f"{clamav.signature} is not yet registered.")

