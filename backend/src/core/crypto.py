from cryptography.fernet import Fernet
from src.core.config import settings

_key = (
    settings.encryption_key.encode()
    if settings.encryption_key
    else Fernet.generate_key()
)
try:
    _fernet = Fernet(_key)
except ValueError:
    _key = Fernet.generate_key()
    _fernet = Fernet(_key)


def encrypt(data: str) -> str:
    """Encrypts a string."""
    return _fernet.encrypt(data.encode()).decode()


def decrypt(data: str) -> str:
    """Decrypts a string."""
    return _fernet.decrypt(data.encode()).decode()
