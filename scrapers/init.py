import logging
from .base import registry

logger = logging.getLogger(__name__)

# Register PornWatch
try:
    from .pornwatch import pornwatch
    registry.register(pornwatch)
    logger.info("✓ PornWatch registered")
except ImportError as e:
    logger.warning(f"✗ Gagal memuat PornWatch: {e}")
except Exception as e:
    logger.error(f"✗ Error registering PornWatch: {e}")

# Register MangoPorn
try:
    from .mangoporn import mangoporn
    registry.register(mangoporn)
    logger.info("✓ MangoPorn registered")
except ImportError as e:
    logger.warning(f"✗ Gagal memuat MangoPorn: {e}")
except Exception as e:
    logger.error(f"✗ Error registering MangoPorn: {e}")

# Register XXXParodyHD
try:
    from .xxxparodyhd import xxxparodyhd
    registry.register(xxxparodyhd)
    logger.info("✓ XXXParodyHD registered")
except ImportError as e:
    logger.warning(f"✗ Gagal memuat XXXParodyHD: {e}")
except Exception as e:
    logger.error(f"✗ Error registering XXXParodyHD: {e}")

logger.info(f"Total scrapers registered: {len(registry.get_all())}")
