# Project Chronos Settings

Project Chronos now supports centralized configuration via the `chronos/settings.py` module. This allows for easier customization and deployment in different environments.

## Overview

The settings module provides configuration options for:
- Database connection
- API server 
- Scraper behavior
- Caching

## Usage

To use the settings in your code:

```python
from chronos.settings import DB_URL, API_HOST, API_PORT

# Use settings values in your code
```

## Environment Variables

All settings can be overridden using environment variables:

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| DB_FILE | CHRONOS_DB_FILE | BASE_DIR/chronos.db | Path to SQLite database file |
| DB_ECHO | CHRONOS_DB_ECHO | False | Enable SQLAlchemy query logging |
| API_HOST | CHRONOS_API_HOST | 127.0.0.1 | API server host |
| API_PORT | CHRONOS_API_PORT | 8000 | API server port |
| API_WORKERS | CHRONOS_API_WORKERS | 1 | Number of API workers |
| API_DEBUG | CHRONOS_API_DEBUG | False | Enable API debug mode |
| SCRAPER_TIMEOUT | CHRONOS_SCRAPER_TIMEOUT | 30 | Scraper request timeout in seconds |
| SCRAPER_USER_AGENT | CHRONOS_SCRAPER_USER_AGENT | Chronos/0.1.0... | User agent for scraper requests |
| CACHE_ENABLED | CHRONOS_CACHE_ENABLED | True | Enable response caching |
| CACHE_TTL | CHRONOS_CACHE_TTL | 3600 | Cache time-to-live in seconds |

## Example

To run the API server on a custom port with debugging:

```bash
export CHRONOS_API_PORT=9000
export CHRONOS_API_DEBUG=true
python -m api.main
```

## Integration

The settings module has been integrated with:
- Database connection in `chronos/db.py`
- API server in `api/main.py`
- Scrapers in `chronos/scrapers/base.py`

You can now easily add new settings as needed by extending `chronos/settings.py`.