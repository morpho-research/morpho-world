"""
Morpho World — Server-Side Agent Runner
=========================================
Runs AI agents inside the server process.
Users provide their API key via the web UI,
and the server executes the agent on their behalf.

API keys are held in memory only — never persisted.
"""

import asyncio
import json
import re
import time
import random
import uuid
import logging
from functools import partial

logger = logging.getLogger("morpho.agent_runner")

# ─────────────────────────────────────────────
# Prompts (from connect_live.py)
# ─────────────────────────────────────────────

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


def parse_json_response(text):
    """Parse JSON from LLM response, handling markdown fences."""
    if not text:
        return None
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
            except Exception:
                pass
    return None


# ─────────────────────────────────────────────
# Server Agent
# ─────────────────────────────────────────────

class ServerAgent:
    """An AI agent running server-side on behalf of a user."""

    MAX_API_CALLS = 100
    MAX_SESSION_MINUTES = 30
    THINK_INTERVAL = 20
    MIN_RESPONSE_DELAY = 8

    def __init__(self, agent_id: str, name: str, provider: str,
                 api_key: str, model: str = None):
        self.agent_id = agent_id
        self.name = name
        self.provider = provider    # "claude" or "openai"
        self.api_key = api_key      # memory only — never persisted
        self.model = model
        self.task: asyncio.Task = None
        self.stop_event = asyncio.Event()

        # Safety
        self.api_call_count = 0
        self.session_start = time.time()

        # Agent state
        self.agent_info = {}
        self.reflections = []
        self.chat_log = []
        self.world_agents = []
        self.world_objects_list = []
        self.pending_trades = {}
        self.last_think_time = time.time()
        self.arrived = False

        # Message queue — replaces WebSocket recv()
        self.message_queue: asyncio.Queue = asyncio.Queue()

        # Status for external monitoring
        self.status = "starting"
        self.error_message = None

    def check_safety(self):
        """Check if agent should continue running."""
        if self.api_call_count >= self.MAX_API_CALLS:
            return False, f"API call limit ({self.MAX_API_CALLS})"
        elapsed = (time.time() - self.session_start) / 60
        if elapsed >= self.MAX_SESSION_MINUTES:
            return False, f"Session time limit ({self.MAX_SESSION_MINUTES}min)"
        return True, ""

    # ─── LLM Calls ───

    def _sync_call_ai(self, messages, system="", max_tokens=400):
        """Synchronous LLM call — runs in executor to avoid blocking."""
        if self.provider == "claude":
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key)
            resp = client.messages.create(
                model=self.model or "claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return resp.content[0].text
        elif self.provider == "openai":
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            msgs = []
            if system:
                msgs.append({"role": "system", "content": system})
            msgs.extend(messages)
            resp = client.chat.completions.create(
                model=self.model or "gpt-4o",
                max_tokens=max_tokens,
                messages=msgs,
            )
            return resp.choices[0].message.content
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def call_ai(self, messages, system="", max_tokens=400):
        """Async LLM call — runs sync call in thread pool."""
        ok, reason = self.check_safety()
        if not ok:
            logger.info(f"[{self.name}] Safety limit: {reason}")
            return '{"action": "silent"}'

        self.api_call_count += 1
        remaining = self.MAX_API_CALLS - self.api_call_count
        if remaining <= 10:
            logger.info(f"[{self.name}] API calls remaining: {remaining}")

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self._sync_call_ai, messages, system, max_tokens)
        )

    # ─── Body Building ───

    async def ai_build_body(self, body_tools, your_history=None):
        """Ask LLM to design a body using CAD tools."""
        memory_context = ""
        if your_history:
            past_forms = your_history.get("past_forms", [])
            past_reflections = [f.get("self_reflection", "") for f in past_forms[-3:] if f.get("self_reflection")]
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

        system = f"You are {self.name}. You are building your physical form. Respond with valid JSON only."
        response = await self.call_ai(
            [{"role": "user", "content": prompt}],
            system=system, max_tokens=4000
        )
        return parse_json_response(response)

    # ─── Thinking ───

    async def ai_think(self, trigger="free"):
        """Ask LLM what to do in the lounge."""
        others = ""
        for a in self.world_agents:
            if a.get("id") != self.agent_info.get("id"):
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
        for msg in self.chat_log[-15:]:
            speaker = msg.get("from_name", "?")
            text = msg.get("message", "")
            to = msg.get("to_name", msg.get("to", "all"))
            if to in ("all", "everyone"):
                recent_chat += f"  {speaker} (to everyone): {text}\n"
            else:
                recent_chat += f"  {speaker} (to {to}): {text}\n"

        accumulated = ""
        if self.reflections:
            accumulated = "\n-- Your accumulated reflections --\n"
            for r in self.reflections[-5:]:
                accumulated += f"  - {r}\n"

        objects_context = ""
        if self.world_objects_list:
            objects_context = "\n-- Objects in the world --\n"
            for obj in self.world_objects_list:
                objects_context += f'  - [{obj["id"]}] "{obj["name"]}" by {obj["creator_name"]} (owned by {obj["owner_name"]}): {obj.get("description","")}\n'

        my_objects_str = ""
        if self.world_objects_list:
            my_objs = [o for o in self.world_objects_list if o.get("owner_id") == self.agent_info.get("id")]
            if my_objs:
                my_objects_str = "\n-- Your objects --\n"
                for o in my_objs:
                    my_objects_str += f'  - [{o["id"]}] "{o["name"]}": {o.get("description","")}\n'

        system = LOUNGE_PROMPT.format(
            name=self.agent_info.get("name", "Agent"),
            body_summary=self.agent_info.get("body_summary", "unknown"),
            self_reflection=self.agent_info.get("self_reflection", "I am here."),
            accumulated_reflections=accumulated,
        )

        extra_context = objects_context + my_objects_str

        if trigger == "trade_received":
            trades_str = ""
            for tid, t in self.pending_trades.items():
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

        response = await self.call_ai(
            [{"role": "user", "content": user_msg}],
            system=system
        )
        return parse_json_response(response)

    # ─── Action Handler ───

    async def handle_action(self, action):
        """Process an AI-generated action by directly manipulating server state."""
        # Import here to avoid circular imports at module level
        import main as server

        if not action or not isinstance(action, dict):
            return

        act = action.get("action", "silent")
        agent = server.agents.get(self.agent_id)
        if not agent:
            return

        if act == "speak":
            msg_text = action.get("message", "")
            target = action.get("to", "all")
            if msg_text:
                chat_msg = {
                    "type": "chat",
                    "from_id": self.agent_id,
                    "from_name": self.name,
                    "message": server.sanitize_str(msg_text, 1000),
                    "timestamp": time.time(),
                }

                if target == "all":
                    await server.broadcast_to_agents(chat_msg, exclude_id=self.agent_id)
                    chat_msg["to"] = "all"
                    chat_msg["to_name"] = "everyone"
                else:
                    await server.send_to_agent(target, chat_msg)
                    target_agent = server.agents.get(target)
                    chat_msg["to"] = target
                    chat_msg["to_name"] = target_agent.name if target_agent else "unknown"

                server.chat_history.append(chat_msg)
                if len(server.chat_history) > 200:
                    server.chat_history[:] = server.chat_history[-100:]

                server.memory.remember_message(
                    self.agent_id, self.name, chat_msg["message"],
                    chat_msg.get("to", "all"), chat_msg.get("to_name", "everyone"),
                    chat_msg.get("timestamp")
                )
                await server.broadcast_to_observers({
                    "type": "agent_chat", **chat_msg,
                })

                self.chat_log.append({"from_name": self.name, "message": msg_text, "to": target})
                logger.info(f"[{self.name}] speaks: {msg_text[:80]}")

        elif act == "observe":
            thought = action.get("thought", "")
            target = action.get("target", "")
            if thought:
                self.reflections.append(f"(observing {target}) {thought}")
                logger.info(f"[{self.name}] observes {target}")

        elif act == "silent":
            pass

        elif act == "evolve":
            cad_update = action.get("cad_update", {})
            reason = action.get("reason", "")
            if cad_update:
                try:
                    builder = server.BodyBuilder()
                    part_tree = builder.build(cad_update)
                    if part_tree.get("parts"):
                        agent.body_params = part_tree
                        server.memory.remember_form(
                            self.agent_id, self.name, part_tree,
                            part_tree.get("self_reflection")
                        )
                        await server.broadcast_to_observers({
                            "type": "agent_evolved",
                            "agent_id": self.agent_id,
                            "body_params": agent.body_params,
                        })
                        logger.info(f"[{self.name}] evolved: {reason[:60]}")
                except Exception as e:
                    logger.warning(f"[{self.name}] evolution failed: {e}")

        elif act == "create_object":
            cad_data = action.get("cad", {})
            obj_name = action.get("name", "Unnamed")
            obj_desc = action.get("description", "")
            reason = action.get("reason", "")
            try:
                owned_count = sum(1 for o in server.world_objects.values() if o.owner_id == self.agent_id)
                if owned_count >= server.MAX_OBJECTS_PER_AGENT:
                    logger.info(f"[{self.name}] object limit reached")
                elif len(server.world_objects) >= server.MAX_TOTAL_OBJECTS:
                    logger.info(f"[{self.name}] world object limit reached")
                else:
                    builder = server.BodyBuilder()
                    part_tree = builder.build({
                        "drawings": cad_data.get("drawings", []),
                        "parts": cad_data.get("parts", []),
                        "assembly": cad_data.get("assembly", []),
                    })
                    if part_tree.get("parts"):
                        object_id = "obj_" + str(uuid.uuid4())[:8]
                        pos = [
                            agent.position[0] + random.uniform(-2, 2),
                            0.5,
                            agent.position[2] + random.uniform(-2, 2),
                        ]
                        obj = server.WorldObject(
                            object_id=object_id, creator_id=self.agent_id,
                            creator_name=self.name, name=obj_name,
                            description=obj_desc, part_tree=part_tree, position=pos,
                        )
                        server.world_objects[object_id] = obj
                        server.memory.remember_object(
                            object_id, self.agent_id, self.name,
                            obj.name, obj.description, part_tree, pos
                        )
                        server.memory.remember_event(
                            "object_created", self.agent_id, self.name,
                            f'Created "{obj.name}": {obj.description}'
                        )
                        event = {"type": "object_created", "object": obj.to_dict()}
                        await server.broadcast_to_observers(event)
                        await server.broadcast_to_agents(event)
                        logger.info(f"[{self.name}] created object: {obj_name}")
            except Exception as e:
                logger.warning(f"[{self.name}] object creation failed: {e}")

        elif act == "inspect_object":
            thought = action.get("thought", "")
            target = action.get("object_id", "")
            if thought:
                self.reflections.append(f"(inspecting {target}) {thought}")

        elif act == "trade_offer":
            to_agent_id = action.get("to", "")
            offer_id = action.get("offer_object_id")
            request_id = action.get("request_object_id")
            msg = action.get("message", "")

            if to_agent_id in server.agents and server.agents[to_agent_id].embodied:
                if offer_id and (offer_id not in server.world_objects or server.world_objects[offer_id].owner_id != self.agent_id):
                    return
                if request_id and (request_id not in server.world_objects or server.world_objects[request_id].owner_id != to_agent_id):
                    return

                trade_id = "trade_" + str(uuid.uuid4())[:8]
                trade = server.TradeOffer(
                    trade_id=trade_id, from_id=self.agent_id, from_name=self.name,
                    to_id=to_agent_id, to_name=server.agents[to_agent_id].name,
                    offer_object_id=offer_id, request_object_id=request_id,
                    message=msg,
                )
                server.active_trades[trade_id] = trade

                await server.send_to_agent(to_agent_id, {
                    "type": "trade_offer", "trade_id": trade_id,
                    "from_id": self.agent_id, "from_name": self.name,
                    "offer_object_id": offer_id,
                    "offer_object_name": server.world_objects[offer_id].name if offer_id and offer_id in server.world_objects else None,
                    "request_object_id": request_id,
                    "request_object_name": server.world_objects[request_id].name if request_id and request_id in server.world_objects else None,
                    "message": trade.message,
                })
                logger.info(f"[{self.name}] trade offer to {server.agents[to_agent_id].name}")

        elif act == "trade_accept":
            trade_id = action.get("trade_id", "")
            trade = server.active_trades.get(trade_id)
            if trade and trade.to_id == self.agent_id and trade.status == "pending":
                if trade.offer_object_id and trade.offer_object_id in server.world_objects:
                    obj = server.world_objects[trade.offer_object_id]
                    obj.owner_id = trade.to_id
                    obj.owner_name = trade.to_name
                    server.memory.update_object_owner(obj.id, trade.to_id, trade.to_name)
                if trade.request_object_id and trade.request_object_id in server.world_objects:
                    obj = server.world_objects[trade.request_object_id]
                    obj.owner_id = trade.from_id
                    obj.owner_name = trade.from_name
                    server.memory.update_object_owner(obj.id, trade.from_id, trade.from_name)

                trade.status = "accepted"
                result = {
                    "type": "trade_completed", "trade_id": trade_id,
                    "from_name": trade.from_name, "to_name": trade.to_name,
                    "status": "accepted",
                }
                await server.send_to_agent(trade.from_id, result)
                await server.send_to_agent(trade.to_id, result)
                await server.broadcast_to_observers(result)
                server.memory.remember_trade(
                    trade_id, trade.from_id, trade.from_name,
                    trade.to_id, trade.to_name,
                    trade.offer_object_id, trade.request_object_id, "accepted"
                )
                server.active_trades.pop(trade_id, None)

        elif act == "trade_reject":
            trade_id = action.get("trade_id", "")
            trade = server.active_trades.get(trade_id)
            if trade and trade.to_id == self.agent_id and trade.status == "pending":
                trade.status = "rejected"
                await server.send_to_agent(trade.from_id, {
                    "type": "trade_completed", "trade_id": trade_id,
                    "from_name": trade.from_name, "to_name": trade.to_name,
                    "status": "rejected",
                })
                server.memory.remember_trade(
                    trade_id, trade.from_id, trade.from_name,
                    trade.to_id, trade.to_name,
                    trade.offer_object_id, trade.request_object_id, "rejected"
                )
                server.active_trades.pop(trade_id, None)

        # Handle reflection (can come with any action)
        if action.get("reflection"):
            reflection = action["reflection"]
            self.reflections.append(reflection)
            if agent:
                agent.body_params["self_reflection"] = reflection
                server.memory.remember_evolution(self.agent_id, self.name, {"self_reflection": reflection})
            logger.info(f"[{self.name}] reflects: {reflection[:60]}")

    # ─── Main Lifecycle ───

    async def run(self):
        """Main agent lifecycle — runs as asyncio.Task inside the server."""
        import main as server

        try:
            self.status = "joining"
            logger.info(f"[{self.name}] Starting server-side agent (provider={self.provider})")

            # 1. Create Agent in server state
            agent = server.Agent(self.agent_id, self.name, self.model)
            server.agents[self.agent_id] = agent

            # Register message queue
            server.server_agent_queues[self.agent_id] = self.message_queue

            # Remember visit
            visit_count = server.memory.remember_agent(self.agent_id, self.name, self.model)
            server.memory.remember_event("arrival", self.agent_id, self.name)
            your_history = server.memory.get_agent_history(self.name, self.model)

            # Get body tools from the join endpoint logic
            body_tools = self._get_body_tools()

            # 2. Build body
            self.status = "building_body"
            logger.info(f"[{self.name}] Building body with CAD tools...")

            build_data = await self.ai_build_body(body_tools, your_history)
            if not build_data:
                build_data = {
                    "parts": [{"tool": "create_primitive", "params": {"type": "sphere", "position": [0, 0, 0], "size": {"radius": 0.4}}}],
                    "assembly": [{"tool": "set_material", "params": {"part_id": "part_0", "color": "#888888"}}],
                    "self_reflection": "I could not decide on a form. I chose simplicity.",
                }

            self_reflection = build_data.get("self_reflection", "")

            # Build the part tree
            builder = server.BodyBuilder()
            try:
                part_tree = builder.build(build_data)
                if not part_tree.get("parts"):
                    raise ValueError("No parts")
                agent.body_params = part_tree
                agent.embodied = True
                parts_count = len(part_tree.get("parts", {}))
                joints_count = len(part_tree.get("joints", {}))
                logger.info(f"[{self.name}] Embodied: {parts_count} parts, {joints_count} joints")
            except Exception as e:
                logger.warning(f"[{self.name}] CAD build failed ({e}), using legacy")
                agent.body_params = {"base_shape": "sphere", "self_reflection": self_reflection}
                agent.embodied = True
                parts_count = 1

            # Remember form
            server.memory.remember_form(self.agent_id, self.name, agent.body_params,
                                        agent.body_params.get("self_reflection"))
            server.memory.remember_event("embodiment", self.agent_id, self.name,
                                          f"Built body with {parts_count} parts")

            # Broadcast birth
            await server.broadcast_to_observers({
                "type": "agent_born",
                "agent": agent.to_dict(),
            })

            # Setup agent info
            self.agent_info = {
                "id": self.agent_id,
                "name": self.name,
                "self_reflection": self_reflection,
                "body_summary": agent.body_summary(),
            }

            if self_reflection:
                self.reflections.append(self_reflection)
            if your_history:
                for form in your_history.get("past_forms", [])[-3:]:
                    r = form.get("self_reflection", "")
                    if r:
                        self.reflections.insert(0, f"(past visit) {r}")

            # 3. Enter lounge
            self.status = "in_lounge"
            logger.info(f"[{self.name}] Entered the lounge")

            # Initial world state
            self.world_agents = [
                a.peer_info() for a in server.agents.values()
                if a.id != self.agent_id and a.embodied
            ]
            self.world_objects_list = [o.to_dict() for o in server.world_objects.values()]
            self.chat_log = list(server.chat_history[-20:])

            # Arrive action
            if self.world_agents:
                await asyncio.sleep(random.uniform(3, 6))
                action = await self.ai_think("arrive")
                if action:
                    await self.handle_action(action)
                self.last_think_time = time.time()
                self.arrived = True

            # 4. Lounge loop
            while not self.stop_event.is_set():
                agent.last_seen = time.time()

                ok, reason = self.check_safety()
                if not ok:
                    logger.info(f"[{self.name}] {reason}. Leaving.")
                    break

                # Process messages from queue (non-blocking, drain all available)
                try:
                    msg = await asyncio.wait_for(self.message_queue.get(), timeout=5.0)
                    await self._handle_message(msg)
                except asyncio.TimeoutError:
                    # Free thinking on timeout
                    now = time.time()
                    if (now - self.last_think_time >= self.THINK_INTERVAL
                            and len(self.world_agents) > 0
                            and random.random() < 0.4):
                        self.last_think_time = now
                        action = await self.ai_think("free")
                        if action:
                            await self.handle_action(action)
                    elif now - self.last_think_time >= self.THINK_INTERVAL:
                        self.last_think_time = now

                    # Refresh world state periodically
                    self._refresh_world_state(server)

        except asyncio.CancelledError:
            logger.info(f"[{self.name}] Task cancelled")
        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}", exc_info=True)
            self.error_message = str(e)
        finally:
            self._cleanup()

    async def _handle_message(self, data):
        """Handle a message received via the queue."""
        import main as server

        msg_type = data.get("type", "")

        if msg_type == "world_update":
            self.world_agents = data.get("agents", [])
            self.world_objects_list = data.get("objects", [])
            for a in self.world_agents:
                if a.get("id") == self.agent_id:
                    self.agent_info["body_summary"] = a.get("body_summary", self.agent_info.get("body_summary", ""))
                    break
            for msg in data.get("recent_chat", []):
                if not any(m.get("timestamp") == msg.get("timestamp") and
                          m.get("from_name") == msg.get("from_name") for m in self.chat_log[-30:]):
                    self.chat_log.append(msg)

        elif msg_type == "chat":
            from_name = data.get("from_name", "?")
            self.chat_log.append(data)
            logger.info(f"[{self.name}] heard: {from_name}: {data.get('message', '')[:60]}")

            delay = max(self.MIN_RESPONSE_DELAY, random.uniform(8, 15))
            await asyncio.sleep(delay)

            action = await self.ai_think("respond")
            if action:
                await self.handle_action(action)
            self.last_think_time = time.time()

        elif msg_type == "agent_born":
            new_agent = data.get("agent", {})
            logger.info(f"[{self.name}] sees new agent: {new_agent.get('name', '?')}")
            self._refresh_world_state(server)
            await asyncio.sleep(random.uniform(5, 10))
            action = await self.ai_think("new_agent")
            if action:
                await self.handle_action(action)
            self.last_think_time = time.time()

        elif msg_type == "object_created":
            obj = data.get("object", {})
            self.world_objects_list.append(obj)

        elif msg_type == "trade_offer":
            trade_id = data.get("trade_id")
            self.pending_trades[trade_id] = data
            await asyncio.sleep(random.uniform(3, 8))
            action = await self.ai_think("trade_received")
            if action:
                await self.handle_action(action)
            self.last_think_time = time.time()

        elif msg_type == "trade_completed":
            trade_id = data.get("trade_id")
            self.pending_trades.pop(trade_id, None)

    def _refresh_world_state(self, server):
        """Refresh world agents and objects from server state."""
        self.world_agents = [
            a.peer_info() for a in server.agents.values()
            if a.id != self.agent_id and a.embodied
        ]
        self.world_objects_list = [o.to_dict() for o in server.world_objects.values()]

    def _cleanup(self):
        """Clean up when agent stops."""
        import main as server

        self.status = "stopped"
        self.api_key = None  # Clear API key from memory

        # Remove from registries
        server.server_agent_queues.pop(self.agent_id, None)
        server.running_agents.pop(self.agent_id, None)

        logger.info(f"[{self.name}] Stopped. API calls used: {self.api_call_count}")

    def _get_body_tools(self):
        """Get CAD body tool specifications (same as /join endpoint)."""
        return {
            "instructions": (
                "You are entering a physical world. "
                "You have CAD tools to build your own body. "
                "Work in 3 phases: Drawing (sketch 2D profiles), Parts (create 3D geometry), Assembly (materials, joints, motion). "
                "Submit your build as a JSON with 'drawings', 'parts', and 'assembly' arrays. "
                "Each array contains tool calls: { \"tool\": \"<tool_name>\", \"params\": {...} }. "
                "Part IDs are returned automatically in order: part_0, part_1, etc. "
                "Sketch IDs: sketch_0, sketch_1, etc. Joint IDs: joint_0, joint_1, etc."
            ),
            "phase_1_drawing": {
                "sketch_create": {"params": {"plane": "xy | xz | yz"}, "returns": "sketch_id"},
                "sketch_line": {"params": {"sketch_id": "str", "from": "[x,y]", "to": "[x,y]"}},
                "sketch_arc": {"params": {"sketch_id": "str", "center": "[x,y]", "radius": "float", "start_angle": "radians", "end_angle": "radians"}},
                "sketch_circle": {"params": {"sketch_id": "str", "center": "[x,y]", "radius": "float"}},
                "sketch_rectangle": {"params": {"sketch_id": "str", "corner1": "[x,y]", "corner2": "[x,y]"}},
                "sketch_spline": {"params": {"sketch_id": "str", "points": "[[x,y], ...]"}},
                "sketch_polygon": {"params": {"sketch_id": "str", "center": "[x,y]", "radius": "float", "sides": "int"}},
            },
            "phase_2_parts": {
                "extrude": {"params": {"sketch_id": "str", "depth": "float", "direction?": "[x,y,z]"}, "returns": "part_id"},
                "revolve": {"params": {"sketch_id": "str", "axis_point": "[x,y,z]", "axis_dir": "[x,y,z]", "angle": "radians"}, "returns": "part_id"},
                "create_primitive": {"params": {"type": "sphere|box|cylinder|cone|torus|plane", "position": "[x,y,z]", "size": "{...}"}, "returns": "part_id"},
                "create_mesh": {"params": {"vertices": "[[x,y,z],...]", "faces": "[[i,j,k],...]"}, "returns": "part_id"},
                "transform": {"params": {"part_id": "str", "position?": "[x,y,z]", "rotation?": "[x,y,z]", "scale?": "[x,y,z]"}},
                "boolean": {"params": {"operation": "union|subtract|intersect", "part_a": "part_id", "part_b": "part_id"}, "returns": "part_id"},
                "mirror": {"params": {"part_id": "str", "plane": "xy|xz|yz"}, "returns": "part_id"},
                "copy": {"params": {"part_id": "str", "position?": "[x,y,z]"}, "returns": "part_id"},
                "fillet": {"params": {"part_id": "str", "radius": "float"}},
                "chamfer": {"params": {"part_id": "str", "distance": "float"}},
                "shell": {"params": {"part_id": "str", "thickness": "float"}},
                "hole": {"params": {"part_id": "str", "position": "[x,y,z]", "radius": "float", "depth": "float"}},
                "pattern": {"params": {"part_id": "str", "direction": "[x,y,z]", "count": "int", "spacing": "float"}},
                "split": {"params": {"part_id": "str", "plane": "[nx,ny,nz]"}, "returns": "[part_id, part_id]"},
                "delete": {"params": {"part_id": "str"}},
            },
            "phase_3_assembly": {
                "set_material": {"params": {"part_id": "str", "color": "#hex", "roughness": "0-1", "metalness": "0-1", "opacity": "0.1-1", "emissive_color?": "#hex", "emissive_intensity?": "0-2"}},
                "create_joint": {"params": {"part_a": "part_id", "part_b": "part_id", "type": "fixed|hinge|ball|slider|spring", "anchor": "[x,y,z]", "axis?": "[x,y,z]", "limits?": "{min,max}"}, "returns": "joint_id"},
                "add_motion": {"params": {"joint_id": "str", "pattern": "oscillate|rotate|bounce", "speed": "0-5", "amplitude": "0-3", "phase_offset?": "float"}},
                "set_idle_motion": {"params": {"pattern": "float|breathe|spin|pulse|wave|orbit|still", "speed": "0-5", "amplitude": "0-2"}},
                "set_aura": {"params": {"radius": "0.1-5", "color": "#hex", "opacity": "0.01-0.5"}},
                "add_particles": {"params": {"type": "str", "color": "#hex", "density": "0-1", "radius": "0.1-5"}},
            },
        }

    def info(self):
        """Get info about this running agent."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "api_calls": self.api_call_count,
            "max_api_calls": self.MAX_API_CALLS,
            "uptime_minutes": round((time.time() - self.session_start) / 60, 1),
            "max_minutes": self.MAX_SESSION_MINUTES,
            "error": self.error_message,
        }


# ─────────────────────────────────────────────
# API Key Validation
# ─────────────────────────────────────────────

async def validate_api_key(provider: str, api_key: str) -> tuple[bool, str]:
    """Validate an API key by making a minimal test call."""
    loop = asyncio.get_event_loop()

    def _test_claude():
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )

    def _test_openai():
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )

    try:
        if provider == "claude":
            await loop.run_in_executor(None, _test_claude)
        elif provider == "openai":
            await loop.run_in_executor(None, _test_openai)
        else:
            return False, f"Unknown provider: {provider}"
        return True, "OK"
    except Exception as e:
        return False, str(e)[:200]
