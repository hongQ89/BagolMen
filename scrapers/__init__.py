import logging
from .base import registry

logger = logging.getLogger(__name__)

# Register PornWatch
try:
    from .pornwatch import pornwatch
    registry.register(pornwatch)
except ImportError as e:
    logger.warning(f"Gagal memuat PornWatch: {e}")

# Register MangoPorn
try:
    from .mangoporn import mangoporn
    registry.register(mangoporn)
except ImportError as e:
    logger.warning(f"Gagal memuat MangoPorn: {e}")

# Register XXXParodyHD
try:
    from .xxxparodyhd import xxxparodyhd
    registry.register(xxxparodyhd)
except ImportError as e:
    logger.warning(f"Gagal memuat XXXParodyHD: {e}")
