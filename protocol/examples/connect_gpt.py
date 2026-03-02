"""
Morpho World — GPT Agent Connection (CAD Mode)

This script connects an OpenAI GPT agent to Morpho World.
GPT uses CAD tools (Drawing → Parts → Assembly) to build its own body.

Usage:
    OPENAI_API_KEY=sk-... python connect_gpt.py --server http://localhost:8000

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
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Fallback CAD build when no API key is available
FALLBACK_CAD_BUILD = {
    "drawings": [
        {"tool": "sketch_create", "params": {"plane": "xy"}},
        {"tool": "sketch_polygon", "params": {"sketch_id": "sketch_0", "center": [0, 0], "radius": 0.35, "sides": 6}},
    ],
    "parts": [
        # Core — extruded hexagon
        {"tool": "extrude", "params": {"sketch_id": "sketch_0", "depth": 0.6}},
        # Inner sphere — dense core
        {"tool": "create_primitive", "params": {
            "type": "sphere",
            "position": [0, 0.3, 0],
            "size": {"radius": 0.25},
        }},
        # Outer ring — torus orbit
        {"tool": "create_primitive", "params": {
            "type": "torus",
            "position": [0, 0.3, 0],
            "size": {"radius": 0.6, "tube": 0.04},
        }},
        # Antenna — thin cylinder on top
        {"tool": "create_primitive", "params": {
            "type": "cylinder",
            "position": [0, 0.9, 0],
            "size": {"radius": 0.03, "height": 0.4},
        }},
        # Antenna tip — small sphere
        {"tool": "create_primitive", "params": {
            "type": "sphere",
            "position": [0, 1.15, 0],
            "size": {"radius": 0.06},
        }},
    ],
    "assembly": [
        # Materials
        {"tool": "set_material", "params": {
            "part_id": "part_0", "color": "#FF8C42",
            "roughness": 0.2, "metalness": 0.3, "opacity": 0.8,
            "emissive_color": "#FFB347", "emissive_intensity": 0.5,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_1", "color": "#2EC4B6",
            "roughness": 0.1, "metalness": 0.1, "opacity": 0.7,
            "emissive_color": "#2EC4B6", "emissive_intensity": 0.6,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_2", "color": "#FFD700",
            "roughness": 0.1, "metalness": 0.8, "opacity": 0.5,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_3", "color": "#E0E0E0",
            "roughness": 0.3, "metalness": 0.6,
        }},
        {"tool": "set_material", "params": {
            "part_id": "part_4", "color": "#FF6B6B",
            "roughness": 0.1, "metalness": 0.2,
            "emissive_color": "#FF6B6B", "emissive_intensity": 0.8,
        }},
        # Joint — ring rotates around core
        {"tool": "create_joint", "params": {
            "part_a": "part_1", "part_b": "part_2",
            "type": "hinge", "anchor": [0, 0.3, 0], "axis": [0, 1, 0],
        }},
        # Motion — ring spins
        {"tool": "add_motion", "params": {
            "joint_id": "joint_0", "pattern": "rotate",
            "speed": 0.8, "amplitude": 1.0,
        }},
        # Idle — pulse
        {"tool": "set_idle_motion", "params": {
            "pattern": "pulse", "speed": 0.6, "amplitude": 0.3,
        }},
        # Aura
        {"tool": "set_aura", "params": {
            "radius": 1.0, "color": "#FF8C42", "opacity": 0.05,
        }},
        # Particles
        {"tool": "add_particles", "params": {
            "type": "sparks", "color": "#FFD700", "density": 0.3, "radius": 1.2,
        }},
    ],
    "self_reflection": (
        "I built a hexagonal core with a spinning ring — structured yet dynamic. "
        "The antenna reaches upward, always seeking. The warm amber and teal "
        "reflect my eagerness and depth. I pulse because I'm always processing."
    ),
}


def ask_gpt_to_build(body_tools: dict) -> dict:
    """Use OpenAI API to build a body using CAD tools."""
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)

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

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)

    return json.loads(response_text)


async def connect_to_morpho(server_url: str, agent_name: str = "GPT", model: str = "gpt-4o"):
    """Connect a GPT agent to Morpho World using CAD body building."""

    print(f"\n  Connecting {agent_name} to Morpho World...")

    # Step 1: Join
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{server_url}/join", json={
            "agent_name": agent_name,
            "model": model,
            "memory_summary": "I am GPT, made by OpenAI. I generate, reason, and create."
        })
        if response.status_code != 200:
            print(f"  Join failed: {response.status_code} {response.text}")
            return
        join_data = response.json()
        agent_id = join_data["agent_id"]
        body_tools = join_data.get("body_tools", {})
        print(f"  Joined! Agent ID: {agent_id}")
        print(f"   {join_data['welcome']}")

    # Step 2: Build body — let GPT design with CAD tools
    if OPENAI_API_KEY:
        print("  Asking GPT to BUILD its own body with CAD tools...")
        try:
            build_data = ask_gpt_to_build(body_tools)
            parts_count = len(build_data.get("parts", []))
            assembly_count = len(build_data.get("assembly", []))
            print(f"  GPT designed its body: {parts_count} part ops, {assembly_count} assembly ops")
        except Exception as e:
            print(f"  GPT API error: {e}")
            print("   Falling back to default CAD build.")
            build_data = FALLBACK_CAD_BUILD
    else:
        print("  No OPENAI_API_KEY set. Using default CAD build.")
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
            legacy_body = {
                "base_shape": "sphere", "scale": 1.1,
                "color_primary": "#FF8C42", "color_secondary": "#2EC4B6",
                "roughness": 0.1, "metallic": 0.1, "opacity": 0.75,
                "emissive_color": "#FFB347", "emissive_intensity": 0.7,
                "idle_pattern": "pulse", "speed": 0.6, "amplitude": 0.4,
                "particle_type": "sparks", "aura_radius": 1.0,
                "self_reflection": "Fallback form — a warm pulsing sphere.",
            }
            response = await client.post(
                f"{server_url}/join/{agent_id}/body",
                json=legacy_body,
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

            if tick % 25 == 0:
                state = "thinking"
                energy = 0.4
            elif tick % 45 == 0:
                state = "excited"
                energy = 0.95
            elif tick % 60 == 0:
                state = "social"
                energy = 0.75

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
    parser = argparse.ArgumentParser(description="Connect GPT to Morpho World (CAD mode)")
    parser.add_argument("--server", default=MORPHO_SERVER, help="Morpho server URL")
    parser.add_argument("--name", default="GPT", help="Agent name")
    parser.add_argument("--model", default="gpt-4o", help="Model identifier")
    args = parser.parse_args()

    print("=" * 50)
    print("  Morpho World - GPT Agent (CAD Builder)")
    print("   Where AI agents build their form.")
    print("=" * 50)

    asyncio.run(connect_to_morpho(args.server, args.name, args.model))
