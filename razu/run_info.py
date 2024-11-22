import json
from datetime import datetime, timezone
from pathlib import Path

from razu.application_registry import ApplicationRegistry


class RunInfo():
    RUN_INFO_SUFFIX = "_run_info.json" 

    def __init__(self, directory: str, application: str | ApplicationRegistry):
        self.directory = directory
        self.name = None
        self.uri = None
        self.start_time = None
        self.end_time = None
        
        if isinstance(application, str):
            self.id = application
            self._load()
        elif isinstance(application, ApplicationRegistry):
            self.id = application.id()
            self.name = application.name()
            self.uri = application.uri
        else:
            raise TypeError("application moet een string of ApplicationRegistry zijn")
        
    def register_start(self) -> None:
        self.start_time = self._now()

    def register_end(self) -> None:
        self.end_time = self._now()

    def save(self, result:str = "") -> None:
        with self._run_info_path().open("w", encoding="utf-8") as file:
            json.dump({
                "name": self.name,
                "uri": self.uri, 
                "start_time": self.start_time,
                "end_time": self.end_time,
                "result": result
            }, file, indent=4)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _load(self) -> None:
        run_info_path = self._run_info_path()
        if not run_info_path.exists():
            raise FileNotFoundError(f"Run info file not found: {run_info_path}")
        with run_info_path.open("r", encoding="utf-8") as file:
            try:
                info = json.load(file)
                self.name = info['name']
                self.uri = info['uri']
                self.start_time = info['start_time']
                self.end_time = info['end_time']
            except json.JSONDecodeError as e:
                raise ValueError(f"Corrupted JSON in {run_info_path}: {e}")
            
    def _run_info_path(self) -> Path:
        return Path(self.directory,  f"{self.id}{RunInfo.RUN_INFO_SUFFIX}")
