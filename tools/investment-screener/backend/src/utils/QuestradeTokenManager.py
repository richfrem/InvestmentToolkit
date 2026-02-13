import os
import json
import keyring
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from typing import Optional, Dict, Any

class QuestradeTokenManager:
    """
    Manages Questrade OAuth2 tokens with hardware-backed encryption (keyring)
    and atomic disk operations. Implements ADR 015 and ADR 019.
    """
    
    SERVICE_NAME = "InvestmentToolkit"
    KEY_ACCOUNT = "QuestradeMasterKey"
    CACHE_FILE = ".questrade_cache"

    def __init__(self, cache_dir: str = "."):
        self.cache_path = os.path.join(cache_dir, self.CACHE_FILE)
        self._key: Optional[bytes] = None

    def _get_or_create_key(self) -> bytes:
        """Retrieves or generates the AESGCM master key from the OS Keychain."""
        if self._key:
            return self._key
            
        stored_key = keyring.get_password(self.SERVICE_NAME, self.KEY_ACCOUNT)
        
        if stored_key:
            self._key = bytes.fromhex(stored_key)
        else:
            # Generate a new 256-bit key
            self._key = AESGCM.generate_key(bit_length=256)
            keyring.set_password(self.SERVICE_NAME, self.KEY_ACCOUNT, self._key.hex())
            
        return self._key

    def _encrypt(self, data: str) -> bytes:
        """Encrypts data using AES-GCM."""
        key = self._get_or_create_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        return nonce + ciphertext

    def _decrypt(self, encrypted_data: bytes) -> str:
        """Decrypts data using AES-GCM."""
        key = self._get_or_create_key()
        aesgcm = AESGCM(key)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted_data.decode('utf-8')

    def save_tokens(self, token_data: Dict[str, Any]) -> None:
        """
        Atomically saves encrypted tokens to disk.
        Pattern: Write temp -> Atomic rename (os.replace).
        """
        json_str = json.dumps(token_data)
        encrypted_bytes = self._encrypt(json_str)
        
        temp_path = self.cache_path + ".tmp"
        
        try:
            with open(temp_path, "wb") as f:
                f.write(encrypted_bytes)
            
            # Atomic swap (ADR 015)
            os.replace(temp_path, self.cache_path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise RuntimeError(f"Failed to save tokens atomically: {e}")

    def load_tokens(self) -> Optional[Dict[str, Any]]:
        """Loads and decrypts tokens from the cache file."""
        if not os.path.exists(self.cache_path):
            return None
            
        try:
            with open(self.cache_path, "rb") as f:
                encrypted_bytes = f.read()
            
            decrypted_str = self._decrypt(encrypted_bytes)
            return json.loads(decrypted_str)
        except Exception as e:
            # If decryption fails (e.g. invalid key or corrupted file), 
            # we don't return partial data.
            return None

    def clear_cache(self) -> None:
        """Deletes the local cache file."""
        if os.path.exists(self.cache_path):
            os.remove(self.cache_path)
