KEYRING_SERVICE = 'cli-anything-openwebui'


def _key(profile: str, base_url: str) -> str:
    return f'{profile}:{base_url.rstrip("/")}'


def get_token(profile: str, base_url: str) -> str | None:
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, _key(profile, base_url))
    except Exception:
        return None


def set_token(profile: str, base_url: str, token: str) -> bool:
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, _key(profile, base_url), token)
        return True
    except Exception:
        return False


def delete_token(profile: str, base_url: str) -> bool:
    try:
        import keyring

        keyring.delete_password(KEYRING_SERVICE, _key(profile, base_url))
        return True
    except Exception:
        return False

