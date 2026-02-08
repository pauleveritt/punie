"""Dependencies for Pydantic AI agents in Punie.

ACPDeps is the frozen dataclass holding ACP Client connection, session ID,
and tool call tracker. This is the DepsType for Punie's Pydantic AI Agent.
"""

from dataclasses import dataclass

from punie.acp import Client
from punie.acp.contrib.tool_calls import ToolCallTracker


@dataclass(frozen=True)
class ACPDeps:
    """Dependencies for Pydantic AI agents using ACP.

    This frozen dataclass holds references to the ACP client connection,
    session ID, and tool call tracker. It serves as the DepsType for
    Punie's Pydantic AI Agent, providing tools access to the ACP protocol.

    Attributes:
        client_conn: ACP Client protocol reference for making RPC calls
        session_id: Current ACP session ID
        tracker: Tool call lifecycle manager for reporting tool activity
    """

    client_conn: Client
    session_id: str
    tracker: ToolCallTracker
