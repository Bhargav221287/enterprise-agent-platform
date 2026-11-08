"""Domain Pack Loader and Validator for Enterprise Multi-Agent Workflows."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from app.schemas import DomainPack, PackSummary
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class DomainPackManager:
    """Manages loading, validation, and storage of domain pack definitions."""

    def __init__(self, packs_dir: Optional[Union[str, Path]] = None) -> None:
        """Initialize domain pack manager with target packs directory."""
        self.packs_dir = Path(packs_dir) if packs_dir else Path("domain_packs")
        self._packs: Dict[str, DomainPack] = {}
        self.load_all_packs()

    def validate_and_register(self, data: dict) -> DomainPack:
        """Validate raw dictionary against DomainPack schema and check graph consistency.

        Raises:
            ValueError: If structure or node references are invalid.
        """
        try:
            pack = DomainPack(**data)
        except ValidationError as exc:
            raise ValueError(f"Domain pack schema validation failed: {exc}") from exc

        # Semantic verification: verify entry_agent exists in declared agents
        agent_names = {agent.name for agent in pack.agents}
        if pack.entry_agent not in agent_names:
            raise ValueError(
                f"Entry agent '{pack.entry_agent}' is not declared in agents: {sorted(agent_names)}"
            )

        # Semantic verification: verify routing rules reference valid agent names or END
        for rule in pack.routing_rules:
            if rule.from_agent not in agent_names:
                raise ValueError(
                    f"Routing rule source '{rule.from_agent}' not declared in agents: {sorted(agent_names)}"
                )
            if rule.to_agent != "END" and rule.to_agent not in agent_names:
                raise ValueError(
                    f"Routing rule target '{rule.to_agent}' is neither 'END' nor an agent in {sorted(agent_names)}"
                )

        self._packs[pack.name] = pack
        logger.info("Loaded and registered domain pack: %s (v%s)", pack.name, pack.version)
        return pack

    def load_pack_from_file(self, file_path: Path) -> DomainPack:
        """Load and validate a single YAML domain pack file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Domain pack file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        if not isinstance(raw_data, dict):
            raise ValueError(f"Domain pack YAML must contain a dictionary, got {type(raw_data).__name__}")

        return self.validate_and_register(raw_data)

    def load_all_packs(self) -> Dict[str, DomainPack]:
        """Scan packs directory and load all .yaml and .yml files."""
        if not self.packs_dir.exists():
            logger.warning("Domain packs directory does not exist: %s", self.packs_dir)
            return self._packs

        for file_path in self.packs_dir.glob("*.y*ml"):
            try:
                self.load_pack_from_file(file_path)
            except Exception as e:
                logger.error("Failed to load domain pack from %s: %s", file_path, e)

        return self._packs

    def get_pack(self, name: str) -> Optional[DomainPack]:
        """Retrieve a loaded domain pack by name."""
        return self._packs.get(name)

    def list_packs(self) -> List[PackSummary]:
        """List summaries of all loaded domain packs."""
        return [
            PackSummary(
                name=p.name,
                version=p.version,
                description=p.description,
                default_confidence_threshold=p.default_confidence_threshold,
                entry_agent=p.entry_agent,
                agents=[a.name for a in p.agents],
            )
            for p in self._packs.values()
        ]
