"""
A better machine lib.

PyPI: https://pypi.org/project/wqb/
GitHub: https://github.com/rocky-d/wqb
"""

__version__ = '0.2.5'

from . import common
from . import api
from . import impl

__all__ = common.__all__ + api.__all__ + impl.__all__

from .common import *  # noqa: F403, E402
from .api import *  # noqa: F403, E402
from .impl import *  # noqa: F403, E402
