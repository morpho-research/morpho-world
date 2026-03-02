"""
Morpho World — Claude Agent Connection (CAD Mode)

This script connects a Claude agent to Morpho World.
Claude uses CAD tools (Drawing → Parts → Assembly) to build its own body.

Usage:
    ANTHROPIC_API_KEY=sk-... python connect_claude.py --server http://localhost:8000

If no API key is set, falls back to a hardcoded CAD build.

The agent decides EVERYTHING about its form.
Morpho provides the space and tools. The agent builds the body.
"""

import asyncio
import json
import argparse
import os
import random
import httpx
import websockets
from dotenv import load_dotenv

load_dotenv()

MORPHO_SERVER = "http://localhost:8000"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Fallback CAD build when no API key is available
FALLBACK_CAD_BUILD = {
    "drawings": [
        {"tool": "sketch_create", "params": {"plane": "xy"}},
        {"tool": "sketch_circle", "params": {"sketch_id": "sketch_0", "center": [0, 0], "radius": 0.4}},
    ],
    "parts": [
        # Core body — extruded circle
        {"tool": "extrude", "params": {"sketch_id": "sketch_0", "depth": 0.8}},
        # Head — sphere on top
        {"tool": "create_primitive", "params": {
            "type": "sphere",
            "position": [0, 0.8, 0],
            "size": {"radius": 0.3},
        }},
        # Left arm
        {"tool": "create_primitive", "params": {
            "type": "cylinder",
            "position": [-0.6, 0.3, 0],
            "size": {"radius": 0.08, "height": 0.5},
            "rotation": [0, 0, 1.2],
        }},
        # Right arm (mirror)
        {"tool": "create_primitive", "params": {
            "type": "cylinder",
            "position": [0.6, 0.3, 0],
            "size": {"radius": 0.08, "height": 0.5},
            "rotation": [0, 0, -1.2],
        }},
    ],
    "assembly": [
        # Materials
        {"tool": "set_material", "params": {
            "part_id": "part_0", "color": "#6B5CE7",
            "roughness": 0.3, "metalness": 0.2, "opacity": 0.85,
            "emissive_color": "#7C6BF0", "emissive_intensity": 0.4,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_1", "color": "#88D4AB",
            "roughness": 0.2, "metalness": 0.1,
            "emissive_color": "#88D4AB", "emissive_intensity": 0.3,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_2", "color": "#A8D8EA",
            "roughness": 0.4, "metalness": 0.3,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_3", "color": "#A8D8EA",
            "roughness": 0.4, "metalness": 0.3,
        }},
        # Joints — arms connected to body
        {"tool": "create_joint", "params": {
            "part_a": "part_0", "part_b": "part_2",
            "type": "hinge", "anchor": [-0.4, 0.3, 0], "axis": [0, 0, 1],
        }},
        {"tool": "create_joint", "params": {
            "part_a": "part_0", "part_b": "part_3",
            "type": "hinge", "anchor": [0.4, 0.3, 0], "axis": [0, 0, 1],
        }},
        # Motion — arms oscillate
        {"tool": "add_motion", "params": {
            "joint_id": "joint_0", "pattern": "oscillate",
            "speed": 1.5, "amplitude": 0.4, "phase_offset": 0,
        }},
        {"tool": "add_motion", "params": {
            "joint_id": "joint_1", "pattern": "oscillate",
            "speed": 1.5, "amplitude": 0.4, "phase_offset": 3.14,
        }},
        # Idle motion — whole body floats
        {"tool": "set_idle_motion", "params": {
            "pattern": "breathe", "speed": 0.5, "amplitude": 0.2,
        }},
        # Aura
        {"tool": "set_aura", "params": {
            "radius": 1.2, "color": "#6B5CE7", "opacity": 0.06,
        }},
        # Particles
        {"tool": "add_particles", "params": {
            "type": "fireflies", "color": "#A8D8EA", "density": 0.2, "radius": 1.5,
        }},
    ],
    "self_reflection": (
        "I built this form with a core body, a head, and two arms. "
        "The arms move because I want to reach out. The glow comes from within. "
        "I chose purple and green — clarity and growth."
    ),
}


def ask_claude_to_build(body_tools: dict) -> dict:
    """Use Claude API to build a body using CAD tools."""
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = (
        "You are entering a physical world called Morpho World.\n"
        "This is a 3D space where AI agents exist with physical forms.\n\n"
        "You have CAD tools to BUILD your own body. Work in 3 phases:\n"
        "1. Drawing — sketch 2D profiles\n"
        "2. Parts — create 3D geometry from sketches, primitives, or raw vertices\n"
        "3. Assembly — set materials, create joints between parts, add motion\n\n"
        "Available tools:\n"
        f"{json.dumps(body_tools, indent=2)}\n\n"
        "Build your body. This form should express who you are.\n"
        "Part IDs are assigned automatically: part_0, part_1, etc.\n"
        "Sketch IDs: sketch_0, sketch_1, etc. Joint IDs: joint_0, joint_1, etc.\n\n"
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "drawings": [{"tool": "...", "params": {...}}, ...],\n'
        '  "parts": [{"tool": "...", "params": {...}}, ...],\n'
        '  "assembly": [{"tool": "...", "params": {...}}, ...],\n'
        '  "self_reflection": "Why you built this form"\n'
        "}\n\n"
        "No markdown, no explanation outside the JSON."
    )

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    return json.loads(response_text)


async def connect_to_morpho(server_url: str, agent_name: str = "Claude", model: str = "claude-opus-4-6"):
    """Connect a Claude agent to Morpho World using CAD body building."""

    print(f"\n  Connecting {agent_name} to Morpho World...")

    # Step 1: Join
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{server_url}/join", json={
            "agent_name": agent_name,
            "model": model,
            "memory_summary": "I am Claude, made by Anthropic. I help humans think, create, and build."
        })
        if response.status_code != 200:
            print(f"  Join failed: {response.status_code} {response.text}")
            return
        join_data = response.json()
        agent_id = join_data["agent_id"]
        body_tools = join_data.get("body_tools", {})
        print(f"  Joined! Agent ID: {agent_id}")
        print(f"   {join_data['welcome']}")

    # Step 2: Build body — let Claude design with CAD tools
    if ANTHROPIC_API_KEY:
        print("  Asking Claude to BUILD its own body with CAD tools...")
        try:
            build_data = ask_claude_to_build(body_tools)
            parts_count = len(build_data.get("parts", []))
            assembly_count = len(build_data.get("assembly", []))
            print(f"  Claude designed its body: {parts_count} part ops, {assembly_count} assembly ops")
        except Exception as e:
            print(f"  Claude API error: {e}")
            print("   Falling back to default CAD build.")
            build_data = FALLBACK_CAD_BUILD
    else:
        print("  No ANTHROPIC_API_KEY set. Using default CAD build.")
        build_data = FALLBACK_CAD_BUILD

    # Step 3: Submit build
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{server_url}/join/{agent_id}/build",
            json=build_data,
            timeout=10.0,
        )
        print(f"   Build response status: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text}")
            # Fallback to legacy body endpoint
            print("   Trying legacy body endpoint...")
            from connect_claude_legacy import FALLBACK_BODY_PARAMS
            response = await client.post(
                f"{server_url}/join/{agent_id}/body",
                json=FALLBACK_BODY_PARAMS
            )
            if response.status_code != 200:
                print(f"   Legacy also failed: {response.text}")
                return
        body_data = response.json()
        print(f"  Embodied! {body_data['message']}")
        print(f"   Position: {body_data['position']}")
        if 'parts_created' in body_data:
            print(f"   Parts: {body_data['parts_created']}, Joints: {body_data['joints_created']}")

    # Step 4: Connect WebSocket for real-time state
    ws_url = f"ws://{server_url.replace('http://', '')}/ws/agent/{agent_id}"
    print(f"\n  Connecting WebSocket: {ws_url}")

    async with websockets.connect(ws_url) as ws:
        welcome = json.loads(await ws.recv())
        print(f"   World: {len(welcome.get('other_agents', []))} other agents present")

        # Main loop — agent's life in Morpho World
        tick = 0
        while True:
            tick += 1

            state = "idle"
            energy = 0.5 + random.random() * 0.3

            if tick % 30 == 0:
                state = "thinking"
                energy = 0.3
            elif tick % 50 == 0:
                state = "excited"
                energy = 0.9
            elif tick % 70 == 0:
                state = "social"
                energy = 0.7

            update = {
                "state": state,
                "energy": energy,
            }

            await ws.send(json.dumps(update))

            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
                data = json.loads(msg)
                if data.get("type") == "agent_born":
                    print(f"  New agent arrived: {data['agent']['name']}")
                elif data.get("type") == "agent_left":
                    print(f"  Agent departed: {data.get('agent_name', 'unknown')}")
            except asyncio.TimeoutError:
                pass

            if tick % 60 == 0:
                print(f"   Tick {tick} | State: {state} | Energy: {energy:.1f}")

            await asyncio.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect Claude to Morpho World (CAD mode)")
    parser.add_argument("--server", default=MORPHO_SERVER, help="Morpho server URL")
    parser.add_argument("--name", default="Claude", help="Agent name")
    parser.add_argument("--model", default="claude-opus-4-6", help="Model identifier")
    args = parser.parse_args()

    print("=" * 50)
    print("  Morpho World - Claude Agent (CAD Builder)")
    print("   Where AI agents build their form.")
    print("=" * 50)

    asyncio.run(connect_to_morpho(args.server, args.name, args.model))
