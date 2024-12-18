import pytest
from src.agents.capability_agent import CapabilityAgent
from src.profile.manager import ProfileManager
from src.profile.notion import NotionProfileSource
from src.services.knowledge.notion import NotionKnowledge
from src.config.settings import config
import asyncio
from unittest.mock import Mock, patch
from langchain_core.messages import HumanMessage
import random

# ============= Initialization & Setup =============

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

# ============= Basic Functionality =============

@pytest.mark.asyncio
async def test_basic_query(capability_agent):
    """Test basic capability querying"""
    response = await capability_agent.chat("What are your top technical skills?")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse to technical skills query: {response}")

@pytest.mark.asyncio
async def test_message_format_handling(capability_agent):
    """Test handling of different message formats"""
    # Test with string message
    response1 = await capability_agent.chat("Hello")
    assert response1 is not None
    
    # Test with HumanMessage
    response2 = await capability_agent.chat(HumanMessage(content="Hello"))
    assert response2 is not None

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

# ============= Core Feature Tests =============

@pytest.mark.asyncio
async def test_category_queries(capability_agent):
    """Test querying different capability categories"""
    categories = ['Hard Skills', 'Soft Skills', 'Domain Knowledge', 'Tools/Platforms']
    # Randomly select one category to test
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
    for level in levels:
        response = await capability_agent.chat(f"What skills do you have at {level} level?")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nResponse for {level} level: {response}")

@pytest.mark.asyncio
async def test_skill_search(capability_agent):
    """Test semantic skill search"""
    queries = ['python programming', 'leadership', 'cloud technologies']
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
async def test_skill_summaries(capability_agent):
    """Test different summary formats"""
    formats = ['brief', 'detailed', 'technical', 'business']
    for format_type in formats:
        response = await capability_agent.chat(f"Give me a {format_type} summary of your capabilities")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nResponse for {format_type} summary: {response}")

@pytest.mark.asyncio
async def test_related_capabilities(capability_agent):
    """Test finding related capabilities"""
    skills = ['Python', 'Team Leadership', 'AWS']
    for skill in skills:
        response = await capability_agent.chat(f"What capabilities are related to {skill}?")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nResponse for capabilities related to {skill}: {response}")

@pytest.mark.asyncio
async def test_expertise_distribution(capability_agent):
    """Test expertise distribution analysis"""
    response = await capability_agent.chat("What's the distribution of your expertise levels?")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0
    print(f"\nResponse for expertise distribution: {response}")

# ============= Complex Scenario Tests =============

@pytest.mark.asyncio
async def test_complex_queries(capability_agent):
    """Test handling of complex, multi-part queries"""
    queries = [
        "What are your top 3 technical skills and how do they relate to each other?",
        "Compare your software development skills with your leadership abilities",
        "What are your strongest capabilities in both technical and business domains?"
    ]
    for query in queries:
        response = await capability_agent.chat(query)
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0
        print(f"\nResponse to complex query: {response}")

@pytest.mark.asyncio
async def test_real_world_job_matching(capability_agent):
    """Test matching capabilities against a real job posting"""
    job_posting = """
    Senior Software Engineer - AI/ML Platform
    
    Required Qualifications:
    - 5+ years of experience in Python development
    - Strong experience with cloud platforms (AWS/GCP/Azure)
    - Experience building and deploying ML models
    - Proficiency in modern software development practices (CI/CD, TDD, Agile)
    - Experience with containerization (Docker, Kubernetes)
    
    Preferred Qualifications:
    - Experience with LangChain, OpenAI APIs, or similar LLM frameworks
    - Background in building scalable distributed systems
    - Experience leading technical teams
    - Strong communication and project management skills
    - Experience with real-time data processing
    """
    response = await capability_agent.chat(f"How well do I match this job posting? Please analyze in detail: {job_posting}")
    assert response is not None
    assert isinstance(response, str)
    print(f"\nJob matching analysis:\n{response}")

@pytest.mark.asyncio
async def test_strategy_integration(capability_agent):
    """Test that strategy is properly integrated into responses"""
    response = await capability_agent.chat("What is your approach to problem-solving?")
    strategy = await capability_agent.profile_manager.get_strategy()
    assert any(keyword in response.lower() for keyword in strategy['content'].lower().split()[:5])

# ============= Error Handling & Edge Cases =============

@pytest.mark.asyncio
async def test_error_handling(capability_agent):
    """Test handling of invalid inputs and edge cases"""
    edge_cases = [
        "",  # Empty string
        "   ",  # Whitespace
        "skills that don't exist",  # Non-existent skills
        "!@#$%^",  # Special characters
        "a" * 1000  # Very long input
    ]
    for case in edge_cases:
        response = await capability_agent.chat(case)
        assert response is not None
        assert isinstance(response, str)
        print(f"\nResponse to edge case '{case[:20]}...': {response}")

@pytest.mark.asyncio
async def test_error_recovery(capability_agent):
    """Test agent's ability to recover from errors"""
    with patch.object(capability_agent.profile_manager, 'get_capabilities', 
                     side_effect=Exception("Simulated error")):
        response = await capability_agent.chat("What are your capabilities?")
        # Check for either "error" or "issue" in the response
        assert any(word in response.lower() for word in ["error", "issue"])
        
        # Test a different tool (generate_skill_summary) which isn't mocked to fail
        with patch.object(capability_agent.profile_manager, 'generate_skill_summary', 
                         return_value={"summary": "Test summary of skills"}):
            response = await capability_agent.chat("Give me a brief summary of your skills")
            assert response is not None
            assert not any(word in response.lower() for word in ["error", "issue"])

@pytest.mark.asyncio
async def test_timeout_handling(capability_agent):
    """Test timeout handling in async operations"""
    async def slow_operation(*args, **kwargs):
        await asyncio.sleep(2)  # Simulate slow operation
        return "Slow response"
    
    with patch.object(capability_agent.profile_manager, 'get_capabilities', 
                     side_effect=slow_operation):
        response = await capability_agent.chat(
            "What are your capabilities?", 
            timeout=0.1  # Shorter timeout for faster test
        )
        # Test for the exact timeout message
        assert response == "Operation timed out. Please try again."

# ============= Lifecycle Tests =============

@pytest.mark.asyncio
async def test_graceful_shutdown(capability_agent):
    """Test graceful shutdown of agent"""
    await capability_agent.chat("Hello")
    await capability_agent.shutdown()
    response = await capability_agent.chat("Should still work but might warn about shutdown")
    assert response is not None
