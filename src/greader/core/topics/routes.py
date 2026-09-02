"""FastAPI adapter for the Topic reference API."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from greader.core.topics.models import Topic
from greader.core.topics.schemas import TopicCreate, TopicReplace, TopicResponse
from greader.core.topics.service import (
    TopicNameConflictError,
    TopicNotFoundError,
    TopicService,
)

router = APIRouter(prefix="/api/v1/topics", tags=["topics"])


def _service(request: Request) -> TopicService:
    return request.app.state.topic_service


def _response(topic: Topic) -> TopicResponse:
    return TopicResponse(id=topic.id, name=topic.name, description=topic.description)


def _raise_not_found() -> None:
    raise HTTPException(status_code=404, detail={"code": "topic_not_found"})


def _raise_name_conflict() -> None:
    raise HTTPException(status_code=409, detail={"code": "topic_name_conflict"})


@router.post("", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(request: Request, payload: TopicCreate) -> TopicResponse:
    """Create a reusable Topic."""
    try:
        return _response(
            _service(request).create(
                name=payload.name,
                description=payload.description,
            )
        )
    except TopicNameConflictError:
        _raise_name_conflict()


@router.get("", response_model=list[TopicResponse])
def list_topics(request: Request) -> list[TopicResponse]:
    """List every Topic in deterministic name order."""
    return [_response(topic) for topic in _service(request).list()]


@router.get("/{topic_id}", response_model=TopicResponse)
def get_topic(request: Request, topic_id: str) -> TopicResponse:
    """Get one Topic."""
    try:
        return _response(_service(request).get(topic_id))
    except TopicNotFoundError:
        _raise_not_found()


@router.put("/{topic_id}", response_model=TopicResponse)
def replace_topic(
    request: Request,
    topic_id: str,
    payload: TopicReplace,
) -> TopicResponse:
    """Replace one Topic."""
    try:
        return _response(
            _service(request).replace(
                topic_id=topic_id,
                name=payload.name,
                description=payload.description,
            )
        )
    except TopicNotFoundError:
        _raise_not_found()
    except TopicNameConflictError:
        _raise_name_conflict()


@router.delete("/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(request: Request, topic_id: str) -> Response:
    """Delete one Topic."""
    try:
        _service(request).delete(topic_id)
    except TopicNotFoundError:
        _raise_not_found()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
