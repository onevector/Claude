import xmlrpc.client
from typing import Any


class OdooClientError(RuntimeError):
    pass


class OdooClient:
    """Thin wrapper around Odoo's XML-RPC external API.

    Uses only the standard library's xmlrpc.client - no Odoo-specific SDK
    dependency, so it works against any Odoo Online, Odoo.sh, or
    self-hosted instance that exposes the standard /xmlrpc/2 endpoints.
    """

    def __init__(self, url: str, db: str, username: str, api_key: str):
        self._url = url
        self._db = db
        self._username = username
        self._api_key = api_key
        self._uid: int | None = None
        self._common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        self._models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

    def _authenticate(self) -> int:
        if self._uid is None:
            uid = self._common.authenticate(self._db, self._username, self._api_key, {})
            if not uid:
                raise OdooClientError("Odoo authentication failed - check ODOO_DB/ODOO_USERNAME/ODOO_API_KEY")
            self._uid = uid
        return self._uid

    def _execute(self, model: str, method: str, *args: Any) -> Any:
        uid = self._authenticate()
        return self._models.execute_kw(self._db, uid, self._api_key, model, method, list(args))

    def create_lead(self, vals: dict[str, Any]) -> int:
        try:
            lead_id = self._execute("crm.lead", "create", [vals])
        except xmlrpc.client.Fault as exc:
            raise OdooClientError(f"Odoo rejected crm.lead.create: {exc.faultString}") from exc
        return lead_id
