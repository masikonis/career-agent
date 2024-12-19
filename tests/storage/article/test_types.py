from datetime import datetime

import pytest

from src.storage.article.types import Article, ArticleFilters
from src.storage.base.types import EntityID


def test_article_creation():
    """Test basic article creation with required fields"""
    article = Article(
        title="Test Article",
        content="This is test content",
        author="Test Author",
        source="Test Source",
        published_at=datetime.now(),
    )

    assert article.title == "Test Article"
    assert article.content == "This is test content"
    assert article.author == "Test Author"
    assert article.source == "Test Source"
    assert article.tags == []  # Default empty list
    assert article.url is None  # Default None
    assert article.id is None  # Default None


def test_article_with_optional_fields():
    """Test article creation with all optional fields"""
    now = datetime.now()
    article = Article(
        title="Test Article",
        content="This is test content",
        author="Test Author",
        source="Test Source",
        published_at=now,
        tags=["tag1", "tag2"],
        url="https://test.com",
        id=EntityID("123"),
    )

    assert article.tags == ["tag1", "tag2"]
    assert article.url == "https://test.com"
    assert article.id == EntityID("123")


def test_article_validation():
    """Test article validation rules"""
    # Valid article
    article = Article(
        title="Test Article",
        content="This is test content",
        author="Test Author",
        source="Test Source",
        published_at=datetime.now(),
    )
    assert article.validate() is True

    # Invalid - empty title
    invalid_article = Article(
        title="",
        content="This is test content",
        author="Test Author",
        source="Test Source",
        published_at=datetime.now(),
    )
    assert invalid_article.validate() is False

    # Invalid - empty content
    invalid_article = Article(
        title="Test Article",
        content="",
        author="Test Author",
        source="Test Source",
        published_at=datetime.now(),
    )
    assert invalid_article.validate() is False


def test_article_to_dict():
    """Test article serialization to dictionary"""
    now = datetime.now()
    article = Article(
        title="Test Article",
        content="This is test content",
        author="Test Author",
        source="Test Source",
        published_at=now,
        tags=["tag1", "tag2"],
        url="https://test.com",
        id=EntityID("123"),
    )

    article_dict = article.to_dict()
    assert article_dict["title"] == "Test Article"
    assert article_dict["content"] == "This is test content"
    assert article_dict["author"] == "Test Author"
    assert article_dict["source"] == "Test Source"
    assert article_dict["published_at"] == now.isoformat()
    assert article_dict["tags"] == ["tag1", "tag2"]
    assert article_dict["url"] == "https://test.com"
    assert article_dict["id"] == "123"


def test_article_from_dict():
    """Test article deserialization from dictionary"""
    now = datetime.now()
    article_dict = {
        "title": "Test Article",
        "content": "This is test content",
        "author": "Test Author",
        "source": "Test Source",
        "published_at": now.isoformat(),
        "tags": ["tag1", "tag2"],
        "url": "https://test.com",
        "id": "123",
    }

    article = Article.from_dict(article_dict)
    assert article.title == "Test Article"
    assert article.content == "This is test content"
    assert article.author == "Test Author"
    assert article.source == "Test Source"
    assert article.published_at.isoformat() == now.isoformat()
    assert article.tags == ["tag1", "tag2"]
    assert article.url == "https://test.com"
    assert article.id == EntityID("123")


def test_article_filters():
    """Test ArticleFilters functionality"""
    now = datetime.now()
    filters = ArticleFilters(
        author="Test Author",
        source="Test Source",
        tags=["tag1", "tag2"],
        published_after=now,
        published_before=now,
    )

    filter_dict = filters.to_dict()
    assert filter_dict["author"] == "Test Author"
    assert filter_dict["source"] == "Test Source"
    assert filter_dict["tags"]["$in"] == ["tag1", "tag2"]
    assert filter_dict["published_at"]["$gte"] == now.isoformat()
    assert filter_dict["published_at"]["$lte"] == now.isoformat()


def test_get_search_text():
    """Test article search text generation"""
    article = Article(
        title="Test Article",
        content="This is test content",
        author="Test Author",
        source="Test Source",
        published_at=datetime.now(),
    )

    search_text = article.get_search_text()
    assert "Test Article" in search_text
    assert "This is test content" in search_text
