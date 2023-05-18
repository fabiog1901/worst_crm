from fastapi import APIRouter, Depends, Security, Query
from fastapi.responses import HTMLResponse
from typing import Annotated
from uuid import UUID
import datetime as dt
from worst_crm import db
from worst_crm.models import (
    Task,
    NewTask,
    TaskFilters,
    UpdatedTask,
    TaskInDB,
    TaskOverview,
    TaskOverviewWithProjectName,
    User,
)
import json
import worst_crm.dependencies as dep

router = APIRouter(
    prefix="/tasks",
    dependencies=[Depends(dep.get_current_user)],
    tags=["tasks"],
)


# CRUD
@router.get("/{account_id}")
async def get_all_tasks_for_account_id(
    account_id: UUID,
    name: Annotated[list[str], Query()] = [],
    owned_by: Annotated[list[str], Query()] = [],
    due_date_from: dt.date | None = None,
    due_date_to: dt.date | None = None,
    status: Annotated[list[str], Query()] = [],
    tags: Annotated[list[str], Query()] = [],
    attachments: Annotated[list[str], Query()] = [],
    created_at_from: dt.date | None = None,
    created_at_to: dt.date | None = None,
    created_by: Annotated[list[str], Query()] = [],
    updated_at_from: dt.date | None = None,
    updated_at_to: dt.date | None = None,
    updated_by: Annotated[list[str], Query()] = [],
) -> list[TaskOverviewWithProjectName]:
    # TODO possibly using elasticsearch for text/data columns?

    task_filters = TaskFilters()

    if name:
        task_filters.name = name
    if owned_by:
        task_filters.owned_by = owned_by
    if due_date_from:
        task_filters.due_date_from = due_date_from
    if due_date_to:
        task_filters.due_date_to = due_date_to
    if status:
        task_filters.status = status
    if tags:
        task_filters.tags = tags
    if attachments:
        task_filters.attachments = attachments
    if created_at_from:
        task_filters.created_at_from = created_at_from
    if created_at_to:
        task_filters.created_at_to = created_at_to
    if created_by:
        task_filters.created_by = created_by
    if updated_at_from:
        task_filters.updated_at_from = updated_at_from
    if updated_at_to:
        task_filters.updated_at_to = updated_at_to
    if updated_by:
        task_filters.updated_by = updated_by

    return db.get_all_tasks_for_account_id(account_id, task_filters)


@router.get("/{account_id}/{project_id}")
async def get_all_tasks_for_project_id(
    account_id: UUID, project_id: UUID
) -> list[TaskOverview]:
    return db.get_all_tasks_for_project_id(account_id, project_id)


@router.get("/{account_id}/{project_id}/{task_id}")
async def get_task(account_id: UUID, project_id: UUID, task_id: int) -> Task | None:
    return db.get_task(account_id, project_id, task_id)


@router.post(
    "/{account_id}/{project_id}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def create_task(
    account_id: UUID,
    project_id: UUID,
    current_user: Annotated[User, Depends(dep.get_current_user)],
) -> NewTask | None:
    task_in_db = TaskInDB(
        created_by=current_user.user_id, updated_by=current_user.user_id
    )  # type: ignore

    return db.create_task(account_id, project_id, task_in_db)


@router.put(
    "/{account_id}/{project_id}/{task_id}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def update_task(
    account_id: UUID,
    project_id: UUID,
    task_id: int,
    task: UpdatedTask,
    current_user: Annotated[User, Depends(dep.get_current_user)],
) -> Task | None:
    task_in_db = TaskInDB(
        **task.dict(exclude={"data"}),
        data=json.dumps(task.data),
        updated_by=current_user.user_id
    )

    return db.update_task(account_id, project_id, task_id, task_in_db)


@router.delete(
    "/{account_id}/{project_id}/{task_id}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def delete_task(account_id: UUID, project_id: UUID, task_id: int) -> Task | None:
    return db.delete_task(account_id, project_id, task_id)


# Attachments
@router.get(
    "/{account_id}/{project_id}/{task_id}/presigned-get-url/{filename}",
    name="Get pre-signed URL for downloading an attachment",
)
async def get_presigned_get_url(
    account_id: UUID, project_id: UUID, task_id: int, filename: str
):
    s3_object_name = (
        str(account_id) + "/" + str(project_id) + "/" + str(task_id) + "/" + filename
    )
    data = dep.get_presigned_get_url(s3_object_name)
    return HTMLResponse(content=data)


@router.get(
    "/{account_id}/{project_id}/{task_id}/presigned-put-url/{filename}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
    name="Get pre-signed URL for uploading an attachment",
)
async def get_presigned_put_url(
    account_id: UUID, project_id: UUID, task_id: int, filename: str
):
    s3_object_name = (
        str(account_id) + "/" + str(project_id) + "/" + str(task_id) + "/" + filename
    )
    db.add_task_attachment(account_id, project_id, task_id, filename)
    data = dep.get_presigned_put_url(s3_object_name)
    return HTMLResponse(content=data)


@router.delete(
    "/{account_id}/{project_id}/{task_id}/attachments/{filename}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def delete_attachement(
    account_id: UUID, project_id: UUID, task_id: int, filename: str
):
    s3_object_name = (
        str(account_id) + "/" + str(project_id) + "/" + str(task_id) + "/" + filename
    )
    db.remove_task_attachment(account_id, project_id, task_id, filename)
    dep.s3_remove_object(s3_object_name)
