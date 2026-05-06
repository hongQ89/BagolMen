# Deployment Guide - Bagol Stremio Addon

Deploy the Bagol addon using one of these methods.

## Method 1: Docker Compose (Recommended - Easiest)

### Requirements
- Docker and Docker Compose installed

### Steps

1. **Clone and enter directory**
```bash
git clone https://github.com/hongQ89/BagolMen.git
cd BagolMen
```

2. **Start the addon**
```bash
docker-compose up -d
```

3. **Add to Stremio**
   - Settings → Add-ons → Install from URL
   - Enter: `http://localhost:8008/manifest.json`
   - Or from another device: `http://YOUR_IP:8008/manifest.json`

4. **View logs**
```bash
docker-compose logs -f
```

5. **Stop the addon**
```bash
docker-compose down
```

---

## Method 2: Local Python (Development)

### Requirements
- Python 3.8+
- pip

### Steps

1. **Clone and enter directory**
```bash
git clone https://github.com/hongQ89/BagolMen.git
cd BagolMen
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the addon**
```bash
python addon.py
```

5. **Add to Stremio**
   - Settings → Add-ons → Install from URL
   - Enter: `http://localhost:8008/manifest.json`

---

## Method 3: VPS with Systemd (Production)

### Requirements
- Linux VPS (Ubuntu/Debian)
- SSH access
- sudo privileges

### Steps

1. **SSH into your VPS**
```bash
ssh user@your-vps-ip
```

2. **Install dependencies**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git curl
```

3. **Clone the addon**
```bash
cd /opt
sudo git clone https://github.com/hongQ89/BagolMen.git bagol-addon
cd bagol-addon
sudo pip install -r requirements.txt
```

4. **Create systemd service**
```bash
sudo tee /etc/systemd/system/bagol-addon.service > /dev/null <<EOF
[Unit]
Description=Bagol Stremio Addon
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/bagol-addon
ExecStart=/opt/bagol-addon/start.sh production
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

5. **Enable and start service**
```bash
sudo systemctl daemon-reload
sudo systemctl enable bagol-addon
sudo systemctl start bagol-addon
```

6. **Check status**
```bash
sudo systemctl status bagol-addon
```

7. **View logs**
```bash
sudo journalctl -u bagol-addon -f
```

8. **Access the addon**
   - From your server: `http://YOUR_VPS_IP:8008/manifest.json`

---

## Method 4: Cloud Deployment (Heroku, Railway, Render)

### Heroku

1. **Install Heroku CLI**
```bash
# https://devcenter.heroku.com/articles/heroku-cli
```

2. **Login to Heroku**
```bash
heroku login
```

3. **Create app**
```bash
heroku create your-app-name
```

4. **Deploy**
```bash
git push heroku main
```

5. **View logs**
```bash
heroku logs --tail
```

6. **Access addon**
   - `https://your-app-name.herokuapp.com/manifest.json`

### Railway

1. **Connect GitHub repository** on [railway.app](https://railway.app)

2. **Add environment variables**
   - `FLASK_ENV=production`
   - `FLASK_PORT=8008`

3. **Deploy automatically from GitHub**

4. **Access addon**
   - `https://your-project.railway.app/manifest.json`

### Render

1. **Connect GitHub repository** on [render.com](https://render.com)

2. **Create new Web Service**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn --bind 0.0.0.0:8000 addon:app`

3. **Deploy automatically**

4. **Access addon**
   - `https://your-service.onrender.com/manifest.json`

---

## Method 5: Docker Hub Auto-Build

1. **Push to Docker Hub** (optional)
```bash
docker login
docker build -t yourusername/bagol-addon .
docker push yourusername/bagol-addon
```

2. **Run from Docker Hub**
```bash
docker run -d -p 8008:8008 yourusername/bagol-addon
```

---

## Configuration

### Environment Variables

Create `.env` file or set when running:

```bash
# Server
FLASK_ENV=production         # development or production
FLASK_HOST=0.0.0.0         # Listen on all interfaces
FLASK_PORT=8008            # Port number

# Scraping
REQUEST_TIMEOUT=30         # Seconds per request
MAX_RETRIES=3             # Retry failed requests
CACHE_HOURS=24            # Cache duration

# Logging
LOG_LEVEL=INFO            # DEBUG, INFO, WARNING, ERROR
```

### Using .env file

```bash
# Create .env
cat > .env <<EOF
FLASK_ENV=production
FLASK_PORT=8008
LOG_LEVEL=INFO
EOF

# Docker will automatically load it
docker-compose up -d
```

---

## Testing

### Test Scrapers

```bash
python dev.py test --query "batman"
```

### Test API Endpoints

```bash
# Make sure server is running
python dev.py run

# In another terminal
python dev.py endpoint
```

### Test Specific Scraper

```bash
python dev.py test --scraper mangoporn --query "test"
```

---

## Maintenance

### Update Code

```bash
# Pull latest changes
git pull origin main

# Restart service
docker-compose restart
# or
sudo systemctl restart bagol-addon
```

### Clear Cache

```bash
# Access via API
curl http://localhost:8008/health

# Or edit code to clear cache:
# scrapers.cache.clear()
```

### Monitor Logs

```bash
# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u bagol-addon -f

# Local
tail -f logs/*.log
```

### Performance Tuning

For high load, adjust in `docker-compose.yml`:

```yaml
environment:
  - GUNICORN_WORKERS=8  # Increase workers
  - REQUEST_TIMEOUT=60  # Increase timeout
```

---

## Troubleshooting

### Port Already in Use

```bash
# Change port
docker-compose down
# Edit docker-compose.yml, change port mapping
# Or use environment variable
FLASK_PORT=9000 docker-compose up -d
```

### Addon Not Showing

1. Check server is running: `curl http://localhost:8008/health`
2. Check firewall allows port 8008
3. Check manifest.json: `curl http://localhost:8008/manifest.json`
4. Restart Stremio

### No Results

1. Check internet connection
2. Try different search term
3. Check logs for errors
4. Sites may have changed - CSS selectors may need updating

### SSL/Certificate Errors

If connecting from HTTPS, you may need SSL proxy:

```bash
# Using nginx as reverse proxy
# See nginx configuration examples online
```

---

## Backup & Restore

### Backup Configuration

```bash
# Backup everything
tar -czf bagol-backup.tar.gz .

# Restore
tar -xzf bagol-backup.tar.gz
```

### Update from GitHub

```bash
git pull origin main
docker-compose restart
```

---

## Security Notes

⚠️ **This addon aggregates adult content. Please ensure:**
- Appropriate age restrictions in your household
- Content licensing in your jurisdiction
- No sensitive data stored locally
- Use behind firewall on private network when possible

---

## Support

- Check logs for errors
- Run `python dev.py test` to verify
- See README.md for usage
- Check GitHub issues for known problems
