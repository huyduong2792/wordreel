"""
Quiz API endpoints
Supports both legacy video_id and new post_id
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from models.schemas import (
    QuizResponse, QuizSubmission, QuizResult, QuizQuestion
)
from database.supabase_client import get_supabase
from auth.utils import get_current_user, get_current_user_optional
from services.container import get_quiz_generator

router = APIRouter()


@router.get("/post/{post_id}", response_model=QuizResponse)
async def get_post_quiz(
    post_id: str,
    current_user = Depends(get_current_user_optional)  # Made optional for public access
):
    """Get quiz for a post (any content type)"""
    supabase = get_supabase()
    
    try:
        response = supabase.table("quizzes").select("*").eq(
            "post_id", post_id
        ).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        quiz_data = response.data[0]
        questions = [QuizQuestion(**q) for q in quiz_data["questions"]]
        quiz_data["questions"] = questions
        
        return QuizResponse(**quiz_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quiz: {str(e)}"
        )


# Legacy endpoint for backward compatibility
@router.get("/{video_id}", response_model=QuizResponse)
async def get_quiz(
    video_id: str,
    current_user = Depends(get_current_user_optional)  # Made optional for public access
):
    """Get quiz for a video (legacy - use /post/{post_id} instead)"""
    return await get_post_quiz(video_id, current_user)


@router.post("/submit", response_model=QuizResult)
async def submit_quiz(
    submission: QuizSubmission,
    current_user = Depends(get_current_user)
):
    """Submit quiz answers and get results"""
    supabase = get_supabase()
    quiz_generator = get_quiz_generator()
    
    try:
        quiz_response = supabase.table("quizzes").select("*").eq(
            "id", submission.quiz_id
        ).execute()
        
        if not quiz_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quiz not found"
            )
        
        quiz_data = quiz_response.data[0]
        questions = [QuizQuestion(**q) for q in quiz_data["questions"]]
        
        result = quiz_generator.evaluate_answers(questions, submission.answers)
        
        result_data = {
            "user_id": current_user.id,
            "quiz_id": submission.quiz_id,
            "post_id": quiz_data["post_id"],
            "score": result["score"],
            "total_points": result["total_points"],
            "percentage": result["percentage"],
            "passed": result["passed"],
            "answers": submission.answers,
            "details": result["details"]
        }
        
        supabase.table("quiz_results").insert(result_data).execute()
        
        return QuizResult(
            quiz_id=submission.quiz_id,
            **result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit quiz: {str(e)}"
        )


@router.get("/results/post/{post_id}", response_model=List[QuizResult])
async def get_post_quiz_results(
    post_id: str,
    current_user = Depends(get_current_user)
):
    """Get user's quiz results for a post"""
    supabase = get_supabase()
    
    try:
        response = supabase.table("quiz_results").select("*").eq(
            "post_id", post_id
        ).eq("user_id", current_user.id).order(
            "created_at", desc=True
        ).execute()
        
        results = []
        for result_data in response.data:
            results.append(QuizResult(
                quiz_id=result_data["quiz_id"],
                score=result_data["score"],
                total_points=result_data["total_points"],
                percentage=result_data["percentage"],
                correct_answers=sum(
                    1 for d in result_data["details"] if d.get("is_correct")
                ),
                total_questions=len(result_data["details"]),
                passed=result_data["passed"],
                details=result_data["details"]
            ))
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get quiz results: {str(e)}"
        )


# Legacy endpoint
@router.get("/results/{video_id}", response_model=List[QuizResult])
async def get_quiz_results(
    video_id: str,
    current_user = Depends(get_current_user)
):
    """Get user's quiz results for a video (legacy)"""
    return await get_post_quiz_results(video_id, current_user)
