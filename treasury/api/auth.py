from app.auth import verify_auth_group, hash_password, verify_auth_id
from app.utils import generate_auth_id


def verify_auth(login, password):
    user_id = generate_auth_id(login, hash_password(password))
    if not verify_auth_id(user_id) or not verify_auth_group(user_id, "treasury"):
        return False
    return True
