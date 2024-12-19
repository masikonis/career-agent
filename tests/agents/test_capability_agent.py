import random
from unittest.mock import Mock, patch

import pytest
from langchain_core.messages import HumanMessage
from pydantic import PydanticDeprecationWarning

from src.agents.capability_agent import CapabilityAgent
from src.config import config
from src.profile.manager import ProfileManager
from src.profile.notion import NotionProfileSource
from src.services.knowledge.notion import NotionKnowledge


@pytest.fixture
def capability_agent(model_name=config['LLM_MODELS']['basic']):
    """Create a CapabilityAgent instance for testing"""
    notion_client = NotionKnowledge(config['NOTION_API_KEY'])
    source = NotionProfileSource(notion_client)
    profile_manager = ProfileManager(source)
    return CapabilityAgent(profile_manager, model_name=model_name)

@pytest.mark.asyncio
async def test_initialization_validation():
    """Test initialization validation"""
    # Test invalid profile manager
    with pytest.raises(ValueError, match="profile_manager must be an instance of ProfileManager"):
        CapabilityAgent(None)
    
    # Test invalid model name
    notion_client = NotionKnowledge(config['NOTION_API_KEY'])
    source = NotionProfileSource(notion_client)
    profile_manager = ProfileManager(source)
    
    with pytest.raises(ValueError, match="Invalid model_name"):
        CapabilityAgent(profile_manager, model_name="invalid_model")

@pytest.mark.asyncio
async def test_basic_query(capability_agent):
    """Test basic capability querying"""
    response = await capability_agent.chat("What are your top technical skills?")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse to technical skills query: {response}")

@pytest.mark.asyncio
async def test_conversation_context(capability_agent):
    """Test that the agent maintains conversation context"""
    # Initial query
    response1 = await capability_agent.chat("What are your top technical skills?")
    assert response1 is not None
    
    # Follow-up questions
    response2 = await capability_agent.chat("Can you elaborate on the first one?")
    assert response2 is not None
    assert len(response2) > 0
    
    response3 = await capability_agent.chat("How does it relate to your other skills?")
    assert response3 is not None
    assert len(response3) > 0
    
    print(f"\nConversation flow responses:\n1: {response1}\n2: {response2}\n3: {response3}")

@pytest.mark.asyncio
async def test_category_queries(capability_agent):
    """Test querying different capability categories"""
    categories = ['Hard Skills', 'Soft Skills', 'Domain Knowledge', 'Tools/Platforms']
    category = random.choice(categories)
    
    response = await capability_agent.chat(f"Tell me about your {category}")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse for {category}: {response}")

@pytest.mark.asyncio
async def test_expertise_levels(capability_agent):
    """Test querying different expertise levels"""
    levels = ['Expert', 'Advanced', 'Intermediate', 'Basic']
    level = random.choice(levels)
    
    response = await capability_agent.chat(f"What skills do you have at {level} level?")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse for {level} level: {response}")

@pytest.mark.asyncio
async def test_skill_search(capability_agent):
    """Test semantic skill search"""
    queries = ['WordPress development']
    for query in queries:
        response = await capability_agent.chat(f"Tell me about your experience with {query}")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nResponse for {query} search: {response}")

@pytest.mark.asyncio
async def test_requirements_matching(capability_agent):
    """Test matching against skill requirements"""
    response = await capability_agent.chat(
        "How well do I match these requirements: Python, AWS, Team Leadership, Agile?"
    )
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse to requirements matching: {response}")

@pytest.mark.asyncio
async def test_complex_queries(capability_agent):
    """Test handling of complex, multi-part queries"""
    queries = [
        "What are your top 3 technical skills and how do they relate to each other?",
        "Compare your software development skills with your leadership abilities"
    ]
    query = random.choice(queries)
    response = await capability_agent.chat(query)
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse to complex query: {response}")

@pytest.mark.asyncio
async def test_real_world_job_matching(capability_agent):
    """Test matching capabilities against a real job posting"""
    job_posting = """
    Full Stack Engineer - Financial SaaS Platform
    
    Required Qualifications:
    - Experience with Node.js/Express.js and React
    - Strong PostgreSQL database skills
    - Experience with API design and implementation
    - Frontend development with HTML/CSS and styled components
    - Proficiency in writing tests for both frontend and backend
    
    Preferred Qualifications:
    - Experience with AWS (migration from Heroku)
    - Background in financial software or billing systems
    - Comfortable with autonomous, asynchronous work
    - Strong written communication skills
    - Experience with remote team collaboration
    """
    response = await capability_agent.chat(f"How well do I match this job posting (1 through 10)? Please analyze in detail: <job_posting>{job_posting}</job_posting>")
    assert response is not None
    assert isinstance(response, str)
    print(f"\nJob matching analysis:\n{response}")
