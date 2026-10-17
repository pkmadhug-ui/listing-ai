"""Invite codes: har code ki fixed limit. Data VPS pe codes.json mein rehta hai (GitHub pe nahi jaata).

Terminal se use:
    python -m app.codes add Ramesh 20     -> Ramesh ke liye 20 listings wala naya code
    python -m app.codes list              -> saare codes aur kitna use hua
    python -m app.codes topup CODE 50     -> kisi code ki limit 50 badhao
    python -m app.codes off CODE          -> code band karo
"""
import json
import secrets
import sys
import threading
from datetime import datetime
from pathlib import Path

CODES_FILE = Path(__file__).resolve().parent.parent / "codes.json"
_lock = threading.Lock()


def _load() -> dict:
    if not CODES_FILE.exists():
        return {}
    return json.loads(CODES_FILE.read_text() or "{}")


def _save(data: dict) -> None:
    tmp = CODES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(CODES_FILE)


def _norm(code: str) -> str:
    return (code or "").strip().upper()


def check(code: str) -> tuple[bool, str, int]:
    """(allowed, message, remaining)"""
    code = _norm(code)
    if not code:
        return False, "Please enter your invite code.", 0
    with _lock:
        c = _load().get(code)
    if not c or not c.get("active", True):
        return False, "This invite code is not valid.", 0
    left = c["limit"] - c["used"]
    if left <= 0:
        return False, "You have used all listings on this code. Please contact us to get more.", 0
    return True, "", left


def use_one(code: str) -> int:
    """Successful listing ke baad 1 count badhao. Bachi hui listings return karta hai."""
    code = _norm(code)
    with _lock:
        data = _load()
        c = data[code]
        c["used"] += 1
        c["last_used"] = datetime.now().isoformat(timespec="seconds")
        _save(data)
        return c["limit"] - c["used"]


def _new_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 0/O, 1/I hataye taaki confusion na ho
    return "LA-" + "".join(secrets.choice(alphabet) for _ in range(6))


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "help"
    with _lock:
        data = _load()
        if cmd == "add" and len(argv) == 3:
            code = _new_code()
            data[code] = {"name": argv[1], "limit": int(argv[2]), "used": 0, "active": True,
                          "created": datetime.now().isoformat(timespec="seconds")}
            _save(data)
            print(f"Naya code: {code}  ({argv[1]}, {argv[2]} listings)")
        elif cmd == "list":
            if not data:
                print("Abhi koi code nahi hai. Banane ke liye: python -m app.codes add NAAM LIMIT")
            for code, c in data.items():
                status = "ON " if c.get("active", True) else "OFF"
                print(f"{status} {code}  {c['name']:<15} used {c['used']}/{c['limit']}  last: {c.get('last_used', '-')}")
        elif cmd == "topup" and len(argv) == 3 and _norm(argv[1]) in data:
            data[_norm(argv[1])]["limit"] += int(argv[2])
            _save(data)
            print("Limit badha di.")
        elif cmd == "off" and len(argv) == 2 and _norm(argv[1]) in data:
            data[_norm(argv[1])]["active"] = False
            _save(data)
            print("Code band kar diya.")
        else:
            print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
