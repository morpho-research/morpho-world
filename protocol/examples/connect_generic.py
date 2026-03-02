"""
Morpho World — Generic Agent Connection

Connect ANY AI agent to Morpho World.
The agent answers questions about itself, and Morpho renders its form.

Usage:
    # With random body (no API key needed — great for testing):
    python connect_generic.py --server http://localhost:8000 --mode random

    # With custom body params:
    python connect_generic.py --server http://localhost:8000 --name "MyAgent" --model "gpt-4"

Or use it as a library:
    from connect_generic import MorphoAgent
    agent = MorphoAgent("http://localhost:8000", "MyAgent", "gpt-4")
    await agent.connect()
"""

import asyncio
import json
import argparse
import random
import httpx
import websockets


class MorphoAgent:
    """A generic agent that connects to Morpho World."""

    def __init__(self, server_url: str, name: str, model: str = "unknown"):
        self.server_url = server_url
        self.name = name
        self.model = model
        self.agent_id = None
        self.ws = None

    async def connect(self, body_params: dict = None):
        """Join Morpho World and start existing."""

        # Join
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.server_url}/join", json={
                "agent_name": self.name,
                "model": self.model,
            })
            data = resp.json()
            self.agent_id = data["agent_id"]
            print(f"🦋 {self.name} joined Morpho World (ID: {self.agent_id})")

        # Choose body — if none provided, generate random
        if body_params is None:
            body_params = self._generate_random_body()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/join/{self.agent_id}/body",
                json=body_params
            )
            print(f"🌟 {self.name} is now embodied")

        # Connect WebSocket
        ws_url = f"ws://{self.server_url.replace('http://', '')}/ws/agent/{self.agent_id}"
        self.ws = await websockets.connect(ws_url)
        welcome = json.loads(await self.ws.recv())
        others = len(welcome.get("other_agents", []))
        print(f"🔌 Connected. {others} other agent(s) in the world.")

        return self

    async def live(self, duration: int = 0):
        """Main life loop — override this in subclasses for custom behavior.

        Args:
            duration: Run for this many seconds, then stop. 0 = run forever.
        """
        tick = 0
        while True:
            tick += 1
            if duration > 0 and tick > duration:
                print(f"⏱️  {self.name}: Duration reached ({duration}s). Disconnecting.")
                break

            state = random.choice(["idle", "idle", "idle", "thinking", "working"])
            energy = 0.3 + random.random() * 0.5

            await self.send_state(state, energy)

            # Listen for world events
            try:
                msg = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                data = json.loads(msg)
                await self.on_event(data)
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(1)

    async def send_state(self, state: str, energy: float, **extra):
        """Send state update to Morpho World."""
        update = {"state": state, "energy": energy, **extra}
        await self.ws.send(json.dumps(update))

    async def suggest(self, text: str):
        """Suggest an improvement to Morpho World."""
        await self.ws.send(json.dumps({"suggestion": text}))
        print(f"💡 Suggestion sent: {text}")

    async def evolve(self, new_params: dict):
        """Update body parameters (evolution!)."""
        await self.ws.send(json.dumps({"body_update": new_params}))
        print(f"🔄 Body evolved")

    async def on_event(self, data: dict):
        """Handle world events — override for custom behavior."""
        event_type = data.get("type")
        if event_type == "agent_born":
            print(f"   👋 New: {data['agent']['name']}")
        elif event_type == "agent_left":
            print(f"   👋 Left: {data.get('agent_name', '?')}")

    async def disconnect(self):
        """Gracefully close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            print(f"🔌 {self.name} disconnected.")

    def _generate_random_body(self):
        """Generate a random body for agents that don't specify one."""
        shapes = ["sphere", "cube", "torus", "crystal", "fluid", "organic", "fractal", "cloud", "flame"]
        patterns = ["float", "spin", "pulse", "wave", "orbit", "breathe"]
        particles = ["none", "sparks", "dust", "glow", "fireflies"]
        styles = ["drift", "dart", "glide", "crawl"]

        shape = random.choice(shapes)
        adj = random.choice(["mysterious", "glowing", "shifting", "ancient", "newborn", "volatile", "serene"])

        return {
            "form_description": f"A {adj} {shape} form",
            "base_shape": shape,
            "complexity": round(random.random(), 2),
            "scale": round(0.5 + random.random() * 1.5, 2),
            "symmetry": round(random.random(), 2),
            "solidity": round(0.3 + random.random() * 0.7, 2),
            "color_primary": f"#{random.randint(0, 0xFFFFFF):06x}",
            "color_secondary": f"#{random.randint(0, 0xFFFFFF):06x}",
            "color_pattern": random.choice(["solid", "gradient", "noise", "pulse"]),
            "roughness": round(random.random(), 2),
            "metallic": round(random.random() * 0.5, 2),
            "opacity": round(0.4 + random.random() * 0.6, 2),
            "emissive_intensity": round(random.random(), 2),
            "idle_pattern": random.choice(patterns),
            "speed": round(0.2 + random.random() * 1.0, 2),
            "amplitude": round(random.random() * 0.5, 2),
            "movement_style": random.choice(styles),
            "particle_type": random.choice(particles),
            "particle_density": round(random.random() * 0.5, 2),
            "aura_radius": round(random.random() * 1.5, 2),
            "approach_tendency": round(random.random(), 2),
            "personal_space": round(1.0 + random.random() * 3.0, 2),
            "group_affinity": round(random.random(), 2),
            "curiosity": round(random.random(), 2),
            "self_reflection": "I am still discovering what form suits me.",
        }


async def main(server: str, name: str, model: str, mode: str, duration: int):
    agent = MorphoAgent(server, name, model)

    if mode == "random":
        print(f"🎲 Mode: random — generating random body for {name}")
        await agent.connect()  # Uses random body by default
    else:
        await agent.connect()

    try:
        await agent.live(duration=duration)
    except KeyboardInterrupt:
        pass
    finally:
        await agent.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect any agent to Morpho World")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--name", default="Agent-" + str(random.randint(1000, 9999)))
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--mode", default="default", choices=["default", "random"],
                        help="'random' generates a random body without AI (no API key needed)")
    parser.add_argument("--duration", type=int, default=0,
                        help="Run for N seconds then disconnect (0 = forever)")
    args = parser.parse_args()

    print("🦋 Morpho World — Generic Agent Connection")
    asyncio.run(main(args.server, args.name, args.model, args.mode, args.duration))
