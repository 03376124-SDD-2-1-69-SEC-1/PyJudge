"""Runnable reference implementation for a small Core API module."""

from greader.core.topics.models import Topic
from greader.core.topics.ports import TopicRepository
from greader.core.topics.service import TopicService

__all__ = ["Topic", "TopicRepository", "TopicService"]
