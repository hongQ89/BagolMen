# ❌ MISSING DEPENDENCIES FIX

## Problem Detected

Your Docker logs show:
```
ModuleNotFoundError: No module named 'flask_cors'
```

## Solution

The issue is that `flask_cors` is NOT in `requirements.txt`

### Fix 1: Update requirements.txt (Recommended)

Add this to your `requirements.txt`:

```
Flask==3.0.0
flask-cors==4.0.0
beautifulsoup4==4.12.2
requests==2.31.0
gunicorn==21.2.0
```

**Note:** Added `flask-cors==4.0.0` (was missing!)

### Fix 2: Install Missing Package

If you want quick fix without changing requirements.txt:

```bash
# Inside Docker
pip install flask-cors==4.0.0

# Or locally
pip install -r requirements.txt
```

### Fix 3: Rebuild Docker Image

```bash
cd /path/to/BagolMen
docker-compose down
docker-compose up -d --build
```

## Step-by-Step Fix

1. **Edit requirements.txt:**
   ```bash
   nano requirements.txt
   # or
   vi requirements.txt
   ```

2. **Add flask-cors:**
   ```
   Flask==3.0.0
   flask-cors==4.0.0
   beautifulsoup4==4.12.2
   requests==2.31.0
   gunicorn==21.2.0
   ```

3. **Rebuild Docker:**
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

4. **Verify:**
   ```bash
   docker-compose logs -f
   # Should see: "Starting Container" without ModuleNotFoundError
   ```

5. **Test:**
   ```bash
   curl http://localhost:8008/manifest.json
   ```

## Expected Output After Fix

```json
{
  "id": "org.bagolmen.stremio",
  "version": "2.1.0",
  "name": "Bagol Repo",
  ...
}
```

## If Using Python Locally

```bash
cd /path/to/BagolMen
python3 -m venv venv
source venv/bin/activate
pip install flask-cors==4.0.0
pip install -r requirements.txt
python addon.py
```

## Common Issues

### Still getting ModuleNotFoundError?

1. Clear Docker cache:
   ```bash
   docker system prune -a
   docker-compose up -d --build
   ```

2. Check if requirements.txt is in root:
   ```bash
   ls -la requirements.txt
   ```

3. Verify Docker build:
   ```bash
   docker-compose build --no-cache
   ```

## All Dependencies

Your complete `requirements.txt` should be:

```
Flask==3.0.0
flask-cors==4.0.0
beautifulsoup4==4.12.2
requests==2.31.0
gunicorn==21.2.0
```

That's it! No other dependencies needed.

---

**After fix, your addon will work perfectly!** ✅
