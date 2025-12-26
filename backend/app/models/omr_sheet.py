from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class ProcessingStatus:
    """Processing status constants."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class SheetImages(Document):
    """Image URLs for the sheet."""

    original: str  # S3 URL - original upload
    processed: Optional[str] = None  # S3 URL - after perspective correction
    annotated: Optional[str] = None  # S3 URL - with detected marks highlighted
    thumbnail: Optional[str] = None  # S3 URL - small preview


class UploadMetadata(Document):
    """Upload metadata."""

    method: str = Field(default="upload")  # "upload", "mobile", "scanner"
    batch_id: Optional[PydanticObjectId] = None
    filename: str
    file_size: int  # bytes
    mime_type: str
    uploaded_by: PydanticObjectId
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessingQuality(Document):
    """Processing quality metrics."""

    image_quality: float = Field(default=0.0)  # 0.0 - 1.0
    alignment_score: float = Field(default=0.0)  # How well markers were detected
    overall_confidence: float = Field(default=0.0)
    warnings: List[str] = Field(default_factory=list)


class FillPercentages(Document):
    """Fill percentages for each option."""

    A: float = Field(default=0.0)
    B: float = Field(default=0.0)
    C: float = Field(default=0.0)
    D: float = Field(default=0.0)
    E: float = Field(default=0.0)


class BoundingBox(Document):
    """Bounding box for detected element."""

    x: float
    y: float
    width: float
    height: float


class DetectedAnswer(Document):
    """Detected answer for a question."""

    question_number: int
    detected_mark: str  # "A", "B", "C", "D", "E", "BLANK", "MULTIPLE", "INVALID"
    confidence: float = Field(default=0.0)  # 0.0 - 1.0
    fill_percentages: Optional[FillPercentages] = None
    bounding_box: Optional[BoundingBox] = None
    flagged: bool = Field(default=False)  # Needs manual review
    flag_reason: Optional[str] = None


class ProcessingError(Document):
    """Processing error details."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ProcessingResult(Document):
    """Processing results."""

    status: str = Field(default=ProcessingStatus.PENDING)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    processing_time: Optional[int] = None  # Milliseconds

    # Quality metrics
    quality: ProcessingQuality = Field(default_factory=ProcessingQuality)

    # Detected answers
    detected_answers: List[DetectedAnswer] = Field(default_factory=list)

    # Error details if failed
    error: Optional[ProcessingError] = None


class EvaluatedAnswer(Document):
    """Evaluated answer for a question."""

    question_number: int
    marked_answer: str
    correct_answer: str
    is_correct: bool
    marks_awarded: float

    # Override info
    manually_overridden: bool = Field(default=False)
    overridden_by: Optional[PydanticObjectId] = None
    overridden_at: Optional[datetime] = None
    override_reason: Optional[str] = None


class Score(Document):
    """Score breakdown."""

    obtained: float = Field(default=0.0)
    total: float = Field(default=0.0)
    percentage: float = Field(default=0.0)
    correct: int = Field(default=0)
    incorrect: int = Field(default=0)
    unanswered: int = Field(default=0)
    invalid_marks: int = Field(default=0)


class SectionScore(Document):
    """Section-wise score."""

    section: str
    obtained: float
    total: float
    percentage: float


class EvaluationResult(Document):
    """Evaluation results."""

    answers: List[EvaluatedAnswer] = Field(default_factory=list)

    # Scores
    score: Score = Field(default_factory=Score)

    # Section-wise breakdown
    section_scores: List[SectionScore] = Field(default_factory=list)

    # Rank (updated after all sheets processed)
    rank: Optional[int] = None
    percentile: Optional[float] = None

    # Pass/Fail
    passed: bool = Field(default=False)
    grade: Optional[str] = None


class ReviewChange(Document):
    """Change made during review."""

    question_number: int
    previous_answer: str
    new_answer: str
    reason: str
    changed_by: PydanticObjectId
    changed_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewInfo(Document):
    """Review information."""

    required: bool = Field(default=False)
    reviewed_by: Optional[PydanticObjectId] = None
    reviewed_at: Optional[datetime] = None
    comments: Optional[str] = None
    changes: List[ReviewChange] = Field(default_factory=list)


class OMRSheet(Document):
    """OMR Sheet model - represents an individual scanned answer sheet."""

    # References
    institution_id: Indexed(PydanticObjectId)
    test_id: Indexed(PydanticObjectId)

    # Student identification
    student_id: Optional[PydanticObjectId] = None  # Reference to user (if identified)
    detected_student_id: Optional[str] = None  # ID detected from sheet
    student_id_confidence: float = Field(default=0.0)  # 0.0 - 1.0

    # Images
    images: SheetImages

    # Upload metadata
    upload: UploadMetadata

    # Processing results
    processing: ProcessingResult = Field(default_factory=ProcessingResult)

    # Evaluation results
    evaluation: Optional[EvaluationResult] = None

    # Review
    review: ReviewInfo = Field(default_factory=ReviewInfo)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "omr_sheets"
        use_state_management = True
        indexes = [
            "institution_id",
            "test_id",
            "student_id",
            [("institution_id", 1), ("test_id", 1)],
            [("test_id", 1), ("processing.status", 1)],
            [("upload.batch_id", 1)],
            [("test_id", 1), ("evaluation.score.percentage", -1)],  # For ranking
        ]

    def is_processed(self) -> bool:
        """Check if sheet is processed."""
        return self.processing.status == ProcessingStatus.COMPLETED

    def needs_review(self) -> bool:
        """Check if sheet needs manual review."""
        return self.processing.status == ProcessingStatus.NEEDS_REVIEW or self.review.required

    def get_answer(self, question_number: int) -> Optional[str]:
        """Get detected answer for a question."""
        for answer in self.processing.detected_answers:
            if answer.question_number == question_number:
                return answer.detected_mark
        return None

    def get_all_answers(self) -> Dict[int, str]:
        """Get all detected answers as dict."""
        return {
            answer.question_number: answer.detected_mark
            for answer in self.processing.detected_answers
        }

    def get_flagged_questions(self) -> List[int]:
        """Get list of flagged question numbers."""
        return [
            answer.question_number
            for answer in self.processing.detected_answers
            if answer.flagged
        ]

    async def save_with_timestamp(self):
        """Save with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save()

    async def mark_processing_started(self):
        """Mark processing as started."""
        self.processing.status = ProcessingStatus.PROCESSING
        self.processing.started_at = datetime.utcnow()
        await self.save_with_timestamp()

    async def mark_processing_completed(
        self,
        detected_answers: List[DetectedAnswer],
        quality: ProcessingQuality
    ):
        """Mark processing as completed."""
        self.processing.status = ProcessingStatus.COMPLETED
        self.processing.completed_at = datetime.utcnow()
        self.processing.processing_time = int(
            (self.processing.completed_at - self.processing.started_at).total_seconds() * 1000
        )
        self.processing.detected_answers = detected_answers
        self.processing.quality = quality

        # Check if any answers need review
        flagged = [a for a in detected_answers if a.flagged]
        if flagged:
            self.processing.status = ProcessingStatus.NEEDS_REVIEW
            self.review.required = True

        await self.save_with_timestamp()

    async def mark_processing_failed(self, error_code: str, error_message: str, details: Dict = None):
        """Mark processing as failed."""
        self.processing.status = ProcessingStatus.FAILED
        self.processing.completed_at = datetime.utcnow()
        self.processing.error = ProcessingError(
            code=error_code,
            message=error_message,
            details=details
        )
        await self.save_with_timestamp()

    async def set_evaluation(self, evaluation: EvaluationResult):
        """Set evaluation results."""
        self.evaluation = evaluation
        await self.save_with_timestamp()

    async def override_answer(
        self,
        question_number: int,
        new_answer: str,
        user_id: PydanticObjectId,
        reason: str
    ):
        """Override a detected answer."""
        # Find the answer
        for answer in self.processing.detected_answers:
            if answer.question_number == question_number:
                old_answer = answer.detected_mark
                answer.detected_mark = new_answer
                answer.flagged = False
                answer.flag_reason = None
                break

        # Record the change
        self.review.changes.append(ReviewChange(
            question_number=question_number,
            previous_answer=old_answer,
            new_answer=new_answer,
            reason=reason,
            changed_by=user_id,
        ))

        # Update evaluation if exists
        if self.evaluation:
            # Re-evaluate - this would need the test's answer key
            pass

        await self.save_with_timestamp()


class UploadBatch(Document):
    """Batch upload tracking."""

    institution_id: Indexed(PydanticObjectId)
    test_id: Indexed(PydanticObjectId)

    name: Optional[str] = None
    source: str = Field(default="upload")  # "upload", "scanner", "mobile"

    files: List[Dict[str, Any]] = Field(default_factory=list)
    # Each file: {filename, original_name, s3_key, status, sheet_id, error}

    # Statistics
    total_files: int = Field(default=0)
    processed: int = Field(default=0)
    successful: int = Field(default=0)
    failed: int = Field(default=0)

    status: str = Field(default="uploading")  # "uploading", "processing", "completed", "partial"

    uploaded_by: PydanticObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Settings:
        name = "upload_batches"
        indexes = [
            "institution_id",
            "test_id",
            "status",
        ]

    async def update_stats(self):
        """Update batch statistics."""
        self.processed = sum(1 for f in self.files if f.get("status") in ["completed", "failed"])
        self.successful = sum(1 for f in self.files if f.get("status") == "completed")
        self.failed = sum(1 for f in self.files if f.get("status") == "failed")

        if self.processed == self.total_files:
            self.status = "completed" if self.failed == 0 else "partial"
            self.completed_at = datetime.utcnow()

        await self.save()
