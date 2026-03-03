"""
Configuration for the ShadowLitter Automated Agent.
"""
# Default scanning parameters
POLLING_INTERVAL_DAYS = 7
MAX_CLOUD_COVER = 15.0  # Sentinel-2 metadata filter
IOU_THRESHOLD = 0.45    # Minimum overlap to consider it a "verified" change

# Alert Settings
WEBHOOK_URL = "" # Enter Slack/Discord URL
SMS_ALERTS_ENABLED = False
EMAIL_ALERTS = ["admin@madurai-corporation.gov.in"]

# Baseline Definitions
BASELINE_YEAR = 2023  # Post-monsoon state
BASELINE_MONTH = 12
