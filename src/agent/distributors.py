"""
src/agent/distributors.py
──────────────────────────
Alert distribution system — routes detections to the right recipients.

  CorporationFeed  → weekly PDF report + GeoJSON for Madurai Corporation GIS team
  WhatsAppBot      → ward-specific alerts via Twilio / WhatsApp Business API
  ResearcherAPI    → FastAPI endpoint for research queries
"""
from __future__ import annotations
import json, logging, os
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Corporation Feed ──────────────────────────────────────────────────────────

class CorporationFeed:
    """Generates weekly reports for Madurai Municipal Corporation."""

    def __init__(self, output_dir: str = "outputs/reports"):
        self.out_dir = Path(output_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def generate_weekly_report(self, alerts: list[dict], week_date: Optional[date] = None) -> dict:
        week = (week_date or date.today()).isoformat()
        paths = {}

        # GeoJSON
        features = []
        for a in alerts:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]},
                "properties": {k: v for k, v in a.items() if k not in ("lon","lat","whatsapp_message")},
            })
        geojson = {"type": "FeatureCollection", "features": features}
        gj_path = self.out_dir / f"detections_{week}.geojson"
        gj_path.write_text(json.dumps(geojson, indent=2))
        paths["geojson"] = str(gj_path)

        # CSV
        import csv
        csv_path = self.out_dir / f"detections_{week}.csv"
        if alerts:
            with open(csv_path, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=[k for k in alerts[0] if k != "whatsapp_message"])
                w.writeheader()
                w.writerows([{k: v for k, v in a.items() if k != "whatsapp_message"} for a in alerts])
        paths["csv"] = str(csv_path)

        # PDF heatmap
        try:
            pdf_path = self._generate_heatmap_pdf(alerts, week)
            paths["pdf"] = str(pdf_path)
        except Exception as e:
            logger.warning(f"PDF generation failed: {e}")

        logger.info(f"Weekly report generated: {paths}")
        return paths

    def _generate_heatmap_pdf(self, alerts: list[dict], week: str) -> Path:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from matplotlib.backends.backend_pdf import PdfPages

        pdf_path = self.out_dir / f"heatmap_{week}.pdf"
        lats = [a["lat"] for a in alerts]
        lons = [a["lon"] for a in alerts]
        sizes = [max(a.get("area_sqm", 100) / 10, 20) for a in alerts]
        confs = [a.get("confidence", 0.5) for a in alerts]

        with PdfPages(pdf_path) as pdf:
            fig, ax = plt.subplots(figsize=(12, 9), facecolor="#0d1117")
            ax.set_facecolor("#0d1117")
            scatter = ax.scatter(lons, lats, s=sizes, c=confs, cmap="hot",
                                  alpha=0.8, edgecolors="#ff6b35", linewidths=0.5)
            plt.colorbar(scatter, ax=ax, label="Confidence", fraction=0.02)
            ax.set_xlabel("Longitude", color="white"); ax.set_ylabel("Latitude", color="white")
            ax.set_title(f"shadow-litter | Madurai Waste Detections | Week of {week}",
                         color="white", fontsize=14, fontweight="bold", pad=15)
            ax.tick_params(colors="white"); [s.set_edgecolor("#1e3a5f") for s in ax.spines.values()]
            # Madurai center reference
            ax.axhline(9.9252, color="#4fc3f7", alpha=0.3, ls="--", lw=0.8)
            ax.axvline(78.1198, color="#4fc3f7", alpha=0.3, ls="--", lw=0.8)
            ax.text(78.1198, 9.9252, " Madurai\n center", color="#4fc3f7", fontsize=8)
            plt.tight_layout()
            pdf.savefig(fig, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close()
        return pdf_path

    def deliver_email(self, report_paths: dict, recipient: str) -> None:
        """Send report via SMTP. Set SMTP_HOST, SMTP_USER, SMTP_PASS env vars."""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders

        host = os.environ.get("SMTP_HOST", ""); user = os.environ.get("SMTP_USER", "")
        pw = os.environ.get("SMTP_PASS", "")
        if not all([host, user, pw]):
            logger.warning("SMTP credentials not set. Skipping email delivery.")
            return

        msg = MIMEMultipart()
        msg["From"] = user; msg["To"] = recipient
        msg["Subject"] = f"shadow-litter Weekly Report {date.today().isoformat()}"
        msg.attach(MIMEText("Please find attached the weekly waste detection report.", "plain"))

        for label, path in report_paths.items():
            if Path(path).exists():
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{Path(path).name}"')
                    msg.attach(part)

        with smtplib.SMTP_SSL(host, 465) as server:
            server.login(user, pw); server.send_message(msg)
        logger.info(f"Report emailed to {recipient}")


# ── WhatsApp Bot ──────────────────────────────────────────────────────────────

class WhatsAppBot:
    """Ward-specific alerts via Twilio WhatsApp API."""

    def __init__(self):
        try:
            from twilio.rest import Client
            self.client = Client(
                os.environ.get("TWILIO_SID", ""),
                os.environ.get("TWILIO_TOKEN", ""),
            )
            self.from_number = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        except ImportError:
            logger.warning("pip install twilio  to enable WhatsApp alerts")
            self.client = None

    def ward_specific_alerts(self, alerts: list[dict], ward_number: str) -> list[dict]:
        ward_alerts = [a for a in alerts if str(a.get("ward")) == str(ward_number)]
        return ward_alerts

    def send_alert(self, alert: dict, to_number: str) -> bool:
        if self.client is None:
            logger.warning("Twilio not configured"); return False
        try:
            msg = self.client.messages.create(
                body=alert["whatsapp_message"],
                from_=self.from_number,
                to=f"whatsapp:{to_number}",
            )
            logger.info(f"WhatsApp sent: {msg.sid}")
            return True
        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}"); return False

    def broadcast_ward(self, alerts: list[dict], ward: str, recipients: list[str]) -> None:
        ward_alerts = self.ward_specific_alerts(alerts, ward)
        if not ward_alerts:
            logger.info(f"Ward {ward}: no alerts this week"); return
        for recipient in recipients:
            for alert in ward_alerts:
                self.send_alert(alert, recipient)


# ── Researcher API ────────────────────────────────────────────────────────────

def create_researcher_api(db_path: str = "data/shadow_litter.db"):
    """Create FastAPI app for research queries. Run with: uvicorn ...:app"""
    try:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError("pip install fastapi uvicorn")

    from src.agent.database import DumpArchive

    app = FastAPI(title="shadow-litter Research API", version="0.1.0")
    archive = DumpArchive(db_path)

    @app.get("/api/dumps")
    def query_dumps(zone: str = None, start_date: str = None, status: str = "active", limit: int = 100):
        results = archive.query_history(zone=zone, status=status, since=start_date, limit=limit)
        return JSONResponse(content={"count": len(results), "dumps": results})

    @app.get("/api/stats")
    def stats():
        return archive.stats()

    @app.get("/api/dump/{dump_id}/timeline")
    def timeline(dump_id: int):
        return archive.get_dump_timeline(dump_id)

    return app
