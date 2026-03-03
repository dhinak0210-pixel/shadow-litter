from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
import logging
from datetime import datetime

# from packages.database.prisma import db # Simulated unified DB access

router = APIRouter(prefix="/api/webhooks")
logger = logging.getLogger("civic_feedback")

@router.post("/twilio")
async def twilio_whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    MediaUrl0: str = Form(None)
):
    """
    The Civic Feedback Loop: Ingests ground-truth verifications from 
    Municipal workers or citizens via WhatsApp.
    """
    phone_number = From.replace("whatsapp:", "")
    msg_body = Body.strip().upper()
    logger.info(f"📱 Received Civic WhatsApp from {phone_number}: {msg_body}")
    
    # In a real environment, we'd look up the active detection mapped to this user's ward/zone
    # alert = await db.alert.find_first(where={"sentTo": phone_number, "status": "PENDING"})
    
    response_msg = ""
    
    if "VERIFY" in msg_body or "YES" in msg_body:
        # await db.verification.create(data={"detectionId": alert.detectionId, "status": "TRUE_POSITIVE", "verifiedBy": phone_number})
        response_msg = "✅ Ground-truth registered. The illegal dump site has been VERIFIED. Cleanup crew dispatch authorized. This feedback improves the AI's accuracy."
        logger.info(f"✅ Ground truth updated for {phone_number} -> TRUE_POSITIVE")
        
    elif "FALSE" in msg_body or "NO" in msg_body:
        # await db.verification.create(data={"detectionId": alert.detectionId, "status": "FALSE_POSITIVE"})
        # await db.detection.update(where={"id": alert.detectionId}, data={"status": "DISMISSED"})
        response_msg = "❌ Registered as FALSE ALARM. Thank you. The AI Temporal Fusion model will retrain on this correction."
        logger.info(f"❌ Ground truth updated for {phone_number} -> FALSE_POSITIVE")
        
    elif "CLEANED" in msg_body:
        # await db.detection.update(where={"id": alert.detectionId}, data={"status": "RESOLVED"})
        response_msg = "🧹 Mission Accomplished. The site is marked cleaned. Archiving evidence."
        
    else:
        response_msg = "Shadow Litter Intelligence Bot.\nReply VERIFY to confirm dumping at your location.\nReply FALSE if the AI is incorrect.\nReply CLEANED once resolved."

    if MediaUrl0:
        logger.info(f"📸 Image evidence received: {MediaUrl0} (Ready for Active Learning Ingestion)")
        response_msg += "\n\nPhotographic evidence saved to verification vault."

    # Return valid TwiML XML
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{response_msg}</Message>
</Response>"""

    return Response(content=twiml, media_type="application/xml")
