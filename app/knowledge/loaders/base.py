from abc import ABC, abstractmethod
from pathlib import Path

from app.knowledge.models import ParsedSection


class DocumentLoader(ABC):
    @abstractmethod
    def load(
        self,
        path: Path,
    ) -> list[ParsedSection]:
        """Load document content into sections."""