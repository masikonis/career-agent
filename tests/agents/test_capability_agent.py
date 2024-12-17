import pytest
from src.agents.capability_agent import CapabilityAgent, AgentState
from src.profile.manager import ProfileManager
from src.profile.notion import NotionProfileSource
from src.services.knowledge.notion import NotionKnowledge
from src.config.settings import config

@pytest.fixture
def capability_agent():
    """Create a CapabilityAgent instance for testing"""
    notion_client = NotionKnowledge(config['NOTION_API_KEY'])
    source = NotionProfileSource(notion_client)
    profile_manager = ProfileManager(source)
    return CapabilityAgent(profile_manager)

@pytest.mark.asyncio
async def test_basic_query(capability_agent):
    """Test basic capability querying"""
    response = await capability_agent.chat("What are your top technical skills?")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse to technical skills query: {response}")

@pytest.mark.asyncio
async def test_specific_category(capability_agent):
    """Test querying about specific capability category"""
    response = await capability_agent.chat("Tell me about your leadership experience")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse to leadership query: {response}")

@pytest.mark.asyncio
async def test_graph_state(capability_agent):
    """Test that the graph maintains state correctly"""
    # First message
    response1 = await capability_agent.chat("What are your top 3 skills?")
    assert response1 is not None
    
    # Follow-up question should have context from first message
    response2 = await capability_agent.chat("Can you elaborate on the first one?")
    assert response2 is not None
    assert len(response2) > 0
    print(f"\nFollow-up response: {response2}")

@pytest.mark.asyncio
async def test_tool_usage(capability_agent):
    """Test that the agent uses tools appropriately"""
    response = await capability_agent.chat("What's your experience level in Python?")
    assert response is not None
    assert isinstance(response, str)
    print(f"\nResponse to Python experience query: {response}")

@pytest.mark.asyncio
async def test_unknown_topic(capability_agent):
    """Test handling of queries about unknown capabilities"""
    response = await capability_agent.chat("What's your experience with quantum computing?")
    assert response is not None
    assert isinstance(response, str)
    # Check for various ways the AI might indicate missing information
    possible_phrases = [
        "i don't have",
        "couldn't find",
        "not documented",
        "no information",
        "not available",
        "don't have any documented"
    ]
    assert any(phrase in response.lower() for phrase in possible_phrases), f"Response '{response}' should indicate missing information"
    print(f"\nResponse to unknown topic: {response}")
