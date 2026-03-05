import asyncio
import json
import logging
from typing import Dict, Any, List

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse
from pydantic import BaseModel

from .dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/founder/agents", tags=["Founder Agents"])

import random

# Global Command Queue and Current Command State tracking
COMMAND_QUEUE: List[str] = []

COMMAND_PHASES = [
    "RE-ALLOCATING SUBNETS",
    "BYPASSING SECURITY PROTOCOLS",
    "EXECUTING PRIMARY DIRECTIVE",
    "OPTIMIZING HEURISTIC LOOP",
    "VERIFYING CHECKSUMS",
    "COMMITTING RESULTS TO LEDGER",
]

# Base Mock Agents configuration
AGENTS: List[Dict[str, Any]] = [
    {
        "id": "agent-vanguard-01",
        "name": "Sentinel Vanguard",
        "type": "Security Forensics",
        "status": "online",
        "uptime": "99.98%",
        "cpu_load": "42%",
        "mem_usage": "18.4 GB",
        "subnets": [
            {
                "name": "Packet Analyzer",
                "status": "idle",
                "throughput": "0",
                "last_action": "Awaiting target",
            },
            {
                "name": "Anomaly Detector",
                "status": "idle",
                "throughput": "0",
                "last_action": "System standby",
            },
        ],
    },
    {
        "id": "agent-quantum-02",
        "name": "Quantum Archiver",
        "type": "Data Compression",
        "status": "online",
        "uptime": "99.99%",
        "cpu_load": "88%",
        "mem_usage": "142 GB",
        "subnets": [
            {
                "name": "P-Factor Node",
                "status": "idle",
                "throughput": "0",
                "last_action": "Idle",
            },
            {
                "name": "Hash Verifier",
                "status": "idle",
                "throughput": "0",
                "last_action": "Idle",
            },
            {
                "name": "Block Writer",
                "status": "idle",
                "throughput": "0",
                "last_action": "Idle",
            },
        ],
    },
]


class CommandPayload(BaseModel):
    command: str


@router.post("/command")
async def execute_agent_command(
    payload: CommandPayload,
    current_user: Dict = Depends(get_current_user),
):
    command = payload.command
    logger.info(f"Subagent System Override command queued: {command}")
    COMMAND_QUEUE.append(command)
    return {"status": "enqueued", "command": command}


async def multi_agent_generator():
    """Generates SSE payload simulating intense multi-agent activities or executing commands."""

    # Send Initialization State
    yield f"data: {json.dumps({'type': 'init', 'agents': AGENTS})}\n\n"

    while True:
        try:
            # Check if there is a command queued to override normal telemetry
            if len(COMMAND_QUEUE) > 0:
                active_cmd = COMMAND_QUEUE.pop(0)
                logger.info(f"[SSE] Processing command: {active_cmd}")

                # Signal Command Start
                yield f"data: {json.dumps({'type': 'command_start', 'command': active_cmd})}\n\n"

                # Execute simulated phases for all agents
                for phase in COMMAND_PHASES:
                    for agent_idx, agent in enumerate(AGENTS):
                        for sub_idx, sub in enumerate(agent["subnets"]):
                            # Simulate high load during command
                            cpu_burst = f"{random.randint(80, 100)}%"
                            mem_burst = f"{random.randint(40, 200)} GB"
                            throughput = str(random.randint(5000, 25000))

                            payload = {
                                "type": "telemetry",
                                "agent_id": agent["id"],
                                "subagent_idx": sub_idx,
                                "cpu_load": cpu_burst,
                                "mem_usage": mem_burst,
                                "status": "executing",
                                "throughput": throughput,
                                "last_action": f"[{active_cmd[:10]}...] -> {phase}",
                            }
                            yield f"data: {json.dumps(payload)}\n\n"
                            # Slight offset variation
                            await asyncio.sleep(0.1)

                    # Pause between phases
                    await asyncio.sleep(0.5)

                # Signal Command End
                yield f"data: {json.dumps({'type': 'command_end', 'command': active_cmd})}\n\n"
                # Small cooldown before returning to normal telemetry
                await asyncio.sleep(1.0)
                continue

            # --- NORMAL TELEMETRY LOOP (No active commands) ---
            agent_idx = random.randint(0, len(AGENTS) - 1)
            agent = AGENTS[agent_idx]

            subagent_idx = random.randint(0, len(agent["subnets"]) - 1)

            # Fluctuate resources normally
            cpu = f"{random.randint(10, 80)}%"
            mem = f"{random.randint(4, 32)} GB"

            status = random.choice(["active", "idle", "recalibrating"])
            throughput = str(random.randint(10, 2000)) if status == "active" else "0"

            action_pool = [
                "Scanning packet structures",
                "Polling database shards",
                "Awaiting next instruction tick",
                "Defragmenting memory space",
                "Allocating tensor matrices",
                "Verifying cryptographic signatures",
                "Applying background optimizations",
            ]

            last_action_text = (
                random.choice(action_pool)
                if status in ["active", "recalibrating"]
                else "Standby"
            )

            payload = {
                "type": "telemetry",
                "agent_id": agent["id"],
                "subagent_idx": subagent_idx,
                "cpu_load": cpu,
                "mem_usage": mem,
                "status": status,
                "throughput": throughput,
                "last_action": last_action_text,
            }

            yield f"data: {json.dumps(payload)}\n\n"

            # Normal loop speed
            await asyncio.sleep(0.4)

        except asyncio.CancelledError:
            logger.info("SSE client disconnected from agents stream.")
            break
        except Exception as e:
            logger.error(f"Error in SSE stream: {str(e)}")
            await asyncio.sleep(1)


@router.get("/stream")
async def agents_stream(current_user: Dict = Depends(get_current_user)):
    """
    Streams subagent live execution telemetry back to the Domination UI.
    Requires CustomOAuth2PasswordBearer fetching token from Query params.
    """
    return StreamingResponse(multi_agent_generator(), media_type="text/event-stream")
