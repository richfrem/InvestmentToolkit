import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from utils.QuestradeTokenManager import QuestradeTokenManager

def test_token_lifecycle():
    print("🚀 Starting Token Lifecycle Test...")
    
    manager = QuestradeTokenManager(cache_dir=".")
    test_data = {
        "access_token": "fake_access_123",
        "refresh_token": "fake_refresh_456",
        "api_server": "https://api.example.com",
        "expires_in": 3600
    }

    try:
        # 1. Save tokens
        print("💾 Saving encrypted tokens...")
        manager.save_tokens(test_data)
        
        # 2. Verify file exists and is not plaintext
        print("🔍 Verifying cache file content...")
        with open(".questrade_cache", "rb") as f:
            raw_data = f.read()
            
        try:
            json.loads(raw_data.decode('utf-8'))
            print("❌ FAILED: Cache file is in plaintext!")
            return False
        except (UnicodeDecodeError, json.JSONDecodeError):
            print("✅ SUCCESS: Cache file is encrypted (not a valid JSON string).")

        # 3. Load tokens
        print("📥 Loading tokens...")
        loaded_data = manager.load_tokens()
        
        if loaded_data == test_data:
            print("✅ SUCCESS: Loaded data matches original data.")
        else:
            print(f"❌ FAILED: Data mismatch!\nOriginal: {test_data}\nLoaded: {loaded_data}")
            return False

        # 4. Atomic Swap Test (Simulation)
        print("🔄 Testing Atomic Swap (save again)...")
        test_data["refresh_token"] = "new_refresh_token_789"
        manager.save_tokens(test_data)
        
        loaded_data = manager.load_tokens()
        if loaded_data["refresh_token"] == "new_refresh_token_789":
            print("✅ SUCCESS: Atomic swap/update successful.")
        else:
            print("❌ FAILED: Update did not persist correctly.")
            return False

        return True

    finally:
        print("🧹 Cleaning up...")
        manager.clear_cache()

if __name__ == "__main__":
    success = test_token_lifecycle()
    sys.exit(0 if success else 1)
