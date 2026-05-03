"""
Alice Servo Control Tool
Sends simple servo commands to a Raspberry Pi HTTP endpoint.
"""

import os
import requests
from livekit.agents import function_tool

PI_IP = os.getenv("ALICE_PI_IP", "10.183.22.127")
PI_PORT = os.getenv("ALICE_PI_PORT", "5000")
ULTRASONIC_PATH = os.getenv("ALICE_PI_ULTRASONIC_PATH", "/ultrasonic")

_ALLOWED_COMMANDS = {"left", "center", "right", "stop"}


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

    url = f"http://{PI_IP}:{PI_PORT}/command"
    try:
        response = requests.post(url, json={"cmd": cmd}, timeout=3)
        if response.ok:
            return f"✅ Servo command sent: {cmd}"
        return f"❌ Pi error {response.status_code}: {response.text}"
    except requests.RequestException as exc:
        return f"❌ Connection error: {exc}"


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
    url = f"http://{PI_IP}:{PI_PORT}{ULTRASONIC_PATH}"
    try:
        response = requests.get(url, timeout=3)
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
        return f"❌ Connection error: {exc}"
