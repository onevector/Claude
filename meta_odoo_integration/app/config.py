import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    meta_app_secret: str
    meta_verify_token: str
    meta_page_access_token: str
    meta_graph_api_version: str
    odoo_url: str
    odoo_db: str
    odoo_username: str
    odoo_api_key: str
    data_dir: Path
    field_mapping_path: Path
    port: int


def load_settings() -> Settings:
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        meta_app_secret=_require("META_APP_SECRET"),
        meta_verify_token=_require("META_VERIFY_TOKEN"),
        meta_page_access_token=_require("META_PAGE_ACCESS_TOKEN"),
        meta_graph_api_version=os.environ.get("META_GRAPH_API_VERSION", "v21.0"),
        odoo_url=_require("ODOO_URL").rstrip("/"),
        odoo_db=_require("ODOO_DB"),
        odoo_username=_require("ODOO_USERNAME"),
        odoo_api_key=_require("ODOO_API_KEY"),
        data_dir=data_dir,
        field_mapping_path=Path(os.environ.get("FIELD_MAPPING_PATH", "./config/field_mapping.yaml")),
        port=int(os.environ.get("PORT", "8000")),
    )
