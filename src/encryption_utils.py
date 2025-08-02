from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Standardized path - always use config/.env from project root
load_dotenv("config/.env")

KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
if not KEY:
    raise ValueError("TOKEN_ENCRYPTION_KEY must be set in config/.env file")

fernet = Fernet(KEY.encode())

def encrypt_token(token: str) -> str:
    return fernet.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    return fernet.decrypt(encrypted_token.encode()).decode()

# Simple test
if __name__ == "__main__":
    enc = encrypt_token("my_secret_token")
    print("Encrypted:", enc)
    dec = decrypt_token(enc)
    print("Decrypted:", dec)
