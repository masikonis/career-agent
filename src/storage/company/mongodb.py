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

    def __init__(self, config: Dict):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(config["MONGODB_URI"])
            self.db: Database = self.client[config["MONGODB_DB_NAME"]]
            self.companies = self.db.companies

            # Create indexes
            self.companies.create_index("name")
            self.companies.create_index("industry")
            self.companies.create_index("stage")

            logger.info(f"Connected to MongoDB database: {config['MONGODB_DB_NAME']}")
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
