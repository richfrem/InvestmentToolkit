
import json
import subprocess
import sys
import os

# Test Payload with new fields
payload = {
    "ticker": "TEST",
    "id": "verify-schema-123",
    "source": "AI_AGENT",
    "schemaVersion": "1.1",
    "version": 1,
    "savedAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
    "name": "Verification Test",
    "isDefault": True,  # New field
    "snapshot": {
        "price": 100,
        "currency": "USD",
        "shares": 1000,
        "revenue": 100000,
        "lastActualPS": 1.0
    },
    "dataPreferences": {
        "growthBasis": "next",
        "marginBasis": "next"
    },
    "scenarios": {
        "bear": {
            "weight": 0.2,
            "growthRate": 5,
            "netMargin": 10,
            "exitPE": 15,
            "qualityMultiplier": 1.0,
            "shareChange": 0,
            "moatScore": 1,        # New field
            "managementScore": 2   # New field
        },
        "base": {
            "weight": 0.6,
            "growthRate": 10,
            "netMargin": 15,
            "exitPE": 20,
            "qualityMultiplier": 1.0,
            "shareChange": -1,
            "moatScore": 3,        # New field
            "managementScore": 4   # New field
        },
        "bull": {
            "weight": 0.2,
            "growthRate": 15,
            "netMargin": 20,
            "exitPE": 25,
            "qualityMultiplier": 1.0,
            "shareChange": -2,
            "moatScore": 5,        # New field
            "managementScore": 5   # New field
        }
    },
    "globalSettings": {
        "discountRate": 10,
        "timeHorizon": 5
    },
    "aiThesis": {
        "model": "TestModel",
        "fairValue": 150,
        "action": "BUY",
        "rationale": "Test rationale"
    }
}

# Run persist_projection.py via subprocess
script_path = "tools/investment-screener/backend/py_services/persist_projection.py"
input_json = json.dumps(payload)

try:
    process = subprocess.Popen(
        ['python3', script_path, '--replace'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=input_json)

    if process.returncode == 0:
        print("✅ SUCCESS: Backend accepted payload with new fields.")
        print(stdout)
    else:
        print("❌ FAILURE: Backend rejected payload.")
        print("STDERR:", stderr)
        sys.exit(1)

except Exception as e:
    print(f"❌ EXECUTION ERROR: {e}")
    sys.exit(1)
