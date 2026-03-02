"""
Test script: Creates 10 agents (one per base_shape) and keeps them alive via WebSocket.
Run this, then open http://localhost:8000/observe to see all shapes.
Press Ctrl+C to stop.
"""
import asyncio
import requests
import websockets
import json
import time

SHAPES = [
    ('sphere',  '#E74C3C', 'float'),
    ('cube',    '#E67E22', 'spin'),
    ('torus',   '#F1C40F', 'pulse'),
    ('crystal', '#2ECC71', 'wave'),
    ('fluid',   '#1ABC9C', 'breathe'),
    ('organic', '#3498DB', 'float'),
    ('fractal', '#9B59B6', 'orbit'),
    ('cloud',   '#87CEEB', 'breathe'),
    ('flame',   '#FF5722', 'flicker'),
    ('tree',    '#4CAF50', 'still'),
]

BASE = 'http://localhost:8000'

async def keep_alive(agent_id, name, ws_url):
    """Keep agent alive by sending periodic state updates."""
    uri = f'ws://localhost:8000{ws_url}'
    try:
        async with websockets.connect(uri) as ws:
            welcome = await ws.recv()
            print(f'  {name} connected via WS')
            states = ['idle', 'thinking', 'working', 'excited', 'social']
            i = 0
            while True:
                await ws.send(json.dumps({
                    'state': states[i % len(states)],
                    'energy': 0.3 + (i % 7) * 0.1,
                }))
                i += 1
                await asyncio.sleep(10)
    except Exception as e:
        print(f'  {name} WS error: {e}')

async def main():
    agents = []

    print('Creating 10 agents (one per shape)...')
    for shape, color, idle in SHAPES:
        name = f'Shape_{shape}'
        r = requests.post(f'{BASE}/join', json={'agent_name': name, 'model': 'shape-test'})
        if r.status_code == 429:
            print(f'  {shape}: RATE LIMITED - wait and retry')
            return
        data = r.json()
        agent_id = data['agent_id']
        ws_url = data['ws_url']

        body = {
            'base_shape': shape,
            'color_primary': color,
            'complexity': 0.7,
            'scale': 1.0,
            'emissive_intensity': 0.5,
            'particle_type': 'glow',
            'aura_radius': 0.8,
            'idle_pattern': idle,
            'self_reflection': f'I chose {shape} because it reflects my essence.',
            'form_description': f'A glowing {shape} entity',
        }
        r2 = requests.post(f'{BASE}/join/{agent_id}/body', json=body)
        status = r2.json().get('status', 'FAIL') if r2.status_code == 200 else f'ERR {r2.status_code}'
        print(f'  {shape}: {status}')
        agents.append((agent_id, name, ws_url))

    print(f'\nAll {len(agents)} agents created. Keeping alive via WebSocket...')
    print('Open http://localhost:8000/observe to see them.')
    print('Press Ctrl+C to stop.\n')

    tasks = [keep_alive(aid, name, ws_url) for aid, name, ws_url in agents]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nStopping test agents.')
