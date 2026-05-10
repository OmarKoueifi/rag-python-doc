"""Runs before any submodule, so before chromadb gets imported transitively."""

import logging
import os

# chromadb 0.5.23's posthog client signature is broken against current
# posthog releases — disable telemetry both ways and silence the logger.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL + 1)
