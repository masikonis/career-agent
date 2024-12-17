import pytest
from src.profile.notion import NotionProfileSource
from src.services.knowledge.notion import NotionKnowledge
from src.config.settings import config
import json

@pytest.fixture
def profile_source():
    """Fixture to create a NotionProfileSource instance"""
    notion_client = NotionKnowledge(config['NOTION_API_KEY'])
    return NotionProfileSource(notion_client)

@pytest.mark.asyncio
async def test_get_capabilities(profile_source):
    """Test fetching capabilities from Notion"""
    capabilities = await profile_source.get_capabilities()
    
    # Print the first capability for inspection with better formatting
    capability = capabilities[0]
    formatted_capability = {
        "name": capability["name"],
        "category": capability["category"],
        "level": capability["level"],
        "experience": capability["experience"][:100] + "..."  # Truncate for readability
    }
    
    print("\nFirst capability data:")
    print(json.dumps(formatted_capability, indent=2))
    
    # Basic response structure tests
    assert isinstance(capabilities, list)
    assert len(capabilities) > 0
    
    # Test first capability structure
    capability = capabilities[0]
    assert isinstance(capability, dict)
    
    # Check required fields exist and types
    assert 'name' in capability
    assert 'category' in capability
    assert 'level' in capability
    assert 'experience' in capability
    
    assert isinstance(capability['name'], str)
    assert isinstance(capability['category'], str)
    assert isinstance(capability['level'], str)
    assert isinstance(capability['experience'], str)

@pytest.mark.asyncio
async def test_capability_content(profile_source):
    """Test actual content of capabilities"""
    capabilities = await profile_source.get_capabilities()
    capability = capabilities[0]
    
    # Verify values are from expected sets
    assert capability['category'] in ['Technical', 'Leadership', 'Domain Knowledge', 'Soft Skills', 'Tools/Platforms']
    assert capability['level'] in ['Expert', 'Advanced', 'Intermediate', 'Basic']

@pytest.mark.asyncio
async def test_error_handling(profile_source):
    """Test handling of API errors"""
    profile_source.capabilities_db = "invalid_id"
    with pytest.raises(Exception):
        await profile_source.get_capabilities()
