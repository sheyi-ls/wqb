"""Combined BRAIN client interface."""
from typing import Protocol

from .alpha import AlphaAPI
from .auth import AuthAPI
from .catalog import CatalogAPI
from .simulation import SimulationAPI
from .spc import SpcAPI

__all__ = ['BrainSession']


class BrainSession(AuthAPI, CatalogAPI, AlphaAPI, SimulationAPI, SpcAPI, Protocol):
    """Full WorldQuant BRAIN HTTP client surface."""
