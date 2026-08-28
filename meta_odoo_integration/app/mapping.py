from pathlib import Path
from typing import Any

import yaml

from app.meta_client import LeadData


def load_field_mapping(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    return {k: v for k, v in data.items() if isinstance(v, str)}


def _flatten(field_data: list[dict]) -> dict[str, str]:
    """Meta returns each field as {"name": ..., "values": [...]}; most
    lead-form fields are single-answer, so join multi-values for safety."""
    flat = {}
    for entry in field_data:
        name = entry.get("name")
        values = entry.get("values") or []
        if name:
            flat[name] = ", ".join(str(v) for v in values)
    return flat


def build_lead_vals(lead: LeadData, mapping: dict[str, str]) -> dict[str, Any]:
    """Build the vals dict for crm.lead.create().

    Every raw answer is preserved in the description, even ones that are
    also mapped to a structured field, so the original submission is
    always auditable from the lead record.
    """
    flat = _flatten(lead.field_data)

    vals: dict[str, Any] = {}
    for meta_field, odoo_field in mapping.items():
        value = flat.get(meta_field)
        if value:
            # last mapping for a given odoo_field wins only if non-empty,
            # so e.g. first_name/last_name both targeting contact_name
            # don't clobber a value with a blank one
            vals[odoo_field] = value

    if "first_name" in flat or "last_name" in flat:
        full = f"{flat.get('first_name', '')} {flat.get('last_name', '')}".strip()
        if full:
            vals["contact_name"] = full

    form_label = lead.form_id or "unknown form"
    vals.setdefault("name", f"Facebook Lead - {flat.get('full_name') or vals.get('contact_name') or form_label}")

    description_lines = [f"Meta lead ID: {lead.leadgen_id}", f"Ad ID: {lead.ad_id}", f"Form ID: {lead.form_id}", "", "Submitted answers:"]
    for name, value in flat.items():
        description_lines.append(f"- {name}: {value}")
    vals["description"] = "\n".join(description_lines)

    return vals
