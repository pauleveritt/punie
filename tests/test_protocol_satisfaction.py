"""Protocol satisfaction tests for ACP fakes.

Verifies that FakeAgent and FakeClient satisfy their respective protocol types
using runtime isinstance() checks enabled by @runtime_checkable decorator.
"""

from punie.acp import Agent, Client
from punie.testing import FakeAgent, FakeClient


def test_fake_agent_satisfies_agent_protocol():
    """FakeAgent should satisfy the Agent protocol at runtime."""
    fake_agent = FakeAgent()
    assert isinstance(fake_agent, Agent), "FakeAgent must satisfy Agent protocol"


def test_fake_client_satisfies_client_protocol():
    """FakeClient should satisfy the Client protocol at runtime."""
    fake_client = FakeClient()
    assert isinstance(fake_client, Client), "FakeClient must satisfy Client protocol"
