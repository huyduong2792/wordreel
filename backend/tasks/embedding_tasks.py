"""
Celery tasks for generating embeddings for posts
"""
from celery_app import celery_app
from database.supabase_client import get_service_supabase
from services.container import get_embedding_service, get_quiz_generator
import structlog

logger = structlog.get_logger()


@celery_app.task(max_retries=3, default_retry_delay=60)
def generate_post_embedding_task(post_id: str):
    """
    Generate embedding for any post type (slides, quiz, etc.)
    Uses title, description, and tags to create embedding.
    """
    supabase = get_service_supabase()
    embedding_service = get_embedding_service()
    quiz_generator = get_quiz_generator()
    
    try:
        logger.info("Generating embedding for post", post_id=post_id)
        
        # Get post data
        response = supabase.table("posts").select(
            "id, title, description, content_type, tags, slides"
        ).eq("id", post_id).execute()
        
        if not response.data:
            logger.error("Post not found", post_id=post_id)
            return {"status": "error", "message": "Post not found"}
        
        post = response.data[0]
        title = post.get("title", "")
        description = post.get("description", "") or ""
        content_type = post.get("content_type", "")
        existing_tags = post.get("tags", [])
        
        # Build text content for embedding
        text_content = f"{title}\n{description}"
        
        # For slides, include captions
        if content_type == "image_slides" and post.get("slides"):
            captions = [
                slide.get("caption", "")
                for slide in post["slides"]
                if slide.get("caption")
            ]
            text_content += "\n" + "\n".join(captions)
        
        # For quiz, get questions text
        if content_type == "quiz":
            quiz_response = supabase.table("quizzes").select(
                "questions"
            ).eq("post_id", post_id).execute()
            
            if quiz_response.data:
                questions = quiz_response.data[0].get("questions", [])
                question_texts = [q.get("question", "") for q in questions]
                text_content += "\n" + "\n".join(question_texts)
        
        # Extract tags if not already present
        tags = existing_tags
        if not tags and len(text_content) > 50:
            import asyncio
            tags = asyncio.run(quiz_generator.extract_tags(text_content, title))
            
            # Update tags in database
            if tags:
                supabase.table("posts").update({"tags": tags}).eq(
                    "id", post_id
                ).execute()
                logger.info("Tags extracted", post_id=post_id, tags=tags)
        
        # Generate embedding
        import asyncio
        embedding = asyncio.run(embedding_service.generate_video_embedding(
            title=title,
            transcript=text_content,
            tags=tags
        ))
        
        # Update post with embedding
        supabase.table("posts").update({
            "embedding": embedding
        }).eq("id", post_id).execute()
        
        logger.info(
            "Embedding generated for post",
            post_id=post_id,
            content_type=content_type,
            dimensions=len(embedding) if embedding else 0
        )
        
        return {
            "status": "success",
            "post_id": post_id,
            "content_type": content_type
        }
        
    except Exception as e:
        logger.error("Failed to generate embedding", post_id=post_id, error=str(e))
        raise

