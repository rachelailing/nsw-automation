"""Knowledge Pack inspection and review-first source import endpoints."""

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from db.knowledge_content import get_knowledge_content
from db.knowledge_packs import get_active_knowledge_pack
from db.supabase_client import get_client
from services.knowledge_ingestion import (
    extract_source_text,
    extract_structured_knowledge,
)


router = APIRouter()


def _list_sources(knowledge_pack_id: int) -> list[dict]:
    client = get_client()
    result = (
        client.table("knowledge_sources")
        .select(
            "id, source_name, source_type, original_filename, file_size_bytes, "
            "extraction_status, review_status, extracted_content, error_message, "
            "uploaded_by, reviewed_by, reviewed_at, created_at"
        )
        .eq("knowledge_pack_id", knowledge_pack_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


@router.get("/knowledge/active")
async def active_knowledge_pack():
    pack = await get_active_knowledge_pack()
    content = await get_knowledge_content(pack["id"])
    return {
        "pack": pack,
        "content": content,
        "sources": _list_sources(pack["id"]),
    }


@router.post("/knowledge/sources/import")
async def import_knowledge_source(file: UploadFile = File(...)):
    filename = Path(file.filename or "source").name
    raw_content = await file.read()
    pack = await get_active_knowledge_pack()
    client = get_client()

    source_name = f"{Path(filename).stem}-{uuid4().hex[:8]}"
    source_type = Path(filename).suffix.lower().removeprefix(".") or "unknown"
    source_row = {
        "knowledge_pack_id": pack["id"],
        "source_name": source_name,
        "source_type": source_type,
        "original_filename": filename,
        "file_size_bytes": len(raw_content),
        "checksum": hashlib.sha256(raw_content).hexdigest(),
        "extraction_status": "processing",
        "review_status": "pending_review",
        "uploaded_by": "prototype-user",
    }
    inserted = client.table("knowledge_sources").insert(source_row).execute()
    if not inserted.data:
        raise HTTPException(status_code=500, detail="Could not create the source record.")
    source = inserted.data[0]

    try:
        extracted_text, detected_type = extract_source_text(filename, raw_content)
        extracted_content = extract_structured_knowledge(extracted_text, detected_type)
        updated = (
            client.table("knowledge_sources")
            .update(
                {
                    "source_type": detected_type,
                    "extracted_text": extracted_text,
                    "extracted_content": extracted_content,
                    "extraction_status": "completed",
                    "error_message": None,
                }
            )
            .eq("id", source["id"])
            .execute()
        )
        return updated.data[0] if updated.data else {**source, "extracted_content": extracted_content}
    except Exception as exc:
        client.table("knowledge_sources").update(
            {
                "extraction_status": "failed",
                "error_message": str(exc),
            }
        ).eq("id", source["id"]).execute()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/knowledge/sources/{source_id}")
async def delete_knowledge_source(source_id: int):
    """Delete a failed or pending-review source from the active pack."""
    pack = await get_active_knowledge_pack()
    client = get_client()
    found = (
        client.table("knowledge_sources")
        .select("id, review_status, original_filename, source_name")
        .eq("id", source_id)
        .eq("knowledge_pack_id", pack["id"])
        .limit(1)
        .execute()
    )
    if not found.data:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")

    source = found.data[0]
    if source.get("review_status") == "approved":
        raise HTTPException(
            status_code=409,
            detail="Approved sources cannot be deleted because they are part of the audit trail.",
        )

    deleted = (
        client.table("knowledge_sources")
        .delete()
        .eq("id", source_id)
        .eq("knowledge_pack_id", pack["id"])
        .execute()
    )
    if not deleted.data:
        raise HTTPException(status_code=500, detail="The source could not be deleted.")

    return {
        "deleted": True,
        "source_id": source_id,
        "filename": source.get("original_filename") or source.get("source_name"),
    }
