from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from backend.services.apify_service import apify_service
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging

router = APIRouter(prefix="/ingest/apify", tags=["Apify Integration"])
logger = logging.getLogger(__name__)

class ScrapeRequest(BaseModel):
    actor_id: str
    run_input: Dict[str, Any]

@router.post("/trigger")
async def trigger_scrape(request: ScrapeRequest):
    """
    Manually trigger an Apify scrape.
    Example Actor IDs:
    - LinkedIn: 'curious_programmer/linkedin-profile-scraper'
    - Google Maps: 'compass/google-maps-scraper'
    """
    result = apify_service.run_actor(request.actor_id, request.run_input)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result

@router.post("/webhook")
async def apify_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook endpoint called by Apify when a run completes.
    Payload typically contains {"eventType": "ACTOR.RUN.SUCCEEDED", "resource": {...}}
    """
    payload = await request.json()
    logger.info(f"Received Apify webhook: {payload}")
    
    event_type = payload.get("eventType")
    resource = payload.get("resource", {})
    run_id = resource.get("id")
    dataset_id = resource.get("defaultDatasetId")

    if event_type == "ACTOR.RUN.SUCCEEDED" and dataset_id:
        # Fetching data can be slow, so we do it in the background
        background_tasks.add_task(process_apify_dataset, dataset_id, run_id)
    
    return {"status": "received"}

async def process_apify_dataset(dataset_id: str, run_id: str):
    """
    Background task to fetch and process data from Apify.
    For now, we just log it. In a real scenario, this would save to the DB.
    """
    logger.info(f"Processing dataset {dataset_id} for run {run_id}")
    items = apify_service.get_dataset_items(dataset_id)
    
    logger.info(f"Retrieved {len(items)} items from Apify run {run_id}")
    # TODO: Pass 'items' to your Ingestion Service or save to 'Lead' table
    # Example:
    # for item in items:
    #     IngestionService.process_lead(item)
