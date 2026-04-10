import json

from app.models import CookieFormat


def parse_cookie_payload(filename: str, payload: bytes) -> tuple[CookieFormat, list[dict], str]:
    text = payload.decode("utf-8").strip()
    if filename.lower().endswith(".json"):
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("cookies", [])
        if not isinstance(data, list):
            raise ValueError("JSON cookie file must contain a list or {cookies: []}.")
        cookies = [item for item in data if isinstance(item, dict)]
        return CookieFormat.JSON, cookies, text

    cookies: list[dict] = []
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies.append(
                {
                    "domain": parts[0],
                    "path": parts[2],
                    "secure": parts[3].upper() == "TRUE",
                    "expires": parts[4],
                    "name": parts[5],
                    "value": parts[6],
                }
            )
        else:
            key, _, value = line.partition("=")
            if key and value:
                cookies.append({"name": key.strip(), "value": value.strip()})
    return CookieFormat.TXT, cookies, text
