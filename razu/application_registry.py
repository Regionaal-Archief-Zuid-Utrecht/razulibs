import subprocess
import re
import shutil
from razu.concept_resolver import ConceptResolver


class ApplicationNotFoundError(Exception):
    pass


class ApplicationNotRegisteredError(Exception):
    pass


class ApplicationRegistry:
    _applicaties = ConceptResolver('applicatie')

    def __init__(self, executable, force=False):
        self.executable = shutil.which(executable)
        
        if self.executable is None:
            raise ApplicationNotFoundError(f"Executable for {self.app_name()} not found in PATH or specified location ({executable}).")
        
        self.signature = self._signature_func()
        self.uri = self._applicaties.get_concept_uri(self.signature)
        self.is_registered = bool(self.uri)

        if not self.is_registered and not force:
            raise ApplicationNotRegisteredError(f"Application {self.app_name()} with signature {self.signature} is not registered.")

    def get_command_output(self, command_args):
        try:
            result = subprocess.run([self.executable] + command_args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error executing command for {self.app_name()}: {e}")

    def _signature_func(self) -> str:
        """Subclasses moeten deze methode implementeren."""
        raise NotImplementedError

    def app_name(self) -> str:
        """Subclasses moeten de naam van de applicatie teruggeven."""
        raise NotImplementedError


class Droid(ApplicationRegistry):

    def app_name(self) -> str:
        return "Droid"

    def _signature_func(self) -> str:
        version = self.get_command_output(['-v'])
        detailed_output = self.get_command_output(['-x'])
        versions = '-'.join(re.findall(r"Version:\s+(\S+)", detailed_output))
        return f"{self.app_name().lower()} {version}-{versions}"


class ClamAV(ApplicationRegistry):

    def app_name(self) -> str:
        return "ClamAV"

    def _signature_func(self) -> str:
        version = self.get_command_output(['--version']).lower()
        parts = version.split("/")
        version = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        return version.strip() if version else "unknown-version"
