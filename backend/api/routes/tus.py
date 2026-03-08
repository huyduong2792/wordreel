"""
TUS upload endpoint for chunked uploads
"""
from fastapi import APIRouter, HTTPException, Header, Request, Response
from typing import Optional
import structlog
from services.tus_client import get_tus_client

router = APIRouter()
logger = structlog.get_logger()


@router.options("/")
async def tus_options():
    """TUS protocol OPTIONS endpoint"""
    return Response(
        headers={
            "Tus-Resumable": "1.0.0",
            "Tus-Version": "1.0.0",
            "Tus-Extension": "creation,termination,checksum",
            "Tus-Max-Size": "104857600"
        }
    )


@router.post("/")
async def create_tus_upload(
    request: Request,
    upload_length: int = Header(..., alias="Upload-Length"),
    upload_metadata: Optional[str] = Header(None, alias="Upload-Metadata")
):
    """Create a new TUS upload"""
    try:
        tus_client = get_tus_client()
        
        # Parse metadata
        metadata = {}
        if upload_metadata:
            for item in upload_metadata.split(","):
                parts = item.strip().split(" ", 1)
                if len(parts) == 2:
                    key, value = parts
                    import base64
                    metadata[key] = base64.b64decode(value).decode()
        
        filename = metadata.get("filename", "unnamed.mp4")
        
        # Create upload on TUS server
        upload_url = await tus_client.create_upload(
            file_size=upload_length,
            filename=filename,
            metadata=metadata
        )
        
        return Response(
            status_code=201,
            headers={
                "Location": upload_url,
                "Tus-Resumable": "1.0.0"
            }
        )
        
    except Exception as e:
        logger.error("Failed to create TUS upload", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create upload: {str(e)}"
        )


@router.head("/{upload_id}")
async def get_upload_offset(upload_id: str):
    """Get current upload offset"""
    try:
        tus_client = get_tus_client()
        
        # Construct upload URL
        upload_url = f"{tus_client.server_url}/{upload_id}"
        
        # Get offset
        offset = await tus_client.get_upload_offset(upload_url)
        
        return Response(
            headers={
                "Upload-Offset": str(offset),
                "Tus-Resumable": "1.0.0"
            }
        )
        
    except Exception as e:
        logger.error("Failed to get upload offset", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get offset: {str(e)}"
        )


@router.patch("/{upload_id}")
async def upload_chunk(
    upload_id: str,
    request: Request,
    upload_offset: int = Header(..., alias="Upload-Offset"),
    content_type: str = Header(..., alias="Content-Type")
):
    """Upload a chunk"""
    try:
        # Validate content type
        if content_type != "application/offset+octet-stream":
            raise HTTPException(
                status_code=400,
                detail="Content-Type must be application/offset+octet-stream"
            )
        
        tus_client = get_tus_client()
        
        # Construct upload URL
        upload_url = f"{tus_client.server_url}/{upload_id}"
        
        # Read chunk data
        chunk_data = await request.body()
        
        # Upload chunk
        new_offset = await tus_client.upload_chunk(
            upload_url=upload_url,
            chunk_data=chunk_data,
            offset=upload_offset
        )
        
        return Response(
            status_code=204,
            headers={
                "Upload-Offset": str(new_offset),
                "Tus-Resumable": "1.0.0"
            }
        )
        
    except Exception as e:
        logger.error("Failed to upload chunk", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload chunk: {str(e)}"
        )
