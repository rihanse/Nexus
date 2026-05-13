import re
from datetime import datetime, timedelta



def parse_leave_date(text: str) -> str | None:
    text = text.lower()
    today = datetime.now()

    if "day after tomorrow" in text:
        return (today + timedelta(days=2)).strftime("%Y-%m-%d")
    
    if "tomorrow" in text:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        
    if "today" in text:
        return today.strftime("%Y-%m-%d")

    match = re.search(r"(\d+)(?:st|nd|rd|th)", text)
    if match:
        day = int(match.group(1))
        if 1 <= day <= 31:
            try:
                target_date = today.replace(day=day)
                
                if "this month" not in text and target_date.date() < today.date():
                    # If just "25th" and it passed, bump to next month
                    if today.month == 12:
                        target_date = target_date.replace(year=today.year + 1, month=1)
                    else:
                        target_date = target_date.replace(month=today.month + 1)
                        
                return target_date.strftime("%Y-%m-%d")
            except ValueError:
                # E.g. Feb 30th
                pass

    return None

def extract_dates(text: str) -> tuple[str | None, str | None]:
    """
    Extracts dates in YYYY-MM-DD format or from natural expressions.
    """

    dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)

    if len(dates) >= 2:
        return dates[0], dates[1]

    if len(dates) == 1:
        return dates[0], dates[0]

    natural_date = parse_leave_date(text)
    if natural_date:
        return natural_date, natural_date

    return None, None


def extract_request_id(text: str) -> int | None:
    """
    Extracts request/ticket/claim ID from text.
    """

    patterns = [
        r"(?:request|ticket|claim|reimbursement|asset|leave)\s*(?:id)?\s*[:#]?\s*(\d+)",
        r"\bid\s*[:#]?\s*(\d+)",
        r"\b(\d+)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))

    return None


def extract_leave_type(text: str) -> str | None:
    text = text.lower()

    if "casual" in text:
        return "casual"

    if "sick" in text:
        return "sick"

    if "earned" in text:
        return "earned"

    return None


def extract_reason(text: str) -> str | None:
    """
    Extracts reason after words like because/for.
    """

    match = re.search(r"(?:because|reason is|due to)\s+(.+)", text, re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return None


def extract_issue_type(text: str) -> str | None:
    text = text.lower()

    if "vpn" in text:
        return "vpn"

    if "outlook" in text:
        return "outlook"

    if "email" in text:
        return "email"

    if "printer" in text:
        return "printer"

    if "network" in text:
        return "network"

    if "software installation" in text or "software install" in text:
        return "software installation"

    if "software" in text:
        return "software"

    if "laptop" in text:
        return "laptop"

    return None


def extract_priority(text: str) -> str:
    text = text.lower()

    if "high" in text or "urgent" in text or "critical" in text:
        return "high"

    if "low" in text:
        return "low"

    return "medium"


def extract_engineer_name(text: str) -> str | None:
    """
    Example: assign ticket 1 to Rahul
    """

    match = re.search(r"\bto\s+([a-zA-Z ]+)", text)

    if match:
        return match.group(1).strip().title()

    return None


def extract_asset_type(text: str) -> str | None:
    text = text.lower()

    if "vpn token" in text:
        return "vpn token"

    if "software license" in text:
        return "software license"

    if "laptop" in text:
        return "laptop"

    if "monitor" in text:
        return "monitor"

    if "keyboard" in text:
        return "keyboard"

    if "mouse" in text:
        return "mouse"

    return None


def extract_claim_type(text: str) -> str | None:
    text = text.lower()

    if "travel" in text:
        return "travel"

    if "internet" in text:
        return "internet"

    if "food" in text:
        return "food"

    if "client meeting" in text:
        return "client meeting"

    if "claim" in text or "expense" in text or "reimbursement" in text:
        return "other"

    return None


def extract_amount(text: str) -> float | None:
    """
    Extracts amount from examples like:
    - travel claim of 500
    - reimbursement 1200
    - amount is 750
    """

    match = re.search(r"(?:rs\.?|inr|amount|of)?\s*(\d+(?:\.\d+)?)", text.lower())

    if match:
        return float(match.group(1))

    return None