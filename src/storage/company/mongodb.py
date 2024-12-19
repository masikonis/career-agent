from datetime import datetime
from typing import Dict, List, Optional

from bson import ObjectId
from pymongo import MongoClient
from pymongo.database import Database

from src.utils.logger import get_logger

from ..base.exceptions import EntityNotFoundError, StorageError
from ..base.types import EntityID
from .interfaces import CompanyStorage
from .types import Company, CompanyEvaluation

logger = get_logger(__name__)


class MongoDBCompanyStorage(CompanyStorage):
    """MongoDB implementation of company storage"""

    def __init__(self, config: Dict, is_test: bool = False):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(config["MONGODB_URI"])
            self.db: Database = self.client[config["MONGODB_DB_NAME"]]
            self.companies = self.db.companies
            self.collection = self.db["companies"]

            # Create indexes
            self.companies.create_index("name")
            self.companies.create_index("industry")
            self.companies.create_index("stage")

            # Use test database if is_test is True
            self.db_name = "career-crew-test" if is_test else "career-crew"
            self.db = self.client[self.db_name]
            self.collection = self.db["companies"]

            logger.info(f"Connected to MongoDB database: {self.db_name}")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
            raise StorageError(f"MongoDB initialization failed: {str(e)}")

    async def create(self, company: Company) -> EntityID:
        """Create a new company in storage"""
        try:
            doc = self._to_document(company)
            result = self.companies.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to create company: {str(e)}")
            raise StorageError(f"Company creation failed: {str(e)}")

    async def read(self, entity_id: EntityID) -> Optional[Company]:
        """Retrieve a company by ID"""
        try:
            doc = self.companies.find_one({"_id": ObjectId(entity_id)})
            return self._from_document(doc) if doc else None
        except Exception as e:
            logger.error(f"Failed to read company {entity_id}: {str(e)}")
            raise StorageError(f"Company read failed: {str(e)}")

    async def update(self, entity_id: EntityID, company: Company) -> bool:
        """Update an existing company"""
        try:
            doc = self._to_document(company)
            result = self.companies.update_one(
                {"_id": ObjectId(entity_id)}, {"$set": doc}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update company {entity_id}: {str(e)}")
            raise StorageError(f"Company update failed: {str(e)}")

    async def delete(self, entity_id: EntityID) -> bool:
        """Delete a company"""
        try:
            result = self.companies.delete_one({"_id": ObjectId(entity_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete company {entity_id}: {str(e)}")
            raise StorageError(f"Company deletion failed: {str(e)}")

    def _to_document(self, company: Company) -> Dict:
        """Convert Company object to MongoDB document"""
        return {
            "name": company.name,
            "description": company.description,
            "industry": company.industry.value,
            "stage": company.stage.value,
            "website": company.website,
            "evaluations": [
                self._evaluation_to_dict(e) for e in (company.evaluations or [])
            ],
            "created_at": company.created_at,
            "updated_at": company.updated_at,
        }

    def _from_document(self, doc: Dict) -> Company:
        """Convert MongoDB document to Company object"""
        return Company(
            id=str(doc["_id"]),
            name=doc["name"],
            description=doc["description"],
            industry=doc["industry"],
            stage=doc["stage"],
            website=doc.get("website"),
            evaluations=[
                self._dict_to_evaluation(e) for e in doc.get("evaluations", [])
            ],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    def _evaluation_to_dict(self, eval: CompanyEvaluation) -> Dict:
        """Convert CompanyEvaluation to dictionary"""
        return {
            "match_score": eval.match_score,
            "skills_match": eval.skills_match,
            "notes": eval.notes,
            "evaluated_at": eval.evaluated_at,
        }

    def _dict_to_evaluation(self, data: Dict) -> CompanyEvaluation:
        """Convert dictionary to CompanyEvaluation"""
        return CompanyEvaluation(
            match_score=data["match_score"],
            skills_match=data["skills_match"],
            notes=data.get("notes"),
            evaluated_at=data["evaluated_at"],
        )

    async def add_evaluation(
        self, company_id: EntityID, evaluation: CompanyEvaluation
    ) -> bool:
        """Add an evaluation to a company"""
        try:
            # Convert evaluation to dict
            eval_dict = {
                "match_score": evaluation.match_score,
                "skills_match": evaluation.skills_match,
                "notes": evaluation.notes,
                "evaluated_at": evaluation.evaluated_at or datetime.now(),
            }

            # Add to evaluations array
            result = self.companies.update_one(
                {"_id": ObjectId(company_id)}, {"$push": {"evaluations": eval_dict}}
            )

            if result.modified_count > 0:
                logger.info(f"Added evaluation to company {company_id}")
                return True
            else:
                logger.error(f"Company {company_id} not found")
                return False

        except Exception as e:
            logger.error(f"Failed to add evaluation to company {company_id}: {str(e)}")
            return False

    async def cleanup_test_data(self) -> None:
        """Clean up test data from MongoDB - only used in test environment"""
        if not self.db_name.endswith("-test"):
            logger.warning("Attempted to cleanup non-test database! Aborting.")
            return None

        try:
            result = self.collection.delete_many({})
            logger.info(f"Successfully cleaned up test documents from MongoDB")
        except Exception as e:
            logger.error(f"Failed to cleanup test data: {str(e)}")

        return None  # Explicit return
