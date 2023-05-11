from fastapi import APIRouter, Depends, Security
from fastapi.responses import HTMLResponse
from typing import Annotated
from uuid import UUID
from worst_crm import db
from worst_crm.models import (
    Note,
    NewNote,
    NoteInfo,
    NoteInfoForProject,
    UpdatedNote,
    NoteInDB,
    User,
)
import json
import worst_crm.dependencies as dep

router = APIRouter(
    prefix="/notes",
    dependencies=[Depends(dep.get_current_user)],
    tags=["notes"],
)


# CRUD
@router.get("/{account_id}")
async def get_all_notes(
    account_id: UUID,
) -> list[NoteInfo]:
    return db.get_all_notes(account_id)


@router.get("/{account_id}/{project_id}")
async def get_all_notes_for_project_id(
    account_id: UUID, project_id: UUID
) -> list[NoteInfoForProject]:
    return db.get_all_notes_for_project_id(account_id, project_id)


@router.get("/{account_id}/{project_id}/{note_id}")
async def get_note(account_id: UUID, project_id: UUID, note_id: int) -> Note | None:
    return db.get_note(account_id, project_id, note_id)


@router.post(
    "/{account_id}/{project_id}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def create_note(
    account_id: UUID,
    project_id: UUID,
    note: NewNote,
    current_user: Annotated[User, Depends(dep.get_current_user)],
) -> Note | None:
    note_in_db = NoteInDB(
        **note.dict(), created_by=current_user.user_id, updated_by=current_user.user_id
    )

    return db.create_note(account_id, project_id, note_in_db)


@router.put(
    "/{account_id}/{project_id}/{note_id}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def update_note(
    account_id: UUID,
    project_id: UUID,
    note_id: int,
    note: UpdatedNote,
    current_user: Annotated[User, Depends(dep.get_current_user)],
) -> Note | None:
    note_in_db = NoteInDB(
        **note.dict(exclude={"data"}),
        data=json.dumps(note.data),
        updated_by=current_user.user_id
    )

    return db.update_note(account_id, project_id, note_id, note_in_db)


@router.delete(
    "/{account_id}/{project_id}/{note_id}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def delete_note(account_id: UUID, project_id: UUID, note_id: int) -> Note | None:
    return db.delete_note(account_id, project_id, note_id)


# Attachments
@router.get(
    "/{account_id}/{project_id}/{note_id}/presigned-get-url/{filename}",
    name="Get pre-signed URL for downloading an attachment",
)
async def get_presigned_get_url(
    account_id: UUID, project_id: UUID, note_id: int, filename: str
):
    s3_object_name = (
        str(account_id) + "/" + str(project_id) + "/" + str(note_id) + "/" + filename
    )
    data = dep.get_presigned_get_url(s3_object_name)
    return HTMLResponse(content=data)


@router.get(
    "/{account_id}/{project_id}/{note_id}/presigned-put-url/{filename}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
    name="Get pre-signed URL for uploading an attachment",
)
async def get_presigned_put_url(
    account_id: UUID, project_id: UUID, note_id: int, filename: str
):
    s3_object_name = (
        str(account_id) + "/" + str(project_id) + "/" + str(note_id) + "/" + filename
    )
    db.add_note_attachment(account_id, project_id, note_id, filename)
    data = dep.get_presigned_put_url(s3_object_name)
    return HTMLResponse(content=data)


@router.delete(
    "/{account_id}/{project_id}/{note_id}/attachments/{filename}",
    dependencies=[Security(dep.get_current_user, scopes=["rw"])],
)
async def delete_attachement(
    account_id: UUID, project_id: UUID, note_id: int, filename: str
):
    s3_object_name = (
        str(account_id) + "/" + str(project_id) + "/" + str(note_id) + "/" + filename
    )
    db.remove_note_attachment(account_id, project_id, note_id, filename)
    dep.s3_remove_object(s3_object_name)
