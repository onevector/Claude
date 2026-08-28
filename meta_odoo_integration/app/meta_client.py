from dataclasses import dataclass

import httpx


@dataclass
class LeadData:
    leadgen_id: str
    ad_id: str | None
    form_id: str | None
    created_time: str | None
    field_data: list[dict]


class MetaClientError(RuntimeError):
    pass


async def fetch_lead(
    leadgen_id: str,
    access_token: str,
    graph_api_version: str,
) -> LeadData:
    """Fetch the actual submitted answers for a lead.

    The webhook payload only carries the leadgen_id - the form answers
    (name, email, phone, ...) have to be pulled separately from the Graph
    API using the Page access token.
    """
    url = f"https://graph.facebook.com/{graph_api_version}/{leadgen_id}"
    params = {
        "access_token": access_token,
        "fields": "id,created_time,ad_id,form_id,field_data",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, params=params)
    if response.status_code != 200:
        raise MetaClientError(
            f"Graph API error fetching lead {leadgen_id}: "
            f"{response.status_code} {response.text}"
        )
    payload = response.json()
    return LeadData(
        leadgen_id=payload.get("id", leadgen_id),
        ad_id=payload.get("ad_id"),
        form_id=payload.get("form_id"),
        created_time=payload.get("created_time"),
        field_data=payload.get("field_data", []),
    )
