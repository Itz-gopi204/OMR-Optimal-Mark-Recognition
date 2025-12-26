"""
OMR (Optical Mark Recognition) Processor

This module provides the core OMR processing functionality using OpenCV.
It handles sheet detection, perspective correction, bubble detection, and answer extraction.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class BubbleFillResult:
    """Result of bubble fill analysis."""
    option: str
    fill_percentage: float
    is_filled: bool


@dataclass
class DetectedAnswerResult:
    """Result of answer detection for a question."""
    question_number: int
    detected_mark: str  # "A", "B", "C", "D", "E", "BLANK", "MULTIPLE", "INVALID"
    confidence: float
    fill_percentages: Dict[str, float]
    bounding_box: Optional[Dict[str, float]] = None
    flagged: bool = False
    flag_reason: Optional[str] = None


@dataclass
class QualityMetrics:
    """Image and processing quality metrics."""
    image_quality: float = 0.0
    alignment_score: float = 0.0
    overall_confidence: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """Complete processing result."""
    success: bool
    detected_student_id: Optional[str] = None
    student_id_confidence: float = 0.0
    answers: List[DetectedAnswerResult] = field(default_factory=list)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    processed_image: Optional[np.ndarray] = None
    annotated_image: Optional[np.ndarray] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class OMRProcessor:
    """
    Core OMR processing engine using OpenCV.

    This class handles the complete OMR processing pipeline:
    1. Image loading and preprocessing
    2. Sheet boundary detection
    3. Perspective transformation
    4. Bubble detection and analysis
    5. Answer determination
    """

    def __init__(self, template_config: Dict[str, Any]):
        """
        Initialize the OMR processor.

        Args:
            template_config: Template configuration defining sheet layout
        """
        self.template = template_config
        self.fill_threshold = template_config.get("fill_threshold", 0.4)
        self.confidence_threshold = template_config.get("confidence_threshold", 0.7)

    def process(self, image_path: str) -> ProcessingResult:
        """
        Process an OMR sheet image.

        Args:
            image_path: Path to the image file

        Returns:
            ProcessingResult containing detected answers and quality metrics
        """
        try:
            # Step 1: Load image
            image = self._load_image(image_path)
            if image is None:
                return ProcessingResult(
                    success=False,
                    error_code="IMAGE_LOAD_FAILED",
                    error_message="Failed to load image file"
                )

            quality = QualityMetrics()

            # Step 2: Auto-orient (ensure portrait)
            image = self._auto_orient(image)

            # Step 3: Detect sheet boundaries
            sheet_contour = self._detect_sheet_boundary(image)
            if sheet_contour is None:
                return ProcessingResult(
                    success=False,
                    error_code="SHEET_NOT_DETECTED",
                    error_message="Could not detect sheet boundaries"
                )

            # Step 4: Perspective transform
            warped = self._perspective_transform(image, sheet_contour)
            quality.alignment_score = 0.9  # Would calculate from marker detection

            # Step 5: Evaluate image quality
            quality.image_quality = self._evaluate_image_quality(warped)
            if quality.image_quality < 0.3:
                quality.warnings.append("low_image_quality")

            # Step 6: Detect student ID (if configured)
            detected_student_id = None
            student_id_confidence = 0.0

            student_id_config = self.template.get("student_id_section")
            if student_id_config and student_id_config.get("enabled"):
                detected_student_id, student_id_confidence = self._detect_student_id(
                    warped, student_id_config
                )

            # Step 7: Process answer sections
            all_answers = []
            answer_sections = self.template.get("answer_sections", [])

            for section in answer_sections:
                section_answers = self._process_answer_section(warped, section)
                all_answers.extend(section_answers)

            # Step 8: Calculate overall confidence
            if all_answers:
                quality.overall_confidence = sum(
                    a.confidence for a in all_answers
                ) / len(all_answers)

            # Step 9: Generate annotated image
            annotated = self._generate_annotated_image(warped, all_answers)

            return ProcessingResult(
                success=True,
                detected_student_id=detected_student_id,
                student_id_confidence=student_id_confidence,
                answers=all_answers,
                quality=quality,
                processed_image=warped,
                annotated_image=annotated
            )

        except Exception as e:
            logger.error(f"OMR processing error: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                error_code="PROCESSING_ERROR",
                error_message=str(e)
            )

    def _load_image(self, path: str) -> Optional[np.ndarray]:
        """Load image from file."""
        try:
            image = cv2.imread(path)
            if image is None:
                logger.error(f"Failed to load image: {path}")
                return None
            return image
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return None

    def _auto_orient(self, image: np.ndarray) -> np.ndarray:
        """Auto-rotate image to portrait orientation."""
        h, w = image.shape[:2]
        if w > h:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        return image

    def _detect_sheet_boundary(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect the answer sheet boundary using edge detection.

        Returns the 4-point contour of the sheet, or None if not found.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Edge detection using Canny
        edges = cv2.Canny(blurred, 75, 200)

        # Find contours
        contours, _ = cv2.findContours(
            edges.copy(),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None

        # Sort by area, get largest contours
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        # Find a 4-point contour (the sheet)
        for contour in contours[:5]:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            # If we found a 4-point contour, it's likely the sheet
            if len(approx) == 4:
                return approx

        # If no 4-point contour found, return the largest contour's bounding rect
        largest = contours[0]
        rect = cv2.minAreaRect(largest)
        box = cv2.boxPoints(rect)
        return np.int0(box)

    def _perspective_transform(
        self,
        image: np.ndarray,
        contour: np.ndarray
    ) -> np.ndarray:
        """Apply 4-point perspective transform to correct skew."""
        # Order points: top-left, top-right, bottom-right, bottom-left
        pts = self._order_points(contour.reshape(4, 2))

        (tl, tr, br, bl) = pts

        # Compute new image dimensions
        width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        max_width = max(int(width_a), int(width_b))

        height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        max_height = max(int(height_a), int(height_b))

        # Destination points
        dst = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype="float32")

        # Compute transformation matrix and apply
        matrix = cv2.getPerspectiveTransform(pts, dst)
        warped = cv2.warpPerspective(image, matrix, (max_width, max_height))

        return warped

    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Order points: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype="float32")

        # Sum and diff to find corners
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # Top-left has smallest sum
        rect[2] = pts[np.argmax(s)]  # Bottom-right has largest sum

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # Top-right has smallest diff
        rect[3] = pts[np.argmax(diff)]  # Bottom-left has largest diff

        return rect

    def _evaluate_image_quality(self, image: np.ndarray) -> float:
        """Evaluate image quality (contrast, sharpness, etc.)."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate Laplacian variance (sharpness)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

        # Calculate contrast
        contrast = gray.std()

        # Normalize to 0-1 range
        sharpness_score = min(laplacian_var / 500, 1.0)
        contrast_score = min(contrast / 80, 1.0)

        return (sharpness_score + contrast_score) / 2

    def _detect_student_id(
        self,
        image: np.ndarray,
        config: Dict
    ) -> Tuple[Optional[str], float]:
        """
        Detect student ID from the sheet.

        Args:
            image: Warped sheet image
            config: Student ID section configuration

        Returns:
            Tuple of (detected_id, confidence)
        """
        id_type = config.get("type", "bubbles")

        if id_type == "barcode":
            return self._detect_barcode(image, config)
        elif id_type == "qr":
            return self._detect_qr_code(image, config)
        else:
            return self._detect_bubble_id(image, config)

    def _detect_barcode(
        self,
        image: np.ndarray,
        config: Dict
    ) -> Tuple[Optional[str], float]:
        """Detect barcode in the image."""
        # Would use pyzbar or similar library
        # For now, return placeholder
        return None, 0.0

    def _detect_qr_code(
        self,
        image: np.ndarray,
        config: Dict
    ) -> Tuple[Optional[str], float]:
        """Detect QR code in the image."""
        # Would use cv2.QRCodeDetector
        try:
            detector = cv2.QRCodeDetector()
            data, points, _ = detector.detectAndDecode(image)
            if data:
                return data, 0.95
        except Exception as e:
            logger.warning(f"QR detection failed: {e}")
        return None, 0.0

    def _detect_bubble_id(
        self,
        image: np.ndarray,
        config: Dict
    ) -> Tuple[Optional[str], float]:
        """Detect student ID from bubble grid."""
        position = config.get("position", {})
        digits = config.get("digits", 10)

        h, w = image.shape[:2]
        x1 = int(position.get("x", 0) * w)
        y1 = int(position.get("y", 0) * h)
        x2 = int((position.get("x", 0) + position.get("width", 0.2)) * w)
        y2 = int((position.get("y", 0) + position.get("height", 0.3)) * h)

        id_region = image[y1:y2, x1:x2]

        # Convert to grayscale and threshold
        gray = cv2.cvtColor(id_region, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # TODO: Implement full bubble grid detection for student ID
        # This would involve detecting the bubble grid and reading each digit column

        return None, 0.0

    def _process_answer_section(
        self,
        image: np.ndarray,
        section: Dict
    ) -> List[DetectedAnswerResult]:
        """
        Process a single answer section.

        Args:
            image: Warped sheet image
            section: Section configuration

        Returns:
            List of detected answers for this section
        """
        answers = []

        # Extract section region
        position = section.get("position", {})
        h, w = image.shape[:2]

        x1 = int(position.get("x", 0) * w)
        y1 = int(position.get("y", 0) * h)
        x2 = int((position.get("x", 0) + position.get("width", 1)) * w)
        y2 = int((position.get("y", 0) + position.get("height", 1)) * h)

        section_img = image[y1:y2, x1:x2]

        # Get configuration
        questions_config = section.get("questions", {})
        q_start = questions_config.get("start", 1)
        q_end = questions_config.get("end", 100)
        options = questions_config.get("options", ["A", "B", "C", "D"])
        per_row = questions_config.get("per_row", 5)

        bubble_config = section.get("bubble_config", {})
        fill_threshold = bubble_config.get("fill_threshold", self.fill_threshold)

        # Convert to grayscale and threshold
        gray = cv2.cvtColor(section_img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Find all contours (potential bubbles)
        contours, _ = cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        # Filter contours to find bubbles
        bubbles = self._filter_bubble_contours(contours, bubble_config)

        # Sort bubbles into grid
        bubble_grid = self._sort_bubbles_to_grid(
            bubbles, q_start, q_end, len(options), per_row
        )

        # Analyze each question
        for q_num in range(q_start, q_end + 1):
            row_bubbles = bubble_grid.get(q_num, [])

            if len(row_bubbles) != len(options):
                answers.append(DetectedAnswerResult(
                    question_number=q_num,
                    detected_mark="INVALID",
                    confidence=0.0,
                    fill_percentages={opt: 0.0 for opt in options},
                    flagged=True,
                    flag_reason="bubble_count_mismatch"
                ))
                continue

            # Calculate fill percentage for each bubble
            fill_percentages = {}
            for i, bubble_contour in enumerate(row_bubbles):
                fill_pct = self._calculate_fill_percentage(binary, bubble_contour)
                fill_percentages[options[i]] = fill_pct

            # Determine answer
            answer = self._determine_answer(fill_percentages, fill_threshold)
            answers.append(answer)
            answers[-1].question_number = q_num

        return answers

    def _filter_bubble_contours(
        self,
        contours: List,
        config: Dict
    ) -> List:
        """Filter contours to find valid bubbles."""
        bubbles = []

        min_area = config.get("min_area", 100)
        max_area = config.get("max_area", 3000)
        min_circularity = config.get("min_circularity", 0.5)

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < min_area or area > max_area:
                continue

            # Check circularity
            perimeter = cv2.arcLength(contour, True)
            if perimeter == 0:
                continue

            circularity = 4 * np.pi * area / (perimeter * perimeter)

            if circularity > min_circularity:
                bubbles.append(contour)

        return bubbles

    def _sort_bubbles_to_grid(
        self,
        bubbles: List,
        q_start: int,
        q_end: int,
        num_options: int,
        per_row: int
    ) -> Dict[int, List]:
        """Sort bubbles into a grid organized by question number."""
        if not bubbles:
            return {}

        # Get centroids
        centroids = []
        for bubble in bubbles:
            M = cv2.moments(bubble)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                centroids.append((cx, cy, bubble))

        if not centroids:
            return {}

        # Sort by y-coordinate (rows), then x-coordinate (columns)
        centroids.sort(key=lambda c: (c[1], c[0]))

        # Group into rows based on y-proximity
        rows = []
        current_row = [centroids[0]]
        row_threshold = 20  # Pixels

        for i in range(1, len(centroids)):
            if abs(centroids[i][1] - current_row[-1][1]) < row_threshold:
                current_row.append(centroids[i])
            else:
                rows.append(sorted(current_row, key=lambda c: c[0]))
                current_row = [centroids[i]]
        rows.append(sorted(current_row, key=lambda c: c[0]))

        # Map to question numbers
        result = {}
        total_questions = q_end - q_start + 1

        for i, row in enumerate(rows):
            if i >= total_questions:
                break
            q_num = q_start + i
            result[q_num] = [item[2] for item in row[:num_options]]

        return result

    def _calculate_fill_percentage(
        self,
        binary_image: np.ndarray,
        contour: np.ndarray
    ) -> float:
        """Calculate what percentage of a bubble is filled."""
        # Create mask for this bubble
        mask = np.zeros(binary_image.shape, dtype="uint8")
        cv2.drawContours(mask, [contour], -1, 255, -1)

        # Count pixels
        total_pixels = cv2.countNonZero(mask)
        if total_pixels == 0:
            return 0.0

        # Count filled pixels within the bubble
        masked = cv2.bitwise_and(binary_image, binary_image, mask=mask)
        filled_pixels = cv2.countNonZero(masked)

        return filled_pixels / total_pixels

    def _determine_answer(
        self,
        fill_percentages: Dict[str, float],
        threshold: float
    ) -> DetectedAnswerResult:
        """Determine the selected answer from fill percentages."""
        # Find options that meet the threshold
        marked = [
            opt for opt, pct in fill_percentages.items()
            if pct >= threshold
        ]

        if len(marked) == 0:
            return DetectedAnswerResult(
                question_number=0,  # Will be set by caller
                detected_mark="BLANK",
                confidence=0.9,
                fill_percentages=fill_percentages
            )
        elif len(marked) == 1:
            return DetectedAnswerResult(
                question_number=0,
                detected_mark=marked[0],
                confidence=fill_percentages[marked[0]],
                fill_percentages=fill_percentages
            )
        else:
            # Multiple marks detected
            return DetectedAnswerResult(
                question_number=0,
                detected_mark="MULTIPLE",
                confidence=0.5,
                fill_percentages=fill_percentages,
                flagged=True,
                flag_reason="multiple_marks"
            )

    def _generate_annotated_image(
        self,
        image: np.ndarray,
        answers: List[DetectedAnswerResult]
    ) -> np.ndarray:
        """Generate annotated image showing detected answers."""
        annotated = image.copy()

        # Draw detection results
        for answer in answers:
            if answer.bounding_box:
                bbox = answer.bounding_box

                # Choose color based on status
                if answer.flagged:
                    color = (0, 0, 255)  # Red for flagged
                elif answer.detected_mark in ["BLANK", "INVALID"]:
                    color = (128, 128, 128)  # Gray for blank/invalid
                else:
                    color = (0, 255, 0)  # Green for detected

                cv2.rectangle(
                    annotated,
                    (int(bbox["x"]), int(bbox["y"])),
                    (int(bbox["x"] + bbox["width"]), int(bbox["y"] + bbox["height"])),
                    color,
                    2
                )

                # Add label
                label = f"Q{answer.question_number}: {answer.detected_mark}"
                cv2.putText(
                    annotated,
                    label,
                    (int(bbox["x"]), int(bbox["y"] - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1
                )

        return annotated

    @staticmethod
    def create_default_template(
        total_questions: int = 100,
        options: List[str] = None,
        questions_per_row: int = 5
    ) -> Dict:
        """Create a default template configuration."""
        if options is None:
            options = ["A", "B", "C", "D"]

        return {
            "page_size": "A4",
            "orientation": "portrait",
            "fill_threshold": 0.4,
            "confidence_threshold": 0.7,
            "student_id_section": {
                "enabled": True,
                "type": "bubbles",
                "position": {"x": 0.05, "y": 0.05, "width": 0.3, "height": 0.15},
                "digits": 10
            },
            "answer_sections": [
                {
                    "name": "Main Section",
                    "position": {"x": 0.05, "y": 0.25, "width": 0.9, "height": 0.7},
                    "questions": {
                        "start": 1,
                        "end": total_questions,
                        "per_row": questions_per_row,
                        "options": options,
                        "option_layout": "horizontal"
                    },
                    "bubble_config": {
                        "width": 15,
                        "height": 15,
                        "spacing_x": 25,
                        "spacing_y": 20,
                        "fill_threshold": 0.4,
                        "min_area": 100,
                        "max_area": 3000,
                        "min_circularity": 0.5
                    }
                }
            ]
        }
