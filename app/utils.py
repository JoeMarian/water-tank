import random
import string

def generate_api_key(length: int = 12) -> str:
    characters = string.ascii_uppercase + string.digits  # A-Z, 0-9
    return ''.join(random.choices(characters, k=length))
