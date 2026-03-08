"""
AI service for quiz generation using OpenAI GPT-4o-mini (optimized for cost)
"""
import json
from typing import List, Optional
from openai import AsyncOpenAI
from config import get_settings
from models.schemas import QuizQuestion, QuestionType, QuizOption
import structlog

logger = structlog.get_logger()
settings = get_settings()


class QuizGenerator:
    """Generate quiz questions from video content using GPT-4o-mini"""
    
    # GPT-4o-mini: 90% cheaper than GPT-4, still very capable
    MODEL = "gpt-4o-mini"
    
    def __init__(self):
        self._client: Optional[AsyncOpenAI] = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """Lazy-load OpenAI client"""
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client
    
    async def generate_quiz(
        self,
        video_transcript: str,
        video_title: str,
        num_questions: int = 5
    ) -> List[QuizQuestion]:
        """Generate quiz questions based on video content"""
        
        # Truncate transcript if too long (save tokens)
        max_transcript = 1500
        if len(video_transcript) > max_transcript:
            video_transcript = video_transcript[:max_transcript] + "..."
        
        prompt = f"""Generate {num_questions} English learning quiz questions from this video.

Title: {video_title}
Transcript: {video_transcript}

Mix question types:
- multiple_choice: Test understanding
- fill_blank: Test vocabulary (use ___ for blank)
- true_false: Test comprehension

Return JSON only:
{{"questions": [
  {{"type": "multiple_choice", "question": "...", "options": [
    {{"id": "a", "text": "...", "is_correct": false}},
    {{"id": "b", "text": "...", "is_correct": true}},
    {{"id": "c", "text": "...", "is_correct": false}},
    {{"id": "d", "text": "...", "is_correct": false}}
  ], "explanation": "...", "points": 10}},
  {{"type": "fill_blank", "question": "The ___ is important.", "correct_answer": "word", "explanation": "...", "points": 10}},
  {{"type": "true_false", "question": "...", "correct_answer": "true", "explanation": "...", "points": 10}}
]}}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an English teacher. Generate quiz questions in valid JSON format only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Parse questions
            questions = []
            for i, q_data in enumerate(result.get("questions", [])):
                try:
                    question_type = QuestionType(q_data["type"])
                    
                    options = None
                    if "options" in q_data:
                        options = [QuizOption(**opt) for opt in q_data["options"]]
                    
                    question = QuizQuestion(
                        id=f"q{i+1}",
                        type=question_type,
                        question=q_data["question"],
                        options=options,
                        correct_answer=q_data.get("correct_answer"),
                        explanation=q_data.get("explanation", ""),
                        points=q_data.get("points", 10)
                    )
                    questions.append(question)
                except Exception as parse_error:
                    logger.warning("Failed to parse question", error=str(parse_error))
                    continue
            
            logger.info("Quiz generated", model=self.MODEL, questions=len(questions))
            return questions
            
        except Exception as e:
            logger.error("Failed to generate quiz", error=str(e))
            raise Exception(f"Failed to generate quiz: {str(e)}")
    
    async def extract_tags(
        self,
        transcript: str,
        title: str,
        max_tags: int = 5
    ) -> List[str]:
        """Extract topic tags from video content (for recommendations)"""
        
        prompt = f"""Extract {max_tags} topic tags from this video content.
        
Title: {title}
Transcript: {transcript[:1000]}

Return JSON: {{"tags": ["tag1", "tag2", ...]}}

Tags should be lowercase, single words or short phrases like:
cooking, travel, technology, business, lifestyle, education, sports, music, etc."""

        try:
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "Extract topic tags. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            tags = result.get("tags", [])[:max_tags]
            
            logger.info("Tags extracted", tags=tags)
            return tags
            
        except Exception as e:
            logger.warning("Failed to extract tags", error=str(e))
            return []
    
    def evaluate_answers(
        self,
        questions: List[QuizQuestion],
        answers: dict
    ) -> dict:
        """Evaluate quiz answers"""
        correct_count = 0
        total_score = 0
        max_score = 0
        details = []
        
        for question in questions:
            max_score += question.points
            user_answer = answers.get(question.id)
            
            is_correct = False
            correct_answer = None
            
            if question.type == QuestionType.MULTIPLE_CHOICE:
                correct_option = next(
                    (opt for opt in (question.options or []) if opt.is_correct),
                    None
                )
                correct_answer = correct_option.id if correct_option else None
                is_correct = user_answer == correct_answer
                
            elif question.type == QuestionType.FILL_BLANK:
                correct_answer = question.correct_answer
                if user_answer and correct_answer:
                    is_correct = user_answer.lower().strip() == correct_answer.lower().strip()
                
            elif question.type == QuestionType.TRUE_FALSE:
                correct_answer = question.correct_answer
                if user_answer is not None and correct_answer:
                    is_correct = str(user_answer).lower() == str(correct_answer).lower()
                
            elif question.type == QuestionType.ARRANGE_SENTENCE:
                correct_answer = question.correct_answer
                is_correct = user_answer == correct_answer
            
            if is_correct:
                correct_count += 1
                total_score += question.points
            
            details.append({
                "question_id": question.id,
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "points_earned": question.points if is_correct else 0,
                "explanation": question.explanation
            })
        
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        return {
            "score": total_score,
            "total_points": max_score,
            "percentage": round(percentage, 1),
            "correct_answers": correct_count,
            "total_questions": len(questions),
            "passed": percentage >= 70,
            "details": details
        }
