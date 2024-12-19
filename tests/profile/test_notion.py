import json

import pytest

from src.config import config
from src.profile.notion import NotionProfileSource
from src.services.knowledge.notion import NotionKnowledge


@pytest.fixture
def profile_source():
    """Fixture to create a NotionProfileSource instance"""
    notion_client = NotionKnowledge(config["NOTION_API_KEY"])
    return NotionProfileSource(notion_client)


@pytest.mark.asyncio
async def test_get_strategy(profile_source):
    """Test fetching strategy from Notion"""
    strategy = await profile_source.get_strategy()

    # Print final content only, with proper formatting
    print("\nStrategy content:")
    print("-" * 80)
    print(strategy["content"])
    print("-" * 80)

    # Basic response structure tests
    assert isinstance(strategy, dict)
    assert "content" in strategy
    assert isinstance(strategy["content"], str)
    assert len(strategy["content"]) > 0


@pytest.mark.asyncio
async def test_capability_content(profile_source):
    """Test actual content of capabilities"""
    capabilities = await profile_source.get_capabilities()
    capability = capabilities[0]

    print("\nFirst capability data:")
    print(
        json.dumps(
            {
                "name": capability["name"],
                "category": capability["category"],
                "level": capability["level"],
                "experience": capability["experience"][:100]
                + "...",  # Truncate for readability
            },
            indent=2,
        )
    )

    # Verify values are from expected sets
    assert capability["category"] in [
        "Technical",
        "Leadership",
        "Domain Knowledge",
        "Soft Skills",
        "Tools/Platforms",
    ]
    assert capability["level"] in ["Expert", "Advanced", "Intermediate", "Basic"]


@pytest.mark.asyncio
async def test_capability_structure(profile_source):
    """Test structure of capabilities response"""
    capabilities = await profile_source.get_capabilities()

    # Basic response structure tests
    assert isinstance(capabilities, list)
    assert len(capabilities) > 0

    # Test first capability structure
    capability = capabilities[0]
    assert isinstance(capability, dict)
    assert all(key in capability for key in ["name", "category", "level", "experience"])


@pytest.mark.asyncio
async def test_capability_error_handling(profile_source):
    """Test handling of API errors for capabilities"""
    original_db = profile_source.capabilities_db
    try:
        profile_source.capabilities_db = "invalid_id"
        with pytest.raises(Exception):
            await profile_source.get_capabilities()
    finally:
        profile_source.capabilities_db = original_db


@pytest.mark.asyncio
async def test_strategy_error_handling(profile_source):
    """Test handling of API errors for strategy"""
    original_page = profile_source.strategy_page
    try:
        profile_source.strategy_page = "invalid_id"
        with pytest.raises(Exception):
            await profile_source.get_strategy()
    finally:
        profile_source.strategy_page = original_page
