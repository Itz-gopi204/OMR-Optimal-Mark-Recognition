from datetime import datetime
from typing import Optional, List, Dict
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class MarkingScheme(Document):
    """Marking scheme for the test."""

    correct: float = Field(default=1.0)  # Marks for correct answer
    incorrect: float = Field(default=0.0)  # Negative marks (0 or negative)
    unanswered: float = Field(default=0.0)  # Marks for unanswered


class SectionConfig(Document):
    """Section-wise configuration."""

    name: str
    question_start: int
    question_end: int
    marks_per_question: float = Field(default=1.0)
    negative_marks: float = Field(default=0.0)


class TestConfig(Document):
    """Test configuration."""

    total_questions: int
    total_marks: float
    duration: Optional[int] = None  # In minutes
    passing_marks: Optional[float] = None
    passing_percentage: Optional[float] = None

    # Marking scheme
    marking_scheme: MarkingScheme = Field(default_factory=MarkingScheme)

    # Section-wise configuration
    sections: List[SectionConfig] = Field(default_factory=list)


class AnswerKeyItem(Document):
    """Individual answer key item."""

    question_number: int
    correct_answer: str  # "A", "B", "C", "D", "E"
    alternate_answers: List[str] = Field(default_factory=list)  # Multiple correct
    marks: float = Field(default=1.0)
    section: Optional[str] = None


class TestSchedule(Document):
    """Test schedule information."""

    date: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    venue: Optional[str] = None


class ProcessingSettings(Document):
    """OMR processing settings for this test."""

    auto_process: bool = Field(default=True)  # Auto-process on upload
    allow_manual_override: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.7)  # Below this, flag for review
    detect_multiple_marks: bool = Field(default=True)
    handle_multiple_marks: str = Field(default="flag")  # "flag", "invalidate", "first_mark"


class ScoreDistribution(Document):
    """Score distribution bucket."""

    range_start: int
    range_end: int
    count: int = Field(default=0)


class TestStatistics(Document):
    """Test statistics."""

    total_sheets: int = Field(default=0)
    processed_sheets: int = Field(default=0)
    pending_sheets: int = Field(default=0)
    error_sheets: int = Field(default=0)
    needs_review_sheets: int = Field(default=0)

    average_score: Optional[float] = None
    highest_score: Optional[float] = None
    lowest_score: Optional[float] = None
    median_score: Optional[float] = None

    pass_count: int = Field(default=0)
    fail_count: int = Field(default=0)
    pass_percentage: Optional[float] = None

    # Score distribution
    distribution: List[ScoreDistribution] = Field(default_factory=list)


class TestStatus:
    """Test status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Test(Document):
    """Test/Exam model."""

    # Basic info
    institution_id: Indexed(PydanticObjectId)
    template_id: PydanticObjectId  # Reference to OMR template

    name: str
    code: Indexed(str)  # Unique within institution
    description: Optional[str] = None

    # Academic info
    subject: Optional[str] = None
    class_name: Optional[str] = None  # "Grade 10", "Class XII"
    section: Optional[str] = None  # "A", "B", "Science"
    academic_year: Optional[str] = None  # "2024-25"

    # Configuration
    config: TestConfig

    # Answer key
    answer_key: List[AnswerKeyItem] = Field(default_factory=list)

    # Schedule
    schedule: Optional[TestSchedule] = None

    # Processing settings
    processing_settings: ProcessingSettings = Field(default_factory=ProcessingSettings)

    # Statistics (updated after processing)
    statistics: TestStatistics = Field(default_factory=TestStatistics)

    # Status
    status: str = Field(default=TestStatus.DRAFT)
    published_at: Optional[datetime] = None

    # Audit
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "tests"
        use_state_management = True
        indexes = [
            "institution_id",
            [("institution_id", 1), ("status", 1)],
            [("institution_id", 1), ("code", 1)],
            [("institution_id", 1), ("subject", 1), ("academic_year", 1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Mathematics Mid-Term Exam",
                "code": "MATH-MID-2024-001",
                "subject": "Mathematics",
                "class_name": "Grade 10",
                "config": {
                    "total_questions": 100,
                    "total_marks": 100,
                    "duration": 180,
                    "passing_percentage": 35
                }
            }
        }

    def has_answer_key(self) -> bool:
        """Check if answer key is set."""
        return len(self.answer_key) > 0

    def is_complete_answer_key(self) -> bool:
        """Check if answer key covers all questions."""
        return len(self.answer_key) == self.config.total_questions

    def get_answer(self, question_number: int) -> Optional[AnswerKeyItem]:
        """Get answer for a specific question."""
        for item in self.answer_key:
            if item.question_number == question_number:
                return item
        return None

    def is_correct_answer(self, question_number: int, answer: str) -> bool:
        """Check if an answer is correct."""
        key = self.get_answer(question_number)
        if not key:
            return False
        return answer == key.correct_answer or answer in key.alternate_answers

    def calculate_score(
        self,
        answers: Dict[int, str]
    ) -> Dict[str, float]:
        """Calculate score based on answers."""
        correct = 0
        incorrect = 0
        unanswered = 0
        total_marks = 0

        for q_num in range(1, self.config.total_questions + 1):
            key = self.get_answer(q_num)
            if not key:
                continue

            answer = answers.get(q_num)

            if not answer or answer in ["BLANK", "INVALID"]:
                unanswered += 1
                total_marks += self.config.marking_scheme.unanswered
            elif self.is_correct_answer(q_num, answer):
                correct += 1
                total_marks += key.marks
            else:
                incorrect += 1
                total_marks += self.config.marking_scheme.incorrect

        percentage = (total_marks / self.config.total_marks) * 100 if self.config.total_marks > 0 else 0

        return {
            "obtained": total_marks,
            "total": self.config.total_marks,
            "percentage": round(percentage, 2),
            "correct": correct,
            "incorrect": incorrect,
            "unanswered": unanswered,
        }

    def is_passed(self, score: float) -> bool:
        """Check if score is passing."""
        if self.config.passing_marks is not None:
            return score >= self.config.passing_marks
        if self.config.passing_percentage is not None:
            percentage = (score / self.config.total_marks) * 100
            return percentage >= self.config.passing_percentage
        return True  # No passing criteria defined

    async def save_with_timestamp(self):
        """Save with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save()

    async def update_statistics(self):
        """Update statistics from processed sheets."""
        from app.models.omr_sheet import OMRSheet, ProcessingStatus

        # Count sheets
        sheets = await OMRSheet.find(OMRSheet.test_id == self.id).to_list()

        self.statistics.total_sheets = len(sheets)
        self.statistics.processed_sheets = sum(
            1 for s in sheets if s.processing.status == ProcessingStatus.COMPLETED
        )
        self.statistics.pending_sheets = sum(
            1 for s in sheets if s.processing.status == ProcessingStatus.PENDING
        )
        self.statistics.error_sheets = sum(
            1 for s in sheets if s.processing.status == ProcessingStatus.FAILED
        )
        self.statistics.needs_review_sheets = sum(
            1 for s in sheets if s.processing.status == ProcessingStatus.NEEDS_REVIEW
        )

        # Calculate score statistics
        completed_sheets = [
            s for s in sheets
            if s.processing.status == ProcessingStatus.COMPLETED and s.evaluation
        ]

        if completed_sheets:
            scores = [s.evaluation.score.obtained for s in completed_sheets]
            self.statistics.average_score = round(sum(scores) / len(scores), 2)
            self.statistics.highest_score = max(scores)
            self.statistics.lowest_score = min(scores)

            # Median
            sorted_scores = sorted(scores)
            mid = len(sorted_scores) // 2
            if len(sorted_scores) % 2 == 0:
                self.statistics.median_score = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2
            else:
                self.statistics.median_score = sorted_scores[mid]

            # Pass/fail
            self.statistics.pass_count = sum(
                1 for s in completed_sheets if s.evaluation.passed
            )
            self.statistics.fail_count = len(completed_sheets) - self.statistics.pass_count
            self.statistics.pass_percentage = round(
                (self.statistics.pass_count / len(completed_sheets)) * 100, 2
            )

        await self.save_with_timestamp()
