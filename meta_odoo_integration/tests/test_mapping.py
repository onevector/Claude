from app.mapping import build_lead_vals
from app.meta_client import LeadData

MAPPING = {
    "full_name": "contact_name",
    "email": "email_from",
    "phone_number": "phone",
    "company_name": "partner_name",
}


def _lead(field_data):
    return LeadData(
        leadgen_id="lg_123",
        ad_id="ad_456",
        form_id="form_789",
        created_time="2026-08-28T00:00:00+0000",
        field_data=field_data,
    )


def test_maps_known_fields_to_odoo_vals():
    lead = _lead(
        [
            {"name": "full_name", "values": ["Jane Doe"]},
            {"name": "email", "values": ["jane@example.com"]},
            {"name": "phone_number", "values": ["+15551234567"]},
        ]
    )
    vals = build_lead_vals(lead, MAPPING)
    assert vals["contact_name"] == "Jane Doe"
    assert vals["email_from"] == "jane@example.com"
    assert vals["phone"] == "+15551234567"


def test_unmapped_fields_preserved_in_description():
    lead = _lead(
        [
            {"name": "full_name", "values": ["Jane Doe"]},
            {"name": "favorite_color", "values": ["teal"]},
        ]
    )
    vals = build_lead_vals(lead, MAPPING)
    assert "favorite_color: teal" in vals["description"]
    assert "lg_123" in vals["description"]


def test_first_last_name_combined_when_no_full_name():
    lead = _lead(
        [
            {"name": "first_name", "values": ["Jane"]},
            {"name": "last_name", "values": ["Doe"]},
        ]
    )
    vals = build_lead_vals(lead, MAPPING)
    assert vals["contact_name"] == "Jane Doe"


def test_opportunity_name_falls_back_to_form_id():
    lead = _lead([{"name": "email", "values": ["only@example.com"]}])
    vals = build_lead_vals(lead, MAPPING)
    assert "form_789" in vals["name"]


def test_multi_value_field_joined():
    lead = _lead([{"name": "full_name", "values": ["A", "B"]}])
    vals = build_lead_vals(lead, MAPPING)
    assert vals["contact_name"] == "A, B"
