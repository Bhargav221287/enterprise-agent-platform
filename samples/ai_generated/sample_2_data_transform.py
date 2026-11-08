def normalize_user_payload(raw_data: dict) -> dict:
    """Cleans, normalizes, and filters enterprise user fields."""
    return {
        "email": raw_data.get("email", "").strip().lower(),
        "first_name": raw_data.get("first_name", "").strip().capitalize(),
        "last_name": raw_data.get("last_name", "").strip().capitalize(),
        "is_active": bool(raw_data.get("is_active", True)),
    }
