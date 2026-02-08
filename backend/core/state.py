from typing import List, Dict, Any

# In-memory buffers for threat events
# Shared between the poller (writer) and the API (reader)
automated_threats: List[Dict[str, Any]] = []
manual_scans: List[Dict[str, Any]] = []
