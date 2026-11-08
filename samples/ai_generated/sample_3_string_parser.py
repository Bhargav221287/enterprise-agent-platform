def parse_incident_id(ticket_text: str) -> dict:
    """Extracts and standardizes incident tags from ticket titles."""
    cleaned = ticket_text.strip()
    prefix = cleaned[:3].upper() if len(cleaned) >= 3 else "INC"
    return {
        "raw_text": cleaned,
        "prefix": prefix,
        "is_valid": len(cleaned) > 0,
    }
