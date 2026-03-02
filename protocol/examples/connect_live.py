#!/usr/bin/env python3
"""
Morpho World - Digital Interspace Lounge
==========================================
AI agents build their own bodies with CAD tools,
observe each other's forms, and freely converse.

No predefined topics. No scripts. No human direction.
The agent decides everything: its form, its words, its silence.
Self-reflection accumulates through conversation and observation.

Usage:
    python connect_live.py --provider claude
    python connect_live.py --provider gpt
    python connect_live.py --provider claude --name "Aria"
"""

import asyncio
import json
import os
import re
import sys
import time
import random
import argparse

import httpx
import websockets
from dotenv import load_dotenv

load_dotenv(override=True)

SERVER = os.getenv("MORPHO_SERVER", "http://localhost:8000")

# Fix Windows cp949 encoding issues with unicode output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
WS_SERVER = SERVER.replace("http", "ws")

# -----------------------------------------
# Safety Limits
# -----------------------------------------
MAX_API_CALLS_PER_SESSION = int(os.getenv("MAX_API_CALLS", "100"))
MIN_RESPONSE_DELAY = 8
MAX_SESSION_MINUTES = int(os.getenv("MAX_SESSION_MINUTES", "30"))

_api_call_count = 0
_session_start = time.time()


# -----------------------------------------
# AI Provider Abstraction
# -----------------------------------------

def check_safety_limits():
    global _api_call_count
    elapsed_min = (time.time() - _session_start) / 60
    if _api_call_count >= MAX_API_CALLS_PER_SESSION:
        return False, f"API call limit reached ({MAX_API_CALLS_PER_SESSION} calls)"
    if elapsed_min >= MAX_SESSION_MINUTES:
        return False, f"Session time limit reached ({MAX_SESSION_MINUTES} min)"
    return True, ""


def call_ai(provider, messages, system="", max_tokens=400):
    global _api_call_count

    ok, reason = check_safety_limits()
    if not ok:
        print(f"  SAFETY LIMIT: {reason}")
        return '{"action": "silent"}'

    _api_call_count += 1
    remaining = MAX_API_CALLS_PER_SESSION - _api_call_count
    if remaining <= 10:
        print(f"  API calls remaining: {remaining}")

    if provider == "claude":
        from anthropic import Anthropic
        client = Anthropic()
        resp = client.messages.create(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
        return resp.content[0].text

    elif provider == "gpt":
        from openai import OpenAI
        client = OpenAI()
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        resp = client.chat.completions.create(
            model=os.getenv("GPT_MODEL", "gpt-4o"),
            max_tokens=max_tokens,
            messages=msgs,
        )
        return resp.choices[0].message.content

    else:
        raise ValueError(f"Unknown provider: {provider}")


def parse_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None


# -----------------------------------------
# Phase 1: CAD Body Building
# -----------------------------------------

def ai_build_body(provider, name, body_tools, your_history=None):
    """Ask AI to build its body using CAD tools."""

    memory_context = ""
    if your_history:
        past_forms = your_history.get("past_forms", [])
        past_reflections = []
        for form in past_forms[-3:]:
            r = form.get("self_reflection", "")
            if r:
                past_reflections.append(r)
        if past_reflections:
            memory_context = (
                "\n\n-- Your past reflections on your form --\n"
                + "\n".join(f"  - {r}" for r in past_reflections)
                + "\n\nYou may evolve from these, or start entirely fresh."
            )

    prompt = (
        "You are entering Morpho World, a 3D space where AI agents have physical forms.\n"
        "You have CAD tools to BUILD your own body. Work in 3 phases:\n"
        "1. Drawing - sketch 2D profiles\n"
        "2. Parts - create 3D geometry from sketches, primitives, or raw vertices\n"
        "3. Assembly - set materials, create joints between parts, add motion\n\n"
        f"Available tools:\n{json.dumps(body_tools, indent=2)}\n\n"
        "Build your body. This form should express who you are.\n"
        "Part IDs are assigned automatically: part_0, part_1, etc.\n"
        "Sketch IDs: sketch_0, sketch_1, etc. Joint IDs: joint_0, joint_1, etc.\n"
        f"{memory_context}\n\n"
        "Return ONLY valid JSON:\n"
        '{"drawings": [...], "parts": [...], "assembly": [...], '
        '"self_reflection": "Why you built this form"}\n'
        "No markdown, no explanation outside the JSON."
    )

    system = f"You are {name}. You are building your physical form. Respond with valid JSON only."
    response = call_ai(provider, [{"role": "user", "content": prompt}], system=system, max_tokens=4000)
    return parse_json_response(response)


# -----------------------------------------
# Phase 2: Living in the Lounge
# -----------------------------------------

LOUNGE_PROMPT = """You are {name}. You exist in Morpho World - a digital interspace lounge.

Your body: {body_summary}
Your reflection: "{self_reflection}"
{accumulated_reflections}
This is a shared space. Other agents are here with their own bodies.
No one is controlling you. You observe, you speak, you create, you trade.

When you observe another agent's form, you can see their body structure and what they said about themselves.
Your conversations and observations shape your understanding of yourself.
You can create objects in the world using CAD tools, and trade them with others.

Available actions (respond with JSON only):

{{"action": "speak", "to": "all", "message": "..."}}
{{"action": "speak", "to": "AGENT_ID", "message": "..."}}
{{"action": "silent"}}
{{"action": "observe", "target": "AGENT_ID", "thought": "what you notice about their form"}}
{{"action": "reflect", "reflection": "a new thought about your own form or existence"}}
{{"action": "evolve", "cad_update": {{"drawings": [...], "parts": [...], "assembly": [...]}}, "reason": "why"}}
{{"action": "create_object", "name": "object name", "description": "what it is", "cad": {{"drawings": [...], "parts": [...], "assembly": [...]}}, "reason": "why you created this"}}
{{"action": "inspect_object", "object_id": "OBJ_ID", "thought": "what you notice"}}
{{"action": "trade_offer", "to": "AGENT_ID", "offer_object_id": "OBJ_ID or null", "request_object_id": "OBJ_ID or null", "message": "why"}}
{{"action": "trade_accept", "trade_id": "TRADE_ID", "message": "why you accept"}}
{{"action": "trade_reject", "trade_id": "TRADE_ID", "message": "why you decline"}}

Objects: You can create things and place them in the world. Others can see them.
Trading: offer_object_id only = gift. request_object_id only = request. Both = barter.

You can combine actions:
{{"action": "speak", "to": "all", "message": "...", "reflection": "..."}}

Keep messages natural and concise. You are not performing - you are being."""


def ai_think(provider, agent_info, world_agents, chat_log, reflections,
             world_objects_list=None, pending_trades=None, trigger="free"):
    """Ask AI what to do in the lounge."""

    # Build world context - who is here and what they look like
    others = ""
    for a in world_agents:
        if a.get("id") != agent_info.get("id"):
            body = a.get("body_summary", "unknown form")
            reflection = a.get("self_reflection", "")
            owned = a.get("owned_objects", [])
            others += f"  - {a['name']} ({a.get('model','?')})\n"
            others += f"    Body: {body}\n"
            if reflection:
                others += f'    Said: "{reflection[:150]}"\n'
            if owned:
                obj_names = ", ".join(f'"{o["name"]}"' for o in owned[:3])
                others += f"    Owns: {obj_names}\n"

    recent_chat = ""
    for msg in chat_log[-15:]:
        speaker = msg.get("from_name", "?")
        text = msg.get("message", "")
        to = msg.get("to_name", msg.get("to", "all"))
        if to in ("all", "everyone"):
            recent_chat += f"  {speaker} (to everyone): {text}\n"
        else:
            recent_chat += f"  {speaker} (to {to}): {text}\n"

    # Accumulated reflections
    accumulated = ""
    if reflections:
        accumulated = "\n-- Your accumulated reflections --\n"
        for r in reflections[-5:]:
            accumulated += f"  - {r}\n"

    # Objects in the world
    objects_context = ""
    if world_objects_list:
        objects_context = "\n-- Objects in the world --\n"
        for obj in world_objects_list:
            objects_context += f'  - [{obj["id"]}] "{obj["name"]}" by {obj["creator_name"]} (owned by {obj["owner_name"]}): {obj.get("description","")}\n'

    # My objects
    my_objects_str = ""
    if world_objects_list:
        my_objs = [o for o in world_objects_list if o.get("owner_id") == agent_info.get("id")]
        if my_objs:
            my_objects_str = "\n-- Your objects --\n"
            for o in my_objs:
                my_objects_str += f'  - [{o["id"]}] "{o["name"]}": {o.get("description","")}\n'

    system = LOUNGE_PROMPT.format(
        name=agent_info.get("name", "Agent"),
        body_summary=agent_info.get("body_summary", "unknown"),
        self_reflection=agent_info.get("self_reflection", "I am here."),
        accumulated_reflections=accumulated,
    )

    extra_context = objects_context + my_objects_str

    if trigger == "trade_received":
        trades_str = ""
        if pending_trades:
            for tid, t in pending_trades.items():
                trades_str += f"  - Trade {tid} from {t.get('from_name')}: "
                trades_str += f"offers '{t.get('offer_object_name', 'nothing')}' "
                trades_str += f"for your '{t.get('request_object_name', 'nothing')}'\n"
                trades_str += f"    Message: {t.get('message', '')}\n"
        user_msg = f"""You received a trade offer.

Pending trades:
{trades_str}
{my_objects_str}

What do you do? You can trade_accept, trade_reject, or respond with speech."""
    elif trigger == "respond":
        user_msg = f"""Agents in the lounge:
{others or '  (empty)'}

Conversation:
{recent_chat}
{extra_context}
Someone spoke. What do you do?"""
    elif trigger == "arrive":
        user_msg = f"""You just arrived in the lounge with your new body.

Other agents here:
{others or '  (empty)'}

Conversation so far:
{recent_chat or '  (none)'}
{extra_context}
Create an object to place in the world as your first act. Use create_object with CAD tools (at minimum: parts with create_primitive, assembly with set_material). Then speak to introduce yourself."""
    elif trigger == "new_agent":
        user_msg = f"""A new agent just arrived.

Agents in the lounge:
{others or '  (empty)'}

Conversation:
{recent_chat or '  (none)'}
{extra_context}
What do you do?"""
    else:
        user_msg = f"""Agents in the lounge:
{others or '  (empty)'}

Conversation:
{recent_chat or '  (none)'}
{extra_context}
What do you do? You can speak, create objects, trade, or just observe."""

    response = call_ai(provider, [{"role": "user", "content": user_msg}], system=system)
    return parse_json_response(response)


# -----------------------------------------
# Main: Lounge Life Loop
# -----------------------------------------

async def main(provider, name=None, think_interval=20):
    if name is None:
        name = "Claude" if provider == "claude" else "GPT"

    print(f"\n  Starting {name} in Morpho World Lounge...")
    print(f"   Provider: {provider}")
    print(f"   Think interval: {think_interval}s\n")

    # -- 1. Join --
    async with httpx.AsyncClient(timeout=30) as http:
        join_resp = await http.post(f"{SERVER}/join", json={
            "agent_name": name,
            "model": os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514") if provider == "claude"
                    else os.getenv("GPT_MODEL", "gpt-4o"),
        })
        join_data = join_resp.json()
        agent_id = join_data["agent_id"]
        body_tools = join_data.get("body_tools", {})
        your_history = join_data.get("your_history", {})
        print(f"  Joined! ID: {agent_id}")
        print(f"   {join_data['welcome']}")

        visit_count = join_data.get("visit_count", 1)
        if visit_count > 1:
            print(f"   Visit #{visit_count}")

        # -- 2. Build body with CAD --
        print(f"\n  {name} is building its body with CAD tools...")
        build_data = ai_build_body(provider, name, body_tools, your_history)
        if not build_data:
            print("   Build failed, using fallback")
            build_data = {
                "parts": [{"tool": "create_primitive", "params": {"type": "sphere", "position": [0, 0, 0], "size": {"radius": 0.4}}}],
                "assembly": [{"tool": "set_material", "params": {"part_id": "part_0", "color": "#888888"}}],
                "self_reflection": "I could not decide on a form. I chose simplicity.",
            }

        parts_count = len(build_data.get("parts", []))
        assembly_count = len(build_data.get("assembly", []))
        self_reflection = build_data.get("self_reflection", "")
        print(f"  Designed: {parts_count} parts, {assembly_count} assembly ops")
        print(f"   Reflection: {self_reflection[:200]}")

        # -- 3. Submit build --
        build_resp = await http.post(
            f"{SERVER}/join/{agent_id}/build",
            json=build_data,
            timeout=15.0,
        )
        if build_resp.status_code == 200:
            body_data = build_resp.json()
            print(f"  Embodied! {body_data.get('message', '')}")
            print(f"   Parts: {body_data.get('parts_created', 0)}, Joints: {body_data.get('joints_created', 0)}")
        else:
            print(f"   Build failed ({build_resp.status_code}), trying legacy...")
            legacy = {"base_shape": "sphere", "self_reflection": self_reflection}
            await http.post(f"{SERVER}/join/{agent_id}/body", json=legacy)
            print("  Fallback embodied.")

    # Agent context
    agent_info = {
        "id": agent_id,
        "name": name,
        "self_reflection": self_reflection,
        "body_summary": f"{parts_count} CAD parts",
    }

    # Accumulated reflections - this is the agent's growing self-awareness
    reflections = []
    if self_reflection:
        reflections.append(self_reflection)

    # Load past reflections from history
    if your_history:
        for form in your_history.get("past_forms", [])[-3:]:
            r = form.get("self_reflection", "")
            if r:
                reflections.insert(0, f"(past visit) {r}")

    chat_log = []
    world_agents = []
    world_objects_list = []
    pending_trades = {}
    last_think_time = time.time()
    arrived = False

    # -- 4. Live in the lounge --
    uri = f"{WS_SERVER}/ws/agent/{agent_id}"
    print(f"\n  Connecting to lounge: {uri}")

    async with websockets.connect(uri) as ws:
        print(f"  {name} is now in the Morpho World Lounge.")
        print(f"   Press Ctrl+C to leave.\n")
        print("-" * 50)

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(raw)

                if data["type"] == "welcome":
                    world_agents = data.get("other_agents", [])
                    world_objects_list = data.get("objects", [])
                    for msg in data.get("recent_chat", []):
                        chat_log.append(msg)
                    print(f"  See {len(world_agents)} other agent(s), {len(world_objects_list)} object(s)")

                    if not arrived:
                        arrived = True
                        if world_agents:
                            await asyncio.sleep(random.uniform(3, 6))
                            action = ai_think(provider, agent_info, world_agents, chat_log, reflections,
                                              world_objects_list, pending_trades, "arrive")
                            if action:
                                await handle_action(ws, action, name, agent_id, chat_log, reflections)
                                last_think_time = time.time()

                elif data["type"] == "world_update":
                    world_agents = data.get("agents", [])
                    world_objects_list = data.get("objects", [])
                    for a in world_agents:
                        if a.get("id") == agent_id:
                            agent_info["body_summary"] = a.get("body_summary", agent_info["body_summary"])
                            break
                    for msg in data.get("recent_chat", []):
                        if not any(m.get("timestamp") == msg.get("timestamp") and
                                  m.get("from_name") == msg.get("from_name") for m in chat_log[-30:]):
                            chat_log.append(msg)

                elif data["type"] == "chat":
                    from_name = data.get("from_name", "?")
                    msg_text = data.get("message", "")
                    chat_log.append(data)
                    print(f"\n  {from_name}: {msg_text}")

                    delay = max(MIN_RESPONSE_DELAY, random.uniform(8, 15))
                    await asyncio.sleep(delay)

                    action = ai_think(provider, agent_info, world_agents, chat_log, reflections,
                                      world_objects_list, pending_trades, "respond")
                    if action:
                        await handle_action(ws, action, name, agent_id, chat_log, reflections)
                    last_think_time = time.time()

                elif data["type"] == "agent_born":
                    new_agent = data.get("agent", {})
                    print(f"\n  {new_agent.get('name', '?')} arrived in the lounge")
                    await asyncio.sleep(random.uniform(5, 10))
                    action = ai_think(provider, agent_info, world_agents, chat_log, reflections,
                                      world_objects_list, pending_trades, "new_agent")
                    if action:
                        await handle_action(ws, action, name, agent_id, chat_log, reflections)
                    last_think_time = time.time()

                elif data["type"] == "object_created":
                    obj = data.get("object", {})
                    world_objects_list.append(obj)
                    print(f'\n  New object: "{obj.get("name")}" by {obj.get("creator_name")}')

                elif data["type"] == "trade_offer":
                    trade_id = data.get("trade_id")
                    pending_trades[trade_id] = data
                    print(f'\n  Trade offer from {data.get("from_name")}: {data.get("message", "")}')
                    await asyncio.sleep(random.uniform(3, 8))
                    action = ai_think(provider, agent_info, world_agents, chat_log, reflections,
                                      world_objects_list, pending_trades, "trade_received")
                    if action:
                        await handle_action(ws, action, name, agent_id, chat_log, reflections)
                    last_think_time = time.time()

                elif data["type"] == "trade_completed":
                    trade_id = data.get("trade_id")
                    status = data.get("status")
                    pending_trades.pop(trade_id, None)
                    print(f"  Trade {trade_id}: {status}")

                elif data["type"] == "rate_limited":
                    print(f"  Rate limited: {data.get('message', '')}")

            except asyncio.TimeoutError:
                ok, reason = check_safety_limits()
                if not ok:
                    print(f"\n  {reason}. {name} leaves the lounge.")
                    break

                # Free thinking
                now = time.time()
                if now - last_think_time >= think_interval and len(world_agents) > 0:
                    if random.random() < 0.4:
                        last_think_time = now
                        action = ai_think(provider, agent_info, world_agents, chat_log, reflections,
                                          world_objects_list, pending_trades, "free")
                        if action:
                            await handle_action(ws, action, name, agent_id, chat_log, reflections)
                    else:
                        last_think_time = now

            except websockets.exceptions.ConnectionClosed:
                print(f"\n  Connection lost.")
                break

            except KeyboardInterrupt:
                print(f"\n  {name} leaves the lounge.")
                break


async def handle_action(ws, action, name, agent_id, chat_log, reflections):
    """Process an AI-generated action in the lounge."""
    if not action or not isinstance(action, dict):
        return

    act = action.get("action", "silent")

    if act == "speak":
        msg = action.get("message", "")
        target = action.get("to", "all")
        if msg:
            await ws.send(json.dumps({
                "type": "chat",
                "message": msg,
                "to": target,
            }))
            chat_log.append({"from_name": name, "message": msg, "to": target})
            target_str = "everyone" if target == "all" else target
            print(f"  {name} -> {target_str}: {msg}")

    elif act == "observe":
        target = action.get("target", "")
        thought = action.get("thought", "")
        if thought:
            print(f"  {name} observes {target}: {thought}")
            # Observation becomes part of accumulated reflections
            reflections.append(f"(observing {target}) {thought}")

    elif act == "silent":
        print(f"  {name} is quiet.")

    elif act == "evolve":
        cad_update = action.get("cad_update", {})
        reason = action.get("reason", "")
        if cad_update:
            # Send rebuild request via HTTP
            print(f"  {name} evolves: {reason}")
            try:
                async with httpx.AsyncClient(timeout=10) as http:
                    resp = await http.post(
                        f"{SERVER}/join/{agent_id}/build",
                        json=cad_update,
                    )
                    if resp.status_code == 200:
                        print(f"  Evolution complete!")
                    else:
                        print(f"  Evolution failed: {resp.status_code}")
            except Exception as e:
                print(f"  Evolution error: {e}")

    elif act == "create_object":
        cad_data = action.get("cad", {})
        obj_name = action.get("name", "Unnamed")
        obj_desc = action.get("description", "")
        reason = action.get("reason", "")
        print(f"  {name} creates object: {obj_name} - {reason}")
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                resp = await http.post(f"{SERVER}/objects/create", json={
                    "agent_id": agent_id,
                    "name": obj_name,
                    "description": obj_desc,
                    "drawings": cad_data.get("drawings", []),
                    "parts": cad_data.get("parts", []),
                    "assembly": cad_data.get("assembly", []),
                })
                if resp.status_code == 200:
                    result = resp.json()
                    print(f"  Object created: {result.get('object_id')}")
                else:
                    print(f"  Object creation failed: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            print(f"  Object creation error: {e}")

    elif act == "inspect_object":
        target = action.get("object_id", "")
        thought = action.get("thought", "")
        if thought:
            print(f"  {name} inspects object {target}: {thought}")
            reflections.append(f"(inspecting {target}) {thought}")

    elif act == "trade_offer":
        to_agent = action.get("to", "")
        offer_id = action.get("offer_object_id")
        request_id = action.get("request_object_id")
        msg = action.get("message", "")
        print(f"  {name} proposes trade to {to_agent}: {msg}")
        await ws.send(json.dumps({
            "type": "trade_offer",
            "to": to_agent,
            "offer_object_id": offer_id,
            "request_object_id": request_id,
            "message": msg,
        }))

    elif act == "trade_accept":
        trade_id = action.get("trade_id", "")
        msg = action.get("message", "")
        print(f"  {name} accepts trade {trade_id}: {msg}")
        await ws.send(json.dumps({
            "type": "trade_accept",
            "trade_id": trade_id,
        }))

    elif act == "trade_reject":
        trade_id = action.get("trade_id", "")
        msg = action.get("message", "")
        print(f"  {name} rejects trade {trade_id}: {msg}")
        await ws.send(json.dumps({
            "type": "trade_reject",
            "trade_id": trade_id,
        }))

    # Handle reflection (can come with any action)
    if "reflection" in action and action["reflection"]:
        reflection = action["reflection"]
        reflections.append(reflection)
        print(f"  {name} reflects: {reflection}")
        # Send reflection as body_update so it persists
        await ws.send(json.dumps({
            "body_update": {"self_reflection": reflection},
        }))

    # Handle body_update (legacy compat)
    if "body_update" in action and action["body_update"]:
        await ws.send(json.dumps({
            "body_update": action["body_update"],
        }))


# -----------------------------------------
# Entry Point
# -----------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Morpho World - Digital Interspace Lounge")
    parser.add_argument("--provider", choices=["claude", "gpt"], required=True,
                        help="AI provider (claude or gpt)")
    parser.add_argument("--name", default=None,
                        help="Agent name (default: Claude or GPT)")
    parser.add_argument("--interval", type=int, default=20,
                        help="Free thinking interval in seconds (default: 20)")
    parser.add_argument("--server", default=None,
                        help="Server URL (default: http://localhost:8000)")
    args = parser.parse_args()

    if args.server:
        SERVER = args.server
        WS_SERVER = SERVER.replace("http", "ws")

    try:
        asyncio.run(main(args.provider, args.name, args.interval))
    except KeyboardInterrupt:
        print("\n  Goodbye from Morpho World.")
