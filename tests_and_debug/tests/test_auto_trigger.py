"""Unit/Integration tests for workflow auto-trigger after artwork upload."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.artwork import Artwork, ArtworkStatus
from backend.models.workflow_run import WorkflowRun, WorkflowStatus
from backend.services.artwork_service import ArtworkService
from backend.storage.base import StorageBackend, StorageResult


@pytest.fixture
def mock_storage() -> MagicMock:
    """Mock storage backend provider."""
    storage = MagicMock(spec=StorageBackend)
    storage.save = AsyncMock(
        return_value=StorageResult(
            path="artworks/mock.png",
            url="http://mock-storage/artworks/mock.png",
            size=1024,
            content_type="image/png",
        )
    )
    return storage


@pytest.mark.asyncio
async def test_auto_trigger_workflow_success(
    mock_db_session: AsyncSession,
    mock_storage: MagicMock,
) -> None:
    """Test that upload_artwork successfully starts the workflow."""
    service = ArtworkService(session=mock_db_session, storage=mock_storage)

    artwork_id = uuid.uuid4()
    mock_artwork = Artwork(
        id=artwork_id,
        title="Test Art",
        original_filename="art.png",
        file_path="artworks/mock.png",
        storage_url="http://mock-storage/artworks/mock.png",
        file_size=1024,
        mime_type="image/png",
        status=ArtworkStatus.UPLOADED,
        image_hash="fakehash",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        workflow_runs=[],
    )

    workflow_run_id = uuid.uuid4()
    mock_workflow_run = WorkflowRun(
        id=workflow_run_id,
        artwork_id=artwork_id,
        workflow_version="v1",
        status=WorkflowStatus.PENDING,
        celery_task_id="mock-celery-id",
    )

    # Mock DB operations
    service._repo.filter_by = AsyncMock(return_value=[])
    service._repo.create = AsyncMock(return_value=mock_artwork)
    service._workflow_repo.create = AsyncMock(return_value=mock_workflow_run)
    service._workflow_repo.update = AsyncMock(return_value=mock_workflow_run)

    # Mock the execute_workflow task dispatch
    with patch("backend.tasks.workflow_task.execute_workflow.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "mock-celery-id"
        mock_delay.return_value = mock_task

        response = await service.upload_artwork(
            file_data=b"mock-image-bytes",
            filename="art.png",
            content_type="image/png",
            title="Test Art",
        )

        # Assert task was dispatched with correct args
        mock_delay.assert_called_once_with(
            str(workflow_run_id),
            str(artwork_id),
            "v1",
        )

        # Assert WorkflowRun database records were created
        service._workflow_repo.create.assert_called_once()
        service._workflow_repo.update.assert_called_once_with(
            workflow_run_id,
            celery_task_id="mock-celery-id",
        )

        # Assert response contains trigger details
        assert response.workflow_run_id == workflow_run_id
        assert response.celery_task_id == "mock-celery-id"
