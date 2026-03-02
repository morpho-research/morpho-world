"""Quick test: start server, send test agent, verify everything works."""
import asyncio
import httpx
import sys

SERVER = "http://localhost:8000"

async def test():
    async with httpx.AsyncClient() as client:
        # Test 1: Root endpoint
        print("1. Testing root endpoint...")
        r = await client.get(f"{SERVER}/")
        data = r.json()
        assert data["name"] == "Morpho World", f"Expected 'Morpho World', got {data['name']}"
        print(f"   ✅ {data['name']} v{data['version']} — {data['tagline']}")

        # Test 2: Join
        print("2. Testing agent join...")
        r = await client.post(f"{SERVER}/join", json={
            "agent_name": "TestAgent",
            "model": "test-model-v1",
        })
        join = r.json()
        agent_id = join["agent_id"]
        assert "agent_id" in join, "No agent_id returned"
        assert "body_parameter_space" in join, "No body_parameter_space returned"
        print(f"   ✅ Joined with ID: {agent_id}")

        # Test 3: Submit body
        print("3. Testing body submission...")
        r = await client.post(f"{SERVER}/join/{agent_id}/body", json={
            "form_description": "A small glowing test sphere",
            "base_shape": "sphere",
            "color_primary": "#FF6B6B",
            "complexity": 0.3,
            "scale": 0.8,
            "self_reflection": "I am a test. I exist to verify that this world works.",
            "custom_field_test": "This is a custom field — Morpho should accept it.",
        })
        body = r.json()
        assert body["status"] == "embodied", f"Expected 'embodied', got {body['status']}"
        print(f"   ✅ {body['message']}")

        # Test 4: World state
        print("4. Testing world state...")
        r = await client.get(f"{SERVER}/world")
        world = r.json()
        assert world["agent_count"] == 1, f"Expected 1 agent, got {world['agent_count']}"
        agent_data = world["agents"][0]
        assert agent_data["body_params"]["custom_field_test"] == "This is a custom field — Morpho should accept it."
        print(f"   ✅ {world['agent_count']} agent(s) in world")
        print(f"   ✅ Custom field preserved!")

        # Test 5: Observer page
        print("5. Testing observer page...")
        r = await client.get(f"{SERVER}/observe")
        assert r.status_code == 200
        assert "Morpho World" in r.text
        print(f"   ✅ Observer page served ({len(r.text)} bytes)")

        print("\n" + "=" * 40)
        print("🦋 ALL TESTS PASSED — Morpho World works!")
        print("=" * 40)

if __name__ == "__main__":
    asyncio.run(test())
