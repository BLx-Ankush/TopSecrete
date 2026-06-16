"""
Alice Servo Control Tool
Sends simple servo commands to a Raspberry Pi HTTP endpoint.
"""

import os
import asyncio
import requests
from livekit.agents import function_tool

_ALLOWED_COMMANDS = {"left", "center", "right", "stop"}


def _pi_config() -> tuple[str, str, str]:
    """Read Pi configuration from environment at call-time.

    This avoids stale defaults if env vars change after import.
    """
    # SECURITY/CONFIG: no hardcoded device IP. Configure ALICE_PI_IP in the
    # environment; default to localhost so a misconfig fails safe locally
    # rather than reaching out to a stale hardcoded LAN address.
    pi_ip = os.getenv("ALICE_PI_IP", "127.0.0.1").strip()
    pi_port = os.getenv("ALICE_PI_PORT", "5000").strip()
    ultrasonic_path = os.getenv("ALICE_PI_ULTRASONIC_PATH", "/ultrasonic").strip() or "/ultrasonic"
    if not ultrasonic_path.startswith("/"):
        ultrasonic_path = "/" + ultrasonic_path
    return pi_ip, pi_port, ultrasonic_path


def _post_json(url: str, payload: dict, timeout_s: float) -> requests.Response:
    return requests.post(url, json=payload, timeout=timeout_s)


def _get(url: str, timeout_s: float) -> requests.Response:
    return requests.get(url, timeout=timeout_s)


@function_tool(
    name="control_servo_motor",
    description=(
        "Control a Raspberry Pi servo motor. "
        "Use one of: left, center, right, stop."
    ),
)
async def control_servo_motor(command: str) -> str:
    """
    Send a servo command to the Raspberry Pi controller.

    Args:
        command: One of left, center, right, stop.
    """
    cmd = command.strip().lower()
    if cmd not in _ALLOWED_COMMANDS:
        return (
            "❌ Invalid command. Use one of: "
            + ", ".join(sorted(_ALLOWED_COMMANDS))
        )

    pi_ip, pi_port, _ = _pi_config()
    url = f"http://{pi_ip}:{pi_port}/command"
    try:
        response = await asyncio.to_thread(_post_json, url, {"cmd": cmd}, 5)
        if response.ok:
            return f"✅ Servo command sent: {cmd}"
        return f"❌ Pi error {response.status_code}: {response.text}"
    except requests.RequestException as exc:
        return (
            "❌ Connection error while sending servo command. "
            f"Tried: {url}. "
            f"Details: {exc}"
        )


@function_tool(
    name="get_ultrasonic_distance",
    description=(
        "Read the ultrasonic sensor distance from the Raspberry Pi. "
        "Returns the distance in centimeters if an object is detected."
    ),
)
async def get_ultrasonic_distance() -> str:
    """
    Fetch ultrasonic sensor distance from the Raspberry Pi.

    Expects either JSON like {"distance_cm": 12.3} or a plain number.
    """
    pi_ip, pi_port, ultrasonic_path = _pi_config()
    url = f"http://{pi_ip}:{pi_port}{ultrasonic_path}"
    try:
        response = await asyncio.to_thread(_get, url, 5)
        if not response.ok:
            return f"❌ Pi error {response.status_code}: {response.text}"

        distance_cm = None
        try:
            payload = response.json()
            if isinstance(payload, dict):
                for key in ("distance_cm", "distance", "cm"):
                    if key in payload:
                        distance_cm = float(payload[key])
                        break
        except ValueError:
            # Non-JSON response; fall through to text parsing.
            pass

        if distance_cm is None:
            try:
                distance_cm = float(response.text.strip())
            except ValueError:
                return "❌ Unexpected sensor response format."

        if distance_cm < 0:
            return "❌ Invalid distance reading."
        return f"✅ Object detected at {distance_cm:.1f} cm"
    except requests.RequestException as exc:
        return (
            "❌ Connection error while reading ultrasonic sensor. "
            f"Tried: {url}. "
            f"Details: {exc}"
        )
