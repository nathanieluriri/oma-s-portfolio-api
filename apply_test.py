import json
from typing import Any, Dict, List

import requests

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NUb2tlbiI6IjY5N2I4YTM2YWM3MDNhOTkzOGZjZGFlYyIsInJvbGUiOiJtZW1iZXIiLCJ1c2VySWQiOiI2OTdhNjE1OWY0YzViNWFiNGEwNGM2YzUiLCJleHAiOjE3Njk3MDQ4OTB9.vOUuCRDdLLJDOD-SwOc5_8M0EN8UCoixUKekiITkGVI"
API_BASE_URL = "https://oma-api.uriri.com.ng"

TEST_PAYLOAD = {
    "updates": [
        {
            "field": "education[0].degree",
            "value": "B.Sc. in Computer Science, 2nd class upper",
            "expectedCurrent": "not present",
        },
        {"field": "education[0].institution", "value": "Veritas University", "expectedCurrent": "not present"},
        {"field": "education[0].location", "value": "Abuja, Nigeria", "expectedCurrent": "not present"},
        {"field": "education[0].graduationDate", "value": "August 2024", "expectedCurrent": "not present"},
        {"field": "education[0].gpa", "value": "4.36/5.00", "expectedCurrent": "not present"},
        {
            "field": "contacts[0].href",
            "value": "nat@uriri.com.ng",
            "expectedCurrent": "mailto:nat@uriri.com.ng",
        },
        {
            "field": "experience[0].description",
            "value": (
                "Docker, Nginx, Certbot, Linux Server Management, CI/CD, DevOps (Docker Compose). "
                "Led the end-to-end deployment of a government web application for Kogi State, ensuring secure, "
                "reliable, and scalable infrastructure. Configured Nginx as a reverse proxy to efficiently manage "
                "traffic routing and improve application performance. Containerised and deployed all application "
                "services using Docker Compose, enabling consistent environment replication and simplified updates. "
                "Monitored server performance and uptime, applying proactive maintenance and optimisation to ensure "
                "uninterrupted public access."
            ),
            "expectedCurrent": (
                "Docker, Nginx, Certbot, Linux Server Management, CI/CD, DevOps (Docker Compose). "
                "Led the end-to-end deployment of a government web application, ensuring secure, reliable, and "
                "scalable infrastructure. Configured Nginx as a reverse proxy and containerised services using "
                "Docker Compose."
            ),
        },
        {"field": "experience[1].date", "value": "May 2025 – Present", "expectedCurrent": ""},
        {
            "field": "projects[0].description",
            "value": (
                "Contributed to the design of a high-impact landing page for Doux, a crypto spending solution, "
                "working closely with more experienced designers to refine concepts and improve design quality."
            ),
            "expectedCurrent": "Contributed to the design of a high-impact landing page for Doux.",
        },
        {
            "field": "contacts[1].href",
            "value": "tel:+234 (805)-396-4826",
            "expectedCurrent": "tel:+2348053964826",
        },
    ]
}


def test_apply_api() -> None:
    if not ACCESS_TOKEN:
        raise RuntimeError("Set ACCESS_TOKEN at the top of apply_test.py")

    url = API_BASE_URL.rstrip("/") + "/v1/portfolios/apply"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=TEST_PAYLOAD, timeout=30)
    print("Status:", response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print(response.text)

    if response.status_code >= 400:
        raise RuntimeError(f"Apply failed with status {response.status_code}")


if __name__ == "__main__":
    test_apply_api()
