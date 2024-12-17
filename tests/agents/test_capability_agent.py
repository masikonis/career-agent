import pytest
from src.agents.capability_agent import CapabilityAgent
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
async def test_category_queries(capability_agent):
    """Test querying different capability categories"""
    categories = ['Hard Skills', 'Soft Skills', 'Domain Knowledge', 'Tools/Platforms']
    for category in categories:
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
    
    Responsibilities:
    - Design and implement AI/ML infrastructure components
    - Lead technical discussions and architecture decisions
    - Mentor junior engineers and contribute to team growth
    - Collaborate with cross-functional teams
    - Drive best practices in software development
    """
    
    # Test overall job match
    response = await capability_agent.chat(f"How well do I match this job posting? Please analyze in detail: {job_posting}")
    assert response is not None
    assert isinstance(response, str)
    print(f"\nJob matching analysis:\n{response}")
