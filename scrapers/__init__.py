"""
Inisialisasi modul scrapers dan registrasi otomatis
"""
import logging
from .base import registry

logger = logging.getLogger(__name__)

# Import scraper yang sudah ada
try:
    from .pornwatch import pornwatch
    registry.register(pornwatch)
    logger.info("PornWatch scraper berhasil diregistrasi.")
except ImportError as e:
    logger.warning(f"Gagal memuat PornWatch scraper: {e}")

# Nanti jika Anda sudah punya mangoporn.py, tinggal tambahkan di sini:
# try:
#     from .mangoporn import mangoporn
#     registry.register(mangoporn)
# except ImportError:
#     pass

