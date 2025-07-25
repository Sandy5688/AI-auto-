from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

load_dotenv("../config/.env") # Adjust as above!
KEY = os.getenv("TOKEN_ENCRYPTION_KEY")
print("Loaded key from env:", KEY)  # Should print your key, not None!

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
