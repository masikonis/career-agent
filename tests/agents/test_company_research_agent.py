import pytest

from src.agents.company_research_agent import CompanyResearchAgent
from src.config import config
from src.repositories.models import Company


@pytest.fixture
def research_agent():
    """Create a CompanyResearchAgent instance for testing"""
    return CompanyResearchAgent(model_name=config["LLM_MODELS"]["basic"])


@pytest.mark.asyncio
async def test_company_research():
    """Test basic company research capabilities"""
    agent = CompanyResearchAgent()

    # Test with Learning Tapestry
    company = await agent.research(
        "Learning Tapestry", "https://www.learningtapestry.com/"
    )

    assert company is not None
    assert isinstance(company, Company)
    assert company.name == "Learning Tapestry"
    assert company.website == "https://www.learningtapestry.com/"
    assert company.description is not None
    assert company.industry is not None
    assert company.stage is not None
    assert isinstance(company.company_fit_score, float)
    assert 0 <= company.company_fit_score <= 1

    print("\nLearning Tapestry Research Results:")
    print("-" * 80)
    print(f"Name: {company.name}")
    print(f"Industry: {company.industry}")
    print(f"Stage: {company.stage}")
    print(f"Description: {company.description}")
    print(f"Fit Score: {company.company_fit_score}")
    print("-" * 80)
