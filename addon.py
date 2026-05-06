from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import logging

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
    "version": "2.0.0",
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
    logger.info(f"Menerima pencarian untuk: {query}")
    
    # Mengembalikan objek meta sebagai representasi hasil pencarian
    meta = {
        "id": f"bagol:{query}",
        "type": "movie",
        "name": f"Hasil Pencarian: {query}",
        "description": f"Pilih item ini untuk mencari sumber stream '{query}'",
        "poster": MANIFEST["logo"],
        "posterShape": "landscape"
    }
    return jsonify({"metas": [meta]})

@app.route('/meta/<type>/<id>.json')
def addon_meta(type, id):
    """Memberikan metadata saat judul pencarian diklik"""
    clean_title = id.replace("bagol:", "").replace("%20", " ")
    
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
    streams = []
    clean_query = id.replace("bagol:", "").replace("%20", " ")
    logger.info(f"Mengeksekusi pencarian stream untuk: {clean_query}")
    
    try:
        # Import registry dari modul scrapers
        from scrapers.base import registry
        
        # Jalankan semua scraper yang terdaftar
        results = registry.scrape_all(clean_query)
        
        # Kumpulkan semua stream dari berbagai sumber
        for scraper_id, scraper_streams in results.items():
            for s in scraper_streams:
                # Menangani format data Stream object dari base.py
                sources_text = s.sources[0] if hasattr(s, 'sources') and s.sources else 'Direct'
                streams.append({
                    "url": s.url,
                    "title": f"[{scraper_id.upper()}] {sources_text}\n{s.title}",
                    "name": "BagolMen"
                })
                
    except Exception as e:
        logger.error(f"Terjadi kesalahan saat scraping stream: {e}")
        
    return jsonify({"streams": streams})

@app.route('/health')
def health_check():
    """Pemeriksaan status peladen (sering digunakan oleh layanan cloud seperti Render)"""
    return jsonify({
        "status": "ok", 
        "addon": MANIFEST["name"], 
        "version": MANIFEST["version"]
    })

# Titik eksekusi lokal
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8008))
    # Jangan gunakan debug=True di production
    app.run(host='0.0.0.0', port=port, debug=False)
