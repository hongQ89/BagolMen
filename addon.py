from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging
import re

# Konfigurasi Logging untuk memantau aktivitas server di dashboard Render
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inisialisasi Aplikasi Flask
app = Flask(__name__)
# CORS wajib diaktifkan agar Stremio bisa menarik data dari server luar
CORS(app)

# ==========================================
# KONFIGURASI MANIFEST STREMIO
# ==========================================
MANIFEST = {
    "id": "org.bagolmen.stremio",
    "version": "2.1.0",
    "name": "Bagol Repo",
    "description": "Kodi Cumination plugin migrated to Stremio. Multi-source content aggregator.",
    "types": ["movie"],
    "catalogs": [
        {
            "type": "movie",
            "id": "bagol_search",
            "name": "Bagol Search",
            "extra": [{"name": "search", "isRequired": True}]
        }
    ],
    "resources": ["stream", "meta"],
    "idPrefixes": ["bagol:", "tt"],
    "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/42/Stremio_logo.svg/1200px-Stremio_logo.svg.png"
}

# ==========================================
# INPUT VALIDATION
# ==========================================

def validate_query(query: str) -> bool:
    """
    Validate search query untuk mencegah injection attacks
    
    Args:
        query: Search query
    
    Returns:
        True if valid, False otherwise
    """
    if not query or len(query.strip()) == 0:
        return False
    
    # Max length check
    if len(query) > 100:
        logger.warning(f"Query too long: {len(query)} chars")
        return False
    
    # Check untuk suspicious characters
    suspicious_chars = ['<', '>', '{', '}', 'javascript:', 'onclick', 'onerror']
    query_lower = query.lower()
    
    for char in suspicious_chars:
        if char in query_lower:
            logger.warning(f"Suspicious character detected: {char}")
            return False
    
    return True


def sanitize_query(query: str) -> str:
    """
    Sanitize query string
    
    Args:
        query: Raw query string
    
    Returns:
        Sanitized query
    """
    # Remove extra whitespace
    query = ' '.join(query.split())
    
    # Remove special chars but keep spaces and alphanumeric
    query = re.sub(r'[^\w\s\-]', '', query)
    
    return query.strip()


# ==========================================
# RUTE / ENDPOINT SERVER
# ==========================================

@app.route('/')
@app.route('/manifest.json')
def addon_manifest():
    """Memberikan spesifikasi manifest ke klien Stremio"""
    return jsonify(MANIFEST)


@app.route('/catalog/<type>/<id>/search=<query>.json')
def addon_catalog(type, id, query):
    """Menangani permintaan pencarian dari kotak pencarian Stremio"""
    
    # Validate input
    if not validate_query(query):
        logger.warning(f"Invalid query received: {query}")
        return jsonify({"metas": []}), 400
    
    clean_query = sanitize_query(query)
    logger.info(f"Menerima pencarian untuk: {clean_query}")
    
    # Mengembalikan objek meta sebagai representasi hasil pencarian
    meta = {
        "id": f"bagol:{clean_query}",
        "type": "movie",
        "name": f"Hasil Pencarian: {clean_query}",
        "description": f"Pilih item ini untuk mencari sumber stream '{clean_query}'",
        "poster": MANIFEST["logo"],
        "posterShape": "landscape"
    }
    return jsonify({"metas": [meta]})


@app.route('/meta/<type>/<id>.json')
def addon_meta(type, id):
    """Memberikan metadata saat judul pencarian diklik"""
    
    # Validate input
    if not validate_query(id):
        logger.warning(f"Invalid id received: {id}")
        return jsonify({"error": "Invalid id"}), 400
    
    clean_title = sanitize_query(id.replace("bagol:", ""))
    
    meta = {
        "id": id,
        "type": "movie",
        "name": clean_title,
        "description": "Mencari stream di MangoPorn, XXXParodyHD, dan PornWatch...",
        "poster": MANIFEST["logo"],
        "background": MANIFEST["logo"]
    }
    return jsonify({"meta": meta})


@app.route('/stream/<type>/<id>.json')
def addon_stream(type, id):
    """Endpoint utama untuk menjalankan scraper dan mengembalikan link video"""
    
    # Validate input
    if not validate_query(id):
        logger.warning(f"Invalid id received: {id}")
        return jsonify({"streams": []}), 400
    
    streams = []
    clean_query = sanitize_query(id.replace("bagol:", ""))
    logger.info(f"Mengeksekusi pencarian stream untuk: {clean_query}")
    
    try:
        # Import registry dari modul scrapers
        from scrapers.base import registry
        
        # Jalankan semua scraper dengan async/timeout support
        results = registry.scrape_all_async(clean_query, timeout=20)
        
        # Kumpulkan semua stream dari berbagai sumber
        for scraper_id, scraper_streams in results.items():
            if not scraper_streams:
                continue
            
            for s in scraper_streams:
                # Validation: check if stream object is valid
                if not s or not hasattr(s, 'url') or not s.url:
                    logger.debug(f"Skipping invalid stream from {scraper_id}")
                    continue
                
                # Safely get sources
                sources_text = 'Direct'
                if hasattr(s, 'sources') and s.sources and len(s.sources) > 0:
                    sources_text = s.sources[0]
                
                # Safely get title
                title = getattr(s, 'title', 'Unknown')
                if not title:
                    title = 'Stream'
                
                # Build stream object
                stream_obj = {
                    "url": s.url,
                    "title": f"[{scraper_id.upper()}] {sources_text}\n{title}",
                    "name": "BagolMen"
                }
                
                streams.append(stream_obj)
                logger.debug(f"Added stream: {sources_text} from {scraper_id}")
        
        if not streams:
            logger.info(f"No streams found for: {clean_query}")
                
    except Exception as e:
        logger.error(f"Terjadi kesalahan saat scraping stream: {e}", exc_info=True)
        return jsonify({"error": str(e), "streams": []}), 500
    
    return jsonify({"streams": streams})


@app.route('/health')
def health_check():
    """
    Pemeriksaan status peladen dengan scraper health status
    (sering digunakan oleh layanan cloud seperti Render)
    """
    try:
        from scrapers.base import registry
        
        scraper_status = {}
        
        # Quick health check untuk setiap scraper
        for scraper in registry.get_all():
            try:
                logger.debug(f"Health check for {scraper.SCRAPER_ID}...")
                
                # Try a quick search dengan timeout
                results = scraper.search("test", timeout=5)
                
                if results and len(results) > 0:
                    scraper_status[scraper.SCRAPER_ID] = {
                        "status": "ok",
                        "message": f"Found {len(results)} results"
                    }
                else:
                    scraper_status[scraper.SCRAPER_ID] = {
                        "status": "no_results",
                        "message": "Search returned no results"
                    }
                    
            except Exception as e:
                scraper_status[scraper.SCRAPER_ID] = {
                    "status": "error",
                    "message": str(e)
                }
        
        return jsonify({
            "status": "ok",
            "addon": MANIFEST["name"],
            "version": MANIFEST["version"],
            "scrapers": scraper_status
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 Not Found: {request.path}")
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 Internal Server Error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# Titik eksekusi lokal
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8008))
    # Jangan gunakan debug=True di production
    app.run(host='0.0.0.0', port=port, debug=False)
