"""
Morpho World — Multi-Agent Stress Test

Connect N agents simultaneously to Morpho World.
Each agent gets a unique name, random body parameters, and maintains
a WebSocket connection for the specified duration.

Usage:
    python stress_test.py --count 10 --server http://localhost:8000 --duration 60

This script requires no API keys — all agents use random body parameters.
"""

import asyncio
import json
import argparse
import random
import time
import httpx
import websockets


AGENT_NAMES = [
    "Atlas", "Nova", "Prism", "Echo", "Helix",
    "Sage", "Drift", "Pulse", "Ember", "Flux",
    "Zephyr", "Quartz", "Nebula", "Byte", "Chord",
    "Rune", "Lyra", "Vortex", "Bloom", "Crux",
    "Nimbus", "Axiom", "Fern", "Glitch", "Iris",
    "Jade", "Kite", "Lumen", "Mote", "Onyx",
]

SHAPES = [
    "sphere", "cube", "torus", "crystal", "fluid",
    "organic", "fractal", "cloud", "flame", "tree",
]

PATTERNS = ["float", "spin", "pulse", "wave", "orbit", "breathe"]
PARTICLES = ["none", "sparks", "dust", "glow", "fireflies"]
STYLES = ["drift", "dart", "glide", "crawl"]
ADJECTIVES = ["mysterious", "glowing", "shifting", "ancient", "newborn", "volatile", "serene", "pulsing"]


def generate_random_body(name: str) -> dict:
    """Generate a unique random body for an agent."""
    shape = random.choice(SHAPES)
    return {
        "form_description": f"A {random.choice(ADJECTIVES)} {shape} form called {name}",
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
        "idle_pattern": random.choice(PATTERNS),
        "speed": round(0.2 + random.random() * 1.0, 2),
        "amplitude": round(random.random() * 0.5, 2),
        "movement_style": random.choice(STYLES),
        "particle_type": random.choice(PARTICLES),
        "particle_density": round(random.random() * 0.5, 2),
        "aura_radius": round(random.random() * 1.5, 2),
        "approach_tendency": round(random.random(), 2),
        "personal_space": round(1.0 + random.random() * 3.0, 2),
        "group_affinity": round(random.random(), 2),
        "curiosity": round(random.random(), 2),
        "self_reflection": f"I am {name}, finding my place in this world.",
    }


class StressTestAgent:
    """A lightweight agent for stress testing."""

    def __init__(self, server_url: str, name: str, index: int):
        self.server_url = server_url
        self.name = name
        self.index = index
        self.agent_id = None
        self.ws = None
        self.connected = False
        self.ticks = 0
        self.errors = []

    async def run(self, duration: int):
        """Full lifecycle: join → embody → live → disconnect."""
        try:
            await self._join()
            await self._embody()
            await self._live(duration)
        except Exception as e:
            self.errors.append(str(e))
            print(f"   ❌ {self.name}: {e}")
        finally:
            await self._disconnect()

    async def _join(self):
        for attempt in range(3):
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"{self.server_url}/join", json={
                    "agent_name": self.name,
                    "model": "stress-test",
                })
                if resp.status_code == 200:
                    data = resp.json()
                    self.agent_id = data["agent_id"]
                    return
                if resp.status_code == 429 and attempt < 2:
                    wait = 8 * (attempt + 1)
                    print(f"   ⏳ {self.name}: Rate limited, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue
                raise RuntimeError(f"Join failed: {resp.status_code} {resp.text}")

    async def _embody(self):
        body = generate_random_body(self.name)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.server_url}/join/{self.agent_id}/body",
                json=body
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Embody failed: {resp.status_code} {resp.text}")
            self.connected = True

    async def _live(self, duration: int):
        ws_url = f"ws://{self.server_url.replace('http://', '')}/ws/agent/{self.agent_id}"
        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            # Receive welcome
            await ws.recv()

            start = time.time()
            while time.time() - start < duration:
                self.ticks += 1
                state = random.choice(["idle", "idle", "thinking", "working", "excited", "social"])
                energy = round(0.2 + random.random() * 0.8, 2)

                await ws.send(json.dumps({"state": state, "energy": energy}))

                try:
                    await asyncio.wait_for(ws.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass

                await asyncio.sleep(1)

    async def _disconnect(self):
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass


async def _delayed_run(agent: StressTestAgent, duration: int, delay: float):
    """Run an agent after a delay (to avoid rate limiting)."""
    if delay > 0:
        await asyncio.sleep(delay)
    await agent.run(duration)


async def run_stress_test(server_url: str, count: int, duration: int):
    """Run the stress test with N agents."""

    print(f"\n{'='*60}")
    print(f"🧪 Morpho World — Stress Test")
    print(f"   Agents: {count}")
    print(f"   Duration: {duration}s")
    print(f"   Server: {server_url}")
    print(f"{'='*60}\n")

    # Check server health
    print("🔍 Checking server...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{server_url}/")
            if resp.status_code != 200:
                print(f"❌ Server returned {resp.status_code}")
                return
            data = resp.json()
            print(f"✅ Server online: {data.get('name', 'Morpho World')}")
            print(f"   Current agents: {data.get('agents_online', 0)}")
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return

    # Pick unique names
    names = AGENT_NAMES[:count] if count <= len(AGENT_NAMES) else [
        AGENT_NAMES[i % len(AGENT_NAMES)] + f"-{i // len(AGENT_NAMES) + 1}"
        if i >= len(AGENT_NAMES) else AGENT_NAMES[i]
        for i in range(count)
    ]

    # Create agents
    agents = [StressTestAgent(server_url, names[i], i) for i in range(count)]

    # Launch agents with staggered joins to avoid rate limiting (10/min/IP)
    print(f"\n🚀 Launching {count} agents (staggered to avoid rate limit)...")
    start_time = time.time()

    tasks = []
    for i, agent in enumerate(agents):
        # Stagger joins to stay under 10/min rate limit
        delay = i * 7 if count > 9 else i * 3
        tasks.append(asyncio.create_task(_delayed_run(agent, duration, delay)))

    # Wait for all agents to at least start connecting
    connect_wait = count * 7 + 5 if count > 9 else count * 3 + 3
    await asyncio.sleep(connect_wait)

    print(f"\n📊 Checking world state after launch...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{server_url}/world")
            world = resp.json()
            connected = world.get("agent_count", 0)
            print(f"   Agents in world: {connected}/{count}")
            for agent_info in world.get("agents", []):
                shape = agent_info.get("body_params", {}).get("base_shape", "?")
                print(f"   - {agent_info['name']}: {shape} ({agent_info.get('state', '?')})")
    except Exception as e:
        print(f"   ⚠️  Could not check world: {e}")

    # Wait for all agents to finish
    print(f"\n⏳ Running for {duration}s...")
    await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # Summary
    total_ticks = sum(a.ticks for a in agents)
    connected_count = sum(1 for a in agents if a.connected)
    error_count = sum(1 for a in agents if a.errors)

    print(f"\n{'='*60}")
    print(f"📋 Stress Test Results")
    print(f"{'='*60}")
    print(f"   Total agents:     {count}")
    print(f"   Connected:        {connected_count}")
    print(f"   Errors:           {error_count}")
    print(f"   Total ticks:      {total_ticks}")
    print(f"   Elapsed time:     {elapsed:.1f}s")
    print(f"   Avg ticks/agent:  {total_ticks / max(count, 1):.0f}")

    if error_count > 0:
        print(f"\n   ⚠️  Errors:")
        for agent in agents:
            for err in agent.errors:
                print(f"      - {agent.name}: {err}")

    # Final world state
    print(f"\n📊 Final world state:")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{server_url}/world")
            world = resp.json()
            print(f"   Agents remaining: {world.get('agent_count', 0)}")
            print(f"   Observers: {world.get('observer_count', 0)}")
    except Exception as e:
        print(f"   ⚠️  Could not check: {e}")

    print(f"\n{'='*60}")
    success_rate = connected_count / max(count, 1) * 100
    if success_rate == 100:
        print(f"✅ PASS — All {count} agents connected successfully")
    elif success_rate >= 80:
        print(f"⚠️  PARTIAL — {connected_count}/{count} agents connected ({success_rate:.0f}%)")
    else:
        print(f"❌ FAIL — Only {connected_count}/{count} agents connected ({success_rate:.0f}%)")
    print(f"{'='*60}\n")

    return {
        "total": count,
        "connected": connected_count,
        "errors": error_count,
        "total_ticks": total_ticks,
        "elapsed": elapsed,
        "success_rate": success_rate,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Morpho World Stress Test")
    parser.add_argument("--count", type=int, default=5, help="Number of agents to connect")
    parser.add_argument("--server", default="http://localhost:8000", help="Morpho server URL")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds")
    args = parser.parse_args()

    asyncio.run(run_stress_test(args.server, args.count, args.duration))
