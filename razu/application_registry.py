import subprocess
import re
import shutil

from razu.concept_resolver import ConceptResolver

class ApplicationRegistry:

    _applicaties = ConceptResolver('applicatie')

    def __init__(self, app_name, executable, signature_func, force):
        self.app_name = app_name
        self.executable = shutil.which(executable)
        self.signature_func = signature_func 

        if self.executable is None:
            raise FileNotFoundError(f"Executable for {self.app_name} not found in PATH or specified location")
        
        self.signature = self.signature_func()
        self.uri = ApplicationRegistry._applicaties.get_concept_uri(self.signature)
        self.is_registered = True if self.uri else False

        if self.is_registered is False and force is not True:
            print(f"Application {self.app_name} with signature {self.signature} is not registered.")
            print("Exiting...")
            exit()

    def get_command_output(self, command_args):
        try:
            result = subprocess.run([self.executable] + command_args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error executing command for {self.app_name}: {e}")
            return ""


class Applications(ApplicationRegistry):

    def __init__(self, executable, force=False):
        super().__init__(self.app_name(), executable, self._signature_func, force)


class Droid(Applications):

    def app_name(self):
        return("Droid")

    def _signature_func(self) -> str:
        # geeft signature als "droid 6.8.0-118-20240501"
        # executable bijvoorbeeld "/home/user/bin/droid/droid.sh"
        version = self.get_command_output(['-v'])
        detailed_output = self.get_command_output(['-x'])
        versions = '-'.join(re.findall(r"Version:\s+(\S+)", detailed_output))
        return f"{self.app_name.lower()} {version}-{versions}"


class ClamAV(Applications):

    def app_name(self):
        return("ClamAV")

    def _signature_func(self) -> str:
        # geeft signature als "clamav 0.103.12/27434"
        # executable bijvoorbeeld "clamscan"
        version = self.get_command_output(['--version']).lower()
        parts = version.split("/")
        version = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        return version.strip() if version else "unknown-version"


