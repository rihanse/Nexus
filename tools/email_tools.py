import requests
from config import POWER_AUTOMATE_URL, TEST_EMAIL_ADDRESS


def send_email(to: str, subject: str, body: str) -> dict:
    """
    Sends email using Power Automate HTTP Trigger.
    If Power Automate URL is not configured, it safely simulates email.
    """
    if not to or not subject or not body:
        return {
            "success": False,
            "message": "Missing email recipient, subject, or body.",
            "mode": "simulation"
        }

    original_to = to
    if TEST_EMAIL_ADDRESS:
        to = TEST_EMAIL_ADDRESS
        body = f"[Simulated routing from {original_to}]\n\n{body}"

    if not POWER_AUTOMATE_URL:
        print(f"\n[EMAIL SIMULATION]\nTo: {to}\nSubject: {subject}\nBody: {body}\n")
        return {
            "success": True,
            "message": "Email skipped: Power Automate URL not configured.",
            "mode": "simulation"
        }

    print(f"\n[SENDING EMAIL via Power Automate]\nTo: {to}\nSubject: {subject}\nBody: {body}\n")

    payload = {
        "to": to,
        "subject": subject,
        "body": body
    }

    try:
        response = requests.post(
            POWER_AUTOMATE_URL,
            json=payload,
            timeout=10
        )

        if response.status_code in [200, 201, 202]:
            return {
                "success": True,
                "message": "Email sent successfully.",
                "mode": "power_automate"
            }

        return {
            "success": False,
            "message": f"Email failed with status code {response.status_code}: {response.text}",
            "mode": "power_automate"
        }

    except Exception as error:
        return {
            "success": False,
            "message": f"Email sending error: {str(error)}",
            "mode": "power_automate"
        }