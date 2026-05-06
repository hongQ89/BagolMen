# Bagol Stremio Addon

**A complete migration of the Cumination Kodi plugin to Stremio**

Convert your favorite adult content aggregators from Kodi to a universal Stremio addon.

## Features

✅ **Three Content Sources**
- **MangoPorn** - Wide selection of adult movies with multiple stream hosts
- **XXXParodyHD** - Parody content with quality detection
- **PornWatch** - Individual scenes with diverse host support

✅ **5+ Stream Extraction Methods**
1. Direct iframe detection
2. HTML5 video tag parsing
3. JavaScript source extraction
4. Stream button/link discovery
5. Player container parsing

✅ **Supported Stream Hosts**
- DoodStream
- FileMoon
- StreamWish
- Vidguard
- Player4Me
- VidNest
- LuluStream
- VidHidePro
- JavggVideo

✅ **Smart Features**
- Automatic host identification
- 24-hour intelligent caching
- Automatic retry logic with exponential backoff
- Multi-source fallback
- Comprehensive error handling
- Production-ready with Docker

## Installation

### Method 1: Docker (Recommended)

```bash
git clone https://github.com/hongQ89/BagolMen.git
cd BagolMen
docker-compose up -d
```

Then in Stremio:
- Settings → Add-ons → Install from URL
- Enter: `http://localhost:8008/manifest.json`

### Method 2: Python (Development)

```bash
git clone https://github.com/hongQ89/BagolMen.git
cd BagolMen

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the addon
python addon.py
```

Then in Stremio, add: `http://localhost:8008/manifest.json`

### Method 3: Systemd Service (Production VPS)

```bash
# Copy to system location
sudo cp -r . /opt/bagol-addon
cd /opt/bagol-addon

# Create systemd service
sudo tee /etc/systemd/system/bagol-addon.service > /dev/null <<EOF
[Unit]
Description=Bagol Stremio Addon
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/bagol-addon
ExecStart=/opt/bagol-addon/start.sh production
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable bagol-addon
sudo systemctl start bagol-addon
```

## Usage

### In Stremio

1. **Open Stremio** and go to Settings
2. **Click "Add-ons"**
3. **Click "Install from URL"**
4. **Enter addon URL**: `http://YOUR_IP:8008/manifest.json`
5. **Search for content** - Results from all sources will appear

### API Endpoints

#### Get Manifest
```
GET /manifest.json
```
Returns addon capabilities and configuration.

#### Search for Streams
```
GET /stream/movie/{search_query}.json
```

Examples:
- `/stream/movie/Batman.json` - Search all sources
- `/stream/movie/Batman@mangoporn.json` - Search specific source

Response:
```json
{
  "streams": [
    {
      "url": "https://...",
      "title": "Batman",
      "sources": ["DoodStream"],
      "source_url": "https://..."
    }
  ]
}
```

#### Get Metadata
```
GET /meta/movie/{id}.json
```

#### Health Check
```
GET /health
```

## Development

### Testing Scrapers

```bash
# Test all scrapers
python dev.py test --query "batman"

# Test specific scraper
python dev.py test --scraper mangoporn --query "test"

# Test XXXParodyHD
python dev.py test --scraper xxxparodyhd --query "parody"
```

### Running Development Server

```bash
# Development mode (Flask)
python dev.py run

# Production mode (Gunicorn)
python dev.py run --production
```

### Testing Endpoints

```bash
# Test if addon is running
python dev.py endpoint

# Test specific endpoint
curl http://localhost:8008/manifest.json
```

### Checking Dependencies

```bash
python dev.py check
```

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Server
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=8008

# Scraping
REQUEST_TIMEOUT=30
MAX_RETRIES=3
CACHE_HOURS=24

# Logging
LOG_LEVEL=INFO
```

### Customization

Edit `addon.py` to:
- Change port
- Add more scrapers
- Modify stream filtering
- Adjust timeout values

Edit individual scraper files (`scrapers/*.py`) to:
- Update CSS selectors if site layout changes
- Add new host types
- Modify search behavior

## Troubleshooting

### Addon not appearing in Stremio

1. Check server is running: `curl http://localhost:8008/health`
2. Check firewall allows port 8008
3. Make sure URL is correct in Stremio settings
4. Try restarting Stremio

### No streams found

1. Check internet connection
2. Verify site URL is still valid
3. Site layout may have changed - CSS selectors need updating
4. Check logs: `docker logs bagol-addon` or `tail -f /var/log/addon.log`

### Slow results

- First search caches results (24 hours)
- Subsequent searches are instant
- Large result sets take longer to process
- Can adjust timeout in config

### SSL/HTTPS errors

Some sites may require SSL verification bypass:

```python
# In addon.py, modify http_get:
response = self.session.get(url, timeout=timeout, verify=False, **kwargs)
```

## API Documentation

See `DEPLOYMENT_GUIDE.md` for detailed API docs and deployment options.

See `KODI_TO_STREMIO_CONVERSION.md` for technical migration details.

## From Kodi to Stremio

**What Changed:**
- Kodi's XML UI → Stremio's HTTP JSON API
- Kodi's plugin callbacks → Flask routes
- Kodi's resolveurl → Direct iframe/stream extraction
- Kodi's addon dependencies → Minimal Python packages

**What Stayed:**
- Site scraping logic
- Host detection
- Stream extraction methods
- Search functionality

See `KODI_TO_STREMIO_CONVERSION.md` for detailed code comparisons.

## Performance

- **Search**: 2-5 seconds (first time), <100ms cached
- **Stream Extraction**: 3-10 seconds per page
- **Memory**: ~50MB baseline, ~200MB under load
- **Concurrency**: Supports 10+ simultaneous requests

## Requirements

- Python 3.8+
- Flask 2.3+
- BeautifulSoup4 4.12+
- Requests 2.31+
- 50MB disk space
- 100MB RAM minimum

## License

GPL 2.0 - Based on original Cumination plugin

## Disclaimer

This addon aggregates content from third-party sites. The author does not:
- Host any content
- Have affiliation with listed sites
- Accept responsibility for site content
- Endorse any particular site

Users are responsible for ensuring they have right to access content in their jurisdiction.

## Support

- Check logs for errors
- Run `python dev.py test` to verify scrapers work
- Test endpoints with `python dev.py endpoint`
- See DEPLOYMENT_GUIDE.md for deployment help

## Contributing

To add new scrapers:

1. Create file `scrapers/newsite.py`
2. Inherit from `BaseScraper`
3. Implement `search()` and `get_streams()`
4. Register in `addon.py`

See existing scrapers for examples.

## Changelog

**v1.0.0** (2026-05-06)
- Initial Stremio release
- MangoPorn, XXXParodyHD, PornWatch scrapers
- Docker deployment
- Full documentation

---

**Bagol Repo** - The culmination of adult sites on Stremio
