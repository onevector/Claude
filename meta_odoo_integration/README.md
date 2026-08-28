# Meta Lead Ads -> Odoo CRM bridge

A small always-on webhook service that replaces Odoo's native Meta/Facebook
lead-ads integration when it's broken or unreliable. Meta sends a webhook
the instant someone submits a Lead Ad form; this service fetches the
submitted answers from the Graph API and creates a `crm.lead` in Odoo via
the standard XML-RPC external API.

```
Meta Lead Ad submitted
   -> Meta POSTs a "leadgen" webhook event (just IDs, no answers)
   -> this service verifies the request signature
   -> GET /{leadgen_id} from the Graph API for the actual field answers
   -> maps form fields to Odoo crm.lead fields
   -> crm.lead.create() over Odoo XML-RPC
   -> local SQLite record so retried/duplicate webhooks don't double-create
   -> anything that fails is appended to a dead-letter file for retry
```

## 1. Set up the Meta side

You need a Meta App with the Lead Ads / Webhooks product, permission to
read leads on the Page running the ads, and a webhook subscription
pointing at this service.

1. **Create or reuse a Meta App** at [developers.facebook.com](https://developers.facebook.com/apps)
   (Business type). If Odoo's native integration already has an app set
   up in your Business Manager, you can usually reuse it.
2. **Add the Webhooks product** to the app, subscribe to the `Page`
   object, and enable the `leadgen` field.
3. **Get a Page access token** for the Page running the ads:
   - Preferred: create a **System User** in Business Manager, assign it
     admin access to the Page, and generate a token for it. System User
     tokens don't expire the way user-linked tokens do (a common cause of
     these integrations quietly breaking every ~60 days).
   - Requires the `leads_retrieval` and `pages_manage_metadata` (or
     `pages_show_list`) permissions, which need **App Review** approval
     from Meta before they work in production (Business Verification is
     usually required too).
4. **Subscribe the app to the Page** (this step is separate from the
   webhook subscription above - it tells Meta *this Page's* leads should
   trigger *your* app's webhook):
   ```
   POST https://graph.facebook.com/v21.0/{page-id}/subscribed_apps
        ?subscribed_fields=leadgen&access_token={PAGE_ACCESS_TOKEN}
   ```
5. Once this service is deployed and reachable at a public HTTPS URL,
   register it in the App Dashboard's Webhooks settings: callback URL
   `https://your-domain/webhook`, verify token = whatever you put in
   `META_VERIFY_TOKEN`. Meta will call `GET /webhook` once to confirm it.

## 2. Set up the Odoo side

Create a dedicated API user (don't reuse a human's login) scoped to just
what this needs:

1. Settings -> Users -> create a service user, e.g.
   `meta-integration@yourcompany.com`.
2. Give it the **CRM / Sales: User** access right (enough to create
   `crm.lead` records) - avoid Administrator.
3. Generate an **API key** for that user: click into the user, "Account
   Security" tab -> "New API Key". Use this, not the account password, in
   `ODOO_API_KEY`.

## 3. Configure and run

```bash
cp .env.example .env
# fill in .env with the values from steps 1-2

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Or with Docker:

```bash
docker build -t meta-odoo-bridge .
docker run --env-file .env -p 8000:8000 -v $(pwd)/data:/data meta-odoo-bridge
```

Expose it publicly (a reverse proxy with TLS, or a platform like
Fly.io/Render/a small VM behind Caddy/nginx) - Meta requires HTTPS for
webhook callback URLs.

## 4. Field mapping

`config/field_mapping.yaml` maps the field names your Meta lead form uses
(check them in Ads Manager -> your Lead Form -> Field name column - they
vary per form) to Odoo `crm.lead` fields. Any submitted field that isn't
mapped is **not dropped** - it's still appended to the lead's Description
so you never lose data, it just won't land in a structured field until you
add a mapping line.

## 5. Reliability

- **Duplicate protection**: a local SQLite file (`data/processed_leads.sqlite3`)
  records every Meta `leadgen_id` already pushed to Odoo, so Meta's webhook
  retries (or an accidental duplicate delivery) never create a second lead.
- **Failure handling**: if the Graph API call or the Odoo create fails
  (token expired, Odoo down, network blip), the lead is logged to
  `data/dead_letter.jsonl` instead of being silently lost. Once the
  underlying issue is fixed, replay them:
  ```bash
  python -m scripts.reprocess_failed
  ```
- **Fast ack**: the webhook handler verifies the signature and returns
  `200` immediately, doing the Graph API + Odoo work in a background task -
  this keeps Meta from timing out and retrying delivery unnecessarily.

## 6. Security

Every incoming webhook POST is verified against Meta's
`X-Hub-Signature-256` header (HMAC-SHA256 of the raw body, keyed with your
`META_APP_SECRET`) before it's processed - requests that don't match are
rejected with `403` and never reach Odoo.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Known limits / things to revisit later

- Page access tokens still eventually need rotating even for System Users
  in some setups - if leads stop arriving, check `data/dead_letter.jsonl`
  first; a string of `Graph API error ... 190` (invalid/expired token) is
  the tell.
- `config/field_mapping.yaml` only handles direct string fields
  (name/email/phone/etc.). Fields that need a many2one lookup in Odoo
  (e.g. mapping a "State" answer to `state_id`) aren't auto-resolved -
  they'll show up in the Description instead until you add that lookup
  logic to `app/mapping.py`.
- This service assumes one Page/one Odoo instance. Multi-Page setups would
  need a Page ID -> Odoo config mapping in `app/pipeline.py`.
