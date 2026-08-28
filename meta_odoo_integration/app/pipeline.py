import asyncio
import logging

from app.config import Settings
from app.mapping import build_lead_vals, load_field_mapping
from app.meta_client import MetaClientError, fetch_lead
from app.odoo_client import OdooClient, OdooClientError
from app.store import DeadLetterQueue, ProcessedLeadsStore

logger = logging.getLogger("meta_odoo_integration")


class Pipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = ProcessedLeadsStore(settings.data_dir / "processed_leads.sqlite3")
        self.dead_letter = DeadLetterQueue(settings.data_dir / "dead_letter.jsonl")
        self.odoo = OdooClient(settings.odoo_url, settings.odoo_db, settings.odoo_username, settings.odoo_api_key)
        self.field_mapping = load_field_mapping(settings.field_mapping_path)

    async def process_leadgen_id(self, leadgen_id: str) -> None:
        if self.store.is_processed(leadgen_id):
            logger.info("Skipping already-processed lead %s", leadgen_id)
            return
        try:
            lead = await fetch_lead(
                leadgen_id,
                self.settings.meta_page_access_token,
                self.settings.meta_graph_api_version,
            )
            vals = build_lead_vals(lead, self.field_mapping)
            odoo_lead_id = await asyncio.to_thread(self.odoo.create_lead, vals)
            self.store.mark_processed(leadgen_id, odoo_lead_id)
            logger.info("Created Odoo crm.lead %s from Meta lead %s", odoo_lead_id, leadgen_id)
        except (MetaClientError, OdooClientError) as exc:
            logger.error("Failed to process lead %s: %s", leadgen_id, exc)
            self.dead_letter.add(leadgen_id, str(exc))
        except Exception as exc:  # noqa: BLE001 - last resort so nothing crashes the background task silently
            logger.exception("Unexpected error processing lead %s", leadgen_id)
            self.dead_letter.add(leadgen_id, f"unexpected error: {exc}")
