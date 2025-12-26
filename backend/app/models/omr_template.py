from datetime import datetime
from typing import Optional, List
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field


class MarkerPosition(Document):
    """Position of an alignment marker."""

    name: str  # "top_left", "top_right", "bottom_left", "bottom_right"
    x: float  # Relative position (0-1)
    y: float
    width: float
    height: float


class MarkerConfig(Document):
    """Alignment marker configuration."""

    type: str = Field(default="corners")  # "corners", "qr", "barcode"
    positions: List[MarkerPosition] = Field(default_factory=list)


class BubblePosition(Document):
    """Position of a single bubble."""

    x: float
    y: float
    width: float
    height: float


class BubbleGridConfig(Document):
    """Bubble grid configuration."""

    rows: int = Field(default=10)
    cols: int = Field(default=10)
    bubble_radius: float = Field(default=10.0)


class StudentIdSection(Document):
    """Student ID section configuration."""

    enabled: bool = Field(default=True)
    type: str = Field(default="bubbles")  # "bubbles", "barcode", "qr"
    position: BubblePosition = Field(default_factory=BubblePosition)
    digits: int = Field(default=10)
    bubble_config: Optional[BubbleGridConfig] = None


class BubbleConfig(Document):
    """Bubble configuration for answer section."""

    width: float = Field(default=15.0)
    height: float = Field(default=15.0)
    spacing_x: float = Field(default=25.0)
    spacing_y: float = Field(default=20.0)
    fill_threshold: float = Field(default=0.4)  # 0.0 - 1.0


class QuestionConfig(Document):
    """Question configuration for a section."""

    start: int  # Starting question number
    end: int  # Ending question number
    per_row: int = Field(default=5)  # Questions per row
    options: List[str] = Field(default=["A", "B", "C", "D"])
    option_layout: str = Field(default="horizontal")  # "horizontal", "vertical"


class AnswerSection(Document):
    """Answer section configuration."""

    name: str = Field(default="Section A")
    position: BubblePosition
    questions: QuestionConfig
    bubble_config: BubbleConfig = Field(default_factory=BubbleConfig)


class TemplateConfig(Document):
    """Complete template configuration."""

    page_size: str = Field(default="A4")  # "A4", "Letter"
    orientation: str = Field(default="portrait")  # "portrait", "landscape"

    # Alignment markers
    markers: MarkerConfig = Field(default_factory=MarkerConfig)

    # Student ID section
    student_id_section: Optional[StudentIdSection] = None

    # Answer sections (can have multiple)
    answer_sections: List[AnswerSection] = Field(default_factory=list)


class AnchorPoint(Document):
    """Detected anchor point for calibration."""

    name: str
    detected_x: float
    detected_y: float
    expected_x: float
    expected_y: float


class DetectedBubble(Document):
    """Detected bubble position from calibration."""

    question_number: int
    option: str
    x: float
    y: float
    width: float
    height: float


class CalibrationData(Document):
    """Calibration data from template scan."""

    processed_at: datetime = Field(default_factory=datetime.utcnow)
    anchor_points: List[AnchorPoint] = Field(default_factory=list)
    bubble_positions: List[DetectedBubble] = Field(default_factory=list)
    quality_score: float = Field(default=0.0)


class OMRTemplateType:
    """Template types."""
    MCQ = "mcq"
    SURVEY = "survey"
    ATTENDANCE = "attendance"


class OMRTemplateStatus:
    """Template status."""
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class OMRTemplate(Document):
    """OMR Template model - defines the structure of an OMR sheet."""

    # Basic info
    institution_id: Indexed(PydanticObjectId)
    name: str
    description: Optional[str] = None
    type: str = Field(default=OMRTemplateType.MCQ)
    version: int = Field(default=1)

    # Template configuration
    config: TemplateConfig = Field(default_factory=TemplateConfig)

    # Calibration
    calibration_image: Optional[str] = None  # S3 URL
    calibration_data: Optional[CalibrationData] = None

    # Preview images
    preview_image: Optional[str] = None  # S3 URL
    sample_filled_image: Optional[str] = None  # S3 URL

    # Metadata
    is_default: bool = Field(default=False)
    is_public: bool = Field(default=False)  # Can other institutions use this?
    usage_count: int = Field(default=0)
    status: str = Field(default=OMRTemplateStatus.DRAFT)

    # Audit
    created_by: PydanticObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "omr_templates"
        use_state_management = True
        indexes = [
            "institution_id",
            [("institution_id", 1), ("status", 1)],
            [("institution_id", 1), ("type", 1)],
            [("is_public", 1), ("status", 1)],
        ]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Standard MCQ 100 Questions",
                "type": "mcq",
                "config": {
                    "page_size": "A4",
                    "orientation": "portrait",
                    "answer_sections": [
                        {
                            "name": "Section A",
                            "questions": {
                                "start": 1,
                                "end": 100,
                                "options": ["A", "B", "C", "D"]
                            }
                        }
                    ]
                }
            }
        }

    def is_calibrated(self) -> bool:
        """Check if template is calibrated."""
        return (
            self.calibration_data is not None and
            len(self.calibration_data.bubble_positions) > 0
        )

    def total_questions(self) -> int:
        """Get total number of questions."""
        total = 0
        for section in self.config.answer_sections:
            total += section.questions.end - section.questions.start + 1
        return total

    def get_options(self) -> List[str]:
        """Get answer options (assumes all sections have same options)."""
        if self.config.answer_sections:
            return self.config.answer_sections[0].questions.options
        return ["A", "B", "C", "D"]

    async def save_with_timestamp(self):
        """Save with updated timestamp."""
        self.updated_at = datetime.utcnow()
        return await self.save()

    async def increment_usage(self):
        """Increment usage count."""
        self.usage_count += 1
        await self.save()
