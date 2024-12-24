from datetime import datetime

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.config import config
from src.repositories.models import Company, CompanyIndustry, CompanyStage
from src.services.scrapers.zenrows import ZenrowsScraper
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CompanyResearchAgent:
    """Agent that researches companies and prepares them for storage"""

    def __init__(self, llm=None, model_name=None):
        model = model_name or config["LLM_MODELS"]["advanced"]
        self.llm = llm or ChatOpenAI(temperature=0, model=model)
        self.scraper = ZenrowsScraper()
        logger.info(f"CompanyResearchAgent initialized with model: {model}")

    async def research(self, company_name: str, website: str) -> Company:
        """Research company and return structured Company data"""

        try:
            # Scrape website
            response = await self.scraper.scrape(website)
            if response.error:
                return f"Error scraping website: {response.error}"

            logger.info(f"Successfully scraped website: {website}")

            message = HumanMessage(
                content=f"""Analyze this company website and provide specific information in a structured way.
            Company Name: {company_name}
            Website: {website}
            
            HTML Content: {response.html}
            
            Please analyze and provide:
            1. A clear, concise description of what the company does (2-3 sentences)
            2. The company's industry (must be one of: SAAS, FINTECH, EDTECH, AI, MARKETPLACE, ENTERPRISE, OTHER)
            3. Company stage (must be one of: IDEA, PRE_SEED, MVP, SEED, EARLY, SERIES_A, LATER) - infer from their content
            4. A company fit score (0.0 to 1.0) based on:
               - Technology alignment (modern tech stack)
               - Growth potential
               - Market position
            
            Format your response as:
            DESCRIPTION: <description>
            INDUSTRY: <industry>
            STAGE: <stage>
            FIT_SCORE: <score>
            REASONING: <brief explanation of the fit score>"""
            )

            response = await self.llm.ainvoke([message])
            logger.info(f"Completed analysis for: {company_name}")

            # Parse the response and create Company object
            parsed = self._parse_llm_response(response.content)

            return Company(
                name=company_name,
                description=parsed["description"],
                industry=CompanyIndustry[parsed["industry"]],
                stage=CompanyStage[parsed["stage"]],
                website=website,
                company_fit_score=float(parsed["fit_score"]),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

        except Exception as e:
            logger.error(f"Error researching company {company_name}: {str(e)}")
            raise

    def _parse_llm_response(self, content: str) -> dict:
        """Parse the LLM response into structured data"""
        lines = content.split("\n")
        result = {}

        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "fit_score":
                    result["fit_score"] = float(value)
                elif key in ["description", "industry", "stage"]:
                    result[key] = value

        return result
