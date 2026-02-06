"""
Watchman Agent Vision Module - PPE Detection and Site Presence Verification
Uses lightweight vision models to detect safety compliance from camera feeds

MISSION:
- Detect PPE (Hard Hat, Safety Vest, Person) from site camera feeds
- Calculate SafetyScore (0-100) based on PPE compliance
- Cross-reference detected workers with Guard's approved database
- Generate handshakes for audit chain integrity

COST TARGET: Keep under $0.001 per frame analysis
"""

import hashlib
import json
import io
from typing import Dict, Any, List, Optional, Literal, Union
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field
import numpy as np

from packages.core.agent_protocol import (
    AgentRole, AgentHandshakeV2, AgentOutputProtocol
)
from packages.core.audit import (
    DecisionProof, LogicCitation, ComplianceStandard,
    create_decision_proof
)
from packages.core.telemetry import track_agent_cost


# PPE Detection Types
class PPEItem(str):
    """PPE items that can be detected"""
    HARD_HAT = "Hard Hat"
    SAFETY_VEST = "Safety Vest"
    SAFETY_GLASSES = "Safety Glasses"
    GLOVES = "Gloves"
    PERSON = "Person"


class Detection(BaseModel):
    """Single object detection from vision model"""
    class_name: str = Field(description="Detected object class (e.g., 'Hard Hat', 'Person')")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence score")
    bbox: List[float] = Field(
        description="Bounding box [x1, y1, x2, y2] in normalized coordinates"
    )
    
    class Config:
        frozen = True


class SafetyAnalysis(BaseModel):
    """
    Complete safety analysis for a single frame
    Includes PPE detection results and compliance scoring
    """
    frame_id: str = Field(description="Unique identifier for this frame")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Detection results
    detections: List[Detection] = Field(default_factory=list)
    persons_detected: int = Field(ge=0, description="Number of persons detected")
    hard_hats_detected: int = Field(ge=0, description="Number of hard hats detected")
    safety_vests_detected: int = Field(ge=0, description="Number of safety vests detected")
    
    # Safety scoring
    safety_score: float = Field(
        ge=0.0, le=100.0,
        description="Overall safety score (0-100) based on PPE compliance"
    )
    compliance_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of workers with proper PPE"
    )
    
    # Risk assessment
    violations: List[str] = Field(
        default_factory=list,
        description="List of safety violations detected"
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Risk level based on violations"
    )
    
    # Metadata
    image_dimensions: tuple[int, int] = Field(
        description="Original image dimensions (width, height)"
    )
    processing_time_ms: float = Field(description="Processing time in milliseconds")
    
    class Config:
        frozen = True


class SitePresenceAlert(BaseModel):
    """Alert for unverified site presence"""
    alert_type: Literal["UNVERIFIED_PRESENCE", "COUNT_MISMATCH", "UNAUTHORIZED_ACCESS"]
    detected_count: int = Field(ge=0, description="Number of persons detected on site")
    approved_count: int = Field(ge=0, description="Number of approved workers from Guard")
    delta: int = Field(description="Difference (detected - approved)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: Literal["INFO", "WARNING", "CRITICAL"]
    
    class Config:
        frozen = True


class WatchmanOutput(AgentOutputProtocol):
    """
    Watchman Agent output conforming to AgentOutputProtocol
    Contains safety analysis and site presence verification
    """
    safety_analysis: SafetyAnalysis
    presence_alert: Optional[SitePresenceAlert] = Field(
        default=None,
        description="Alert if site presence doesn't match approved count"
    )
    
    class Config:
        frozen = True


class WatchmanAgent:
    """
    Watchman Agent - Site Reality Verification
    
    Processes camera feeds to detect PPE compliance and verify site presence
    against Guard's validated worker database.
    """
    
    def __init__(
        self,
        model_name: str = "yolov11-nano",
        confidence_threshold: float = 0.5,
        base_url: Optional[str] = None
    ):
        """
        Initialize Watchman Agent
        
        Args:
            model_name: Vision model to use (default: yolov11-nano for speed)
            confidence_threshold: Minimum confidence for detections (default: 0.5)
            base_url: Optional base URL for vision API
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.base_url = base_url
        
        # In production, initialize actual vision model here
        # For now, we'll use mock detection
        self._mock_mode = True
    
    def analyze_frame(
        self,
        image_buffer: Union[bytes, np.ndarray, Path],
        frame_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a camera frame for PPE compliance
        
        Args:
            image_buffer: Image data (bytes, numpy array, or file path)
            frame_id: Optional frame identifier
            project_id: Optional project identifier for audit chain
        
        Returns:
            Dict containing:
            - safety_analysis: SafetyAnalysis object
            - detections: List of Detection objects
            - decision_proof: DecisionProof for audit trail
            - cost_usd: Processing cost
            - input_tokens: Token usage (for cost tracking)
            - output_tokens: Token usage (for cost tracking)
        """
        start_time = datetime.utcnow()
        
        # Generate frame ID if not provided
        if frame_id is None:
            frame_id = f"FRAME-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Parse image buffer
        image_data, image_dimensions = self._parse_image_buffer(image_buffer)
        
        # Run PPE detection
        detections = self._detect_ppe(image_data, image_dimensions)
        
        # Count detected objects
        persons_detected = sum(1 for d in detections if d.class_name == PPEItem.PERSON)
        hard_hats_detected = sum(1 for d in detections if d.class_name == PPEItem.HARD_HAT)
        safety_vests_detected = sum(1 for d in detections if d.class_name == PPEItem.SAFETY_VEST)
        
        # Calculate safety score and compliance
        safety_score, compliance_rate, violations, risk_level = self._calculate_safety_metrics(
            persons_detected,
            hard_hats_detected,
            safety_vests_detected
        )
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Create safety analysis
        safety_analysis = SafetyAnalysis(
            frame_id=frame_id,
            timestamp=start_time,
            detections=detections,
            persons_detected=persons_detected,
            hard_hats_detected=hard_hats_detected,
            safety_vests_detected=safety_vests_detected,
            safety_score=safety_score,
            compliance_rate=compliance_rate,
            violations=violations,
            risk_level=risk_level,
            image_dimensions=image_dimensions,
            processing_time_ms=processing_time_ms
        )
        
        # Create decision proof for audit trail
        logic_citations = [
            LogicCitation(
                standard=ComplianceStandard.OSHA_1926_501,
                clause="PPE Requirements",
                interpretation=f"Detected {persons_detected} workers with {hard_hats_detected} hard hats and {safety_vests_detected} safety vests",
                confidence=0.90
            )
        ]
        
        reasoning = (
            f"Watchman analyzed site camera frame {frame_id} and detected {persons_detected} person(s). "
            f"PPE compliance: {hard_hats_detected} hard hats, {safety_vests_detected} safety vests. "
            f"Safety score: {safety_score:.1f}/100. "
            f"Risk level: {risk_level}."
        )
        
        decision_proof = create_decision_proof(
            agent_name="Watchman",
            decision=f"SAFETY_SCORE_{int(safety_score)}",
            input_data={
                "frame_id": frame_id,
                "project_id": project_id or "N/A",
                "image_dimensions": image_dimensions,
            },
            logic_citations=logic_citations,
            reasoning=reasoning,
            confidence=0.90,
            risk_level=risk_level,
            estimated_financial_impact=None,
            cost_usd=0.0  # Will be filled by decorator if used
        )
        
        # Token estimation (vision models don't use text tokens, but we track cost similarly)
        # Estimate based on image size: ~100 tokens per megapixel equivalent
        megapixels = (image_dimensions[0] * image_dimensions[1]) / 1_000_000
        input_tokens = int(megapixels * 100)
        output_tokens = len(detections) * 10  # ~10 tokens per detection
        
        return {
            "safety_analysis": safety_analysis,
            "detections": detections,
            "decision_proof": decision_proof,
            "decision_proof_obj": decision_proof,
            "cost_usd": 0.0005,  # Typical cost for lightweight vision inference
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "metadata": {
                "success": True,
                "frame_id": frame_id,
                "processing_time_ms": processing_time_ms,
            }
        }
    
    def verify_site_presence(
        self,
        detected_persons_count: int,
        project_id: str,
        parent_handshake: Optional[AgentHandshakeV2] = None,
        approved_workers_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Verify site presence against Guard's approved worker database
        
        This is the "Reality Check" handshake that connects field reality
        to office-validated compliance.
        
        Args:
            detected_persons_count: Number of persons detected in frame
            project_id: Project identifier for cross-referencing with Guard
            parent_handshake: Optional parent handshake from Scout/Guard
            approved_workers_callback: Optional callback to get approved count from Guard
                                      Should return: {"approved_count": int, "project_id": str}
        
        Returns:
            Dict containing:
            - presence_alert: SitePresenceAlert if mismatch detected
            - handshake: AgentHandshakeV2 for audit chain
            - decision_proof: DecisionProof
            - guard_approved_count: Number of approved workers
            - verified: Boolean indicating if presence is verified
        """
        # Get approved worker count from Guard
        if approved_workers_callback:
            guard_data = approved_workers_callback(project_id)
            approved_count = guard_data.get("approved_count", 0)
        else:
            # Mock: In production, this would query Guard's database
            approved_count = self._mock_get_approved_workers(project_id)
        
        # Check for presence mismatch
        delta = detected_persons_count - approved_count
        
        presence_alert = None
        alert_severity = "INFO"
        verified = True
        
        if delta > 0:
            # More people on site than approved
            verified = False
            alert_severity = "CRITICAL" if delta > 2 else "WARNING"
            presence_alert = SitePresenceAlert(
                alert_type="UNVERIFIED_PRESENCE",
                detected_count=detected_persons_count,
                approved_count=approved_count,
                delta=delta,
                severity=alert_severity
            )
        elif delta < 0:
            # Fewer people than approved (not necessarily a problem, but track it)
            alert_severity = "INFO"
            presence_alert = SitePresenceAlert(
                alert_type="COUNT_MISMATCH",
                detected_count=detected_persons_count,
                approved_count=approved_count,
                delta=delta,
                severity=alert_severity
            )
        
        # Create decision proof
        logic_citations = [
            LogicCitation(
                standard=ComplianceStandard.NYC_BC_3301,
                clause="Site Access Control",
                interpretation=f"Detected {detected_persons_count} persons vs {approved_count} approved workers",
                confidence=0.85
            )
        ]
        
        reasoning = (
            f"Watchman verified site presence for project {project_id}. "
            f"Detected: {detected_persons_count} person(s). "
            f"Approved by Guard: {approved_count} worker(s). "
            f"Status: {'VERIFIED' if verified else 'UNVERIFIED_PRESENCE'}."
        )
        
        decision_proof = create_decision_proof(
            agent_name="Watchman",
            decision="VERIFIED" if verified else "UNVERIFIED_PRESENCE",
            input_data={
                "project_id": project_id,
                "detected_count": detected_persons_count,
                "approved_count": approved_count,
            },
            logic_citations=logic_citations,
            reasoning=reasoning,
            confidence=0.85,
            risk_level="CRITICAL" if not verified else "LOW",
            estimated_financial_impact=None,
            cost_usd=0.0001  # Minimal cost for database lookup
        )
        
        # Create Watchman handshake
        target_agent = None  # Terminal if verified, or could route to Fixer if issues
        if not verified:
            target_agent = AgentRole.FIXER
        
        handshake = AgentHandshakeV2(
            source_agent=AgentRole.WATCHMAN,
            target_agent=target_agent,
            project_id=project_id,
            decision_hash=decision_proof.proof_hash,
            parent_handshake_id=parent_handshake.decision_hash if parent_handshake else None,
            transition_reason="presence_verified" if verified else "unverified_presence_detected",
            metadata={
                "detected_count": detected_persons_count,
                "approved_count": approved_count,
                "delta": delta,
                "verified": verified,
            }
        )
        
        return {
            "presence_alert": presence_alert,
            "handshake": handshake,
            "decision_proof": decision_proof,
            "decision_proof_obj": decision_proof,
            "guard_approved_count": approved_count,
            "verified": verified,
            "cost_usd": 0.0001,
            "input_tokens": 50,
            "output_tokens": 100,
        }
    
    def _parse_image_buffer(
        self,
        image_buffer: Union[bytes, np.ndarray, Path]
    ) -> tuple[Any, tuple[int, int]]:
        """
        Parse image buffer into format suitable for vision model
        
        Returns:
            Tuple of (image_data, dimensions)
        """
        # Mock implementation - in production, would use PIL/OpenCV
        if isinstance(image_buffer, Path):
            # Load from file
            image_dimensions = (1920, 1080)  # Mock HD resolution
            image_data = image_buffer
        elif isinstance(image_buffer, bytes):
            # Parse bytes
            image_dimensions = (1920, 1080)  # Mock
            image_data = image_buffer
        elif isinstance(image_buffer, np.ndarray):
            # NumPy array
            if len(image_buffer.shape) == 3:
                image_dimensions = (image_buffer.shape[1], image_buffer.shape[0])
            else:
                image_dimensions = (640, 480)  # Default
            image_data = image_buffer
        else:
            # Unknown format, use defaults
            image_dimensions = (640, 480)
            image_data = image_buffer
        
        return image_data, image_dimensions
    
    def _detect_ppe(
        self,
        image_data: Any,
        image_dimensions: tuple[int, int]
    ) -> List[Detection]:
        """
        Run PPE detection on image
        
        In production: This would call YOLOv11 or similar vision model
        For now: Returns mock detections for testing
        """
        if self._mock_mode:
            return self._mock_detect_ppe(image_dimensions)
        
        # Production code would call actual vision model here
        # detections = self.model.predict(image_data)
        raise NotImplementedError("Production vision model not yet implemented")
    
    def _mock_detect_ppe(
        self,
        image_dimensions: tuple[int, int]
    ) -> List[Detection]:
        """
        Mock PPE detection for testing
        Simulates detecting workers with various PPE compliance levels
        """
        # Simulate detecting 3 workers with different PPE compliance
        detections = [
            # Person 1 - Full PPE
            Detection(
                class_name=PPEItem.PERSON,
                confidence=0.95,
                bbox=[0.1, 0.2, 0.3, 0.8]
            ),
            Detection(
                class_name=PPEItem.HARD_HAT,
                confidence=0.92,
                bbox=[0.15, 0.2, 0.25, 0.35]
            ),
            Detection(
                class_name=PPEItem.SAFETY_VEST,
                confidence=0.88,
                bbox=[0.12, 0.4, 0.28, 0.7]
            ),
            # Person 2 - Has hard hat, missing vest
            Detection(
                class_name=PPEItem.PERSON,
                confidence=0.93,
                bbox=[0.4, 0.15, 0.6, 0.85]
            ),
            Detection(
                class_name=PPEItem.HARD_HAT,
                confidence=0.90,
                bbox=[0.45, 0.15, 0.55, 0.3]
            ),
            # Person 3 - Full PPE
            Detection(
                class_name=PPEItem.PERSON,
                confidence=0.91,
                bbox=[0.7, 0.25, 0.9, 0.9]
            ),
            Detection(
                class_name=PPEItem.HARD_HAT,
                confidence=0.89,
                bbox=[0.75, 0.25, 0.85, 0.4]
            ),
            Detection(
                class_name=PPEItem.SAFETY_VEST,
                confidence=0.87,
                bbox=[0.72, 0.45, 0.88, 0.75]
            ),
        ]
        
        return detections
    
    def _calculate_safety_metrics(
        self,
        persons_detected: int,
        hard_hats_detected: int,
        safety_vests_detected: int
    ) -> tuple[float, float, List[str], str]:
        """
        Calculate safety score and identify violations
        
        Returns:
            Tuple of (safety_score, compliance_rate, violations, risk_level)
        """
        violations = []
        
        if persons_detected == 0:
            # No workers detected - perfect score
            return 100.0, 1.0, [], "LOW"
        
        # Calculate compliance rates
        hard_hat_rate = hard_hats_detected / persons_detected
        vest_rate = safety_vests_detected / persons_detected
        
        # Overall compliance (both PPE items required)
        compliance_rate = min(hard_hat_rate, vest_rate)
        
        # Identify specific violations
        if hard_hat_rate < 1.0:
            missing_hats = persons_detected - hard_hats_detected
            violations.append(
                f"Missing hard hat(s): {missing_hats} worker(s) without required head protection"
            )
        
        if vest_rate < 1.0:
            missing_vests = persons_detected - safety_vests_detected
            violations.append(
                f"Missing safety vest(s): {missing_vests} worker(s) without required high-visibility clothing"
            )
        
        # Calculate safety score (0-100)
        # Base score is compliance rate * 100
        # Penalize violations more heavily
        base_score = compliance_rate * 100
        
        # Additional penalties for partial compliance
        if hard_hat_rate < 1.0 and vest_rate < 1.0:
            # Both violations - more severe
            safety_score = base_score * 0.8
        else:
            safety_score = base_score
        
        # Determine risk level
        if safety_score >= 90:
            risk_level = "LOW"
        elif safety_score >= 70:
            risk_level = "MEDIUM"
        elif safety_score >= 50:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"
        
        return safety_score, compliance_rate, violations, risk_level
    
    def _mock_get_approved_workers(self, project_id: str) -> int:
        """
        Mock function to get approved worker count from Guard
        In production, this would query Guard's validated database
        """
        # Mock: Return a typical crew size
        return 3


@track_agent_cost(agent_name="Watchman", model_name="claude-3-haiku")
def analyze_site_frame(
    image_buffer: Union[bytes, Path],
    project_id: str,
    frame_id: Optional[str] = None,
    verify_presence: bool = True,
    parent_handshake: Optional[AgentHandshakeV2] = None
) -> Dict[str, Any]:
    """
    Complete Watchman analysis: frame analysis + presence verification
    
    This is the main entry point for Watchman operations.
    
    Args:
        image_buffer: Camera frame image data
        project_id: Project identifier for cross-referencing
        frame_id: Optional frame identifier
        verify_presence: Whether to verify site presence (default: True)
        parent_handshake: Optional parent handshake from Guard
    
    Returns:
        Dict containing WatchmanOutput and handshake for audit chain
        Includes input_tokens and output_tokens for cost tracking
    """
    agent = WatchmanAgent()
    
    # Analyze frame for PPE compliance
    frame_result = agent.analyze_frame(
        image_buffer=image_buffer,
        frame_id=frame_id,
        project_id=project_id
    )
    
    safety_analysis = frame_result["safety_analysis"]
    frame_decision_proof = frame_result["decision_proof_obj"]
    
    # Verify site presence if requested
    presence_alert = None
    final_handshake = None
    total_cost = frame_result["cost_usd"]
    
    if verify_presence:
        presence_result = agent.verify_site_presence(
            detected_persons_count=safety_analysis.persons_detected,
            project_id=project_id,
            parent_handshake=parent_handshake
        )
        
        presence_alert = presence_result.get("presence_alert")
        final_handshake = presence_result["handshake"]
        total_cost += presence_result["cost_usd"]
    else:
        # Create handshake without presence verification
        final_handshake = AgentHandshakeV2(
            source_agent=AgentRole.WATCHMAN,
            target_agent=None,  # Terminal
            project_id=project_id,
            decision_hash=frame_decision_proof.proof_hash,
            parent_handshake_id=parent_handshake.decision_hash if parent_handshake else None,
            transition_reason="frame_analyzed",
            metadata={
                "safety_score": safety_analysis.safety_score,
                "persons_detected": safety_analysis.persons_detected,
                "risk_level": safety_analysis.risk_level,
            }
        )
    
    # Create WatchmanOutput
    watchman_output = WatchmanOutput(
        handshake=final_handshake,
        decision_proof_hash=frame_decision_proof.proof_hash,
        processing_cost_usd=total_cost,
        confidence_score=0.90,
        agent_name=AgentRole.WATCHMAN,
        safety_analysis=safety_analysis,
        presence_alert=presence_alert
    )
    
    # Return with token usage for cost tracking
    return {
        "watchman_output": watchman_output,
        "safety_analysis": safety_analysis,
        "presence_alert": presence_alert,
        "handshake": final_handshake,
        "decision_proof": frame_decision_proof,
        "decision_proof_obj": frame_decision_proof,
        "input_tokens": frame_result["input_tokens"],
        "output_tokens": frame_result["output_tokens"],
        "cost_usd": total_cost,
        "metadata": {
            "success": True,
            "frame_id": safety_analysis.frame_id,
        }
    }
