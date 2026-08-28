import logging

from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import PlainTextResponse

from app.config import load_settings
from app.pipeline import Pipeline
from app.security import verify_meta_signature

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meta_odoo_integration")

app = FastAPI(title="Meta Lead Ads -> Odoo CRM bridge")

settings = load_settings()
pipeline = Pipeline(settings)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    """Meta calls this once, when you register/verify the webhook
    subscription in the App Dashboard. Echo back hub.challenge if the
    verify token matches what you configured there."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.meta_verify_token and challenge is not None:
        return PlainTextResponse(challenge, status_code=200)
    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_meta_signature(raw_body, signature, settings.meta_app_secret):
        logger.warning("Rejected webhook request with invalid signature")
        return PlainTextResponse("Invalid signature", status_code=403)

    payload = await request.json()

    leadgen_ids = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "leadgen":
                leadgen_id = change.get("value", {}).get("leadgen_id")
                if leadgen_id:
                    leadgen_ids.append(leadgen_id)

    for leadgen_id in leadgen_ids:
        background_tasks.add_task(pipeline.process_leadgen_id, leadgen_id)

    # Ack immediately - Meta expects a fast 200 and will retry delivery
    # (not processing) if this handler is slow or errors out.
    return PlainTextResponse("EVENT_RECEIVED", status_code=200)
