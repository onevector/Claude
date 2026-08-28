import os
import tempfile

# Set required env vars before any test module imports app.main / app.config,
# so Settings() construction (which happens at module import time) succeeds
# without needing a real .env file or live Meta/Odoo credentials.
os.environ.setdefault("META_APP_SECRET", "test-app-secret")
os.environ.setdefault("META_VERIFY_TOKEN", "test-verify-token")
os.environ.setdefault("META_PAGE_ACCESS_TOKEN", "test-page-token")
os.environ.setdefault("ODOO_URL", "https://example.odoo.com")
os.environ.setdefault("ODOO_DB", "test-db")
os.environ.setdefault("ODOO_USERNAME", "test@example.com")
os.environ.setdefault("ODOO_API_KEY", "test-api-key")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
os.environ.setdefault("FIELD_MAPPING_PATH", "./config/field_mapping.yaml")
