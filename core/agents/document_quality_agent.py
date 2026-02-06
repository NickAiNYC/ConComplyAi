"""Document Quality Agent - Handle skewed scans, photos, and poor quality documents"""
from typing import Dict
from datetime import datetime
from core.models import DocumentExtractionState, AgentOutput
from core.config import calculate_token_cost


def assess_document_quality(state: DocumentExtractionState) -> dict:
    """
    DOCUMENT NUANCES: Construction docs are often:
    - Skewed scans (rotated, tilted)
    - Photos of crumpled paper
    - Multi-page PDFs with varying layouts
    - Low contrast, blurry, or faded
    
    This agent assesses quality and suggests preprocessing
    """
    try:
        # Simulate quality assessment
        # In production, this would use OpenCV or similar for:
        # - Skew detection (Hough transform)
        # - Blur detection (Laplacian variance)
        # - Contrast analysis (histogram)
        # - Crumple detection (texture analysis)
        
        quality_score = 0.85  # 0-1 scale
        is_skewed = False
        is_crumpled = False
        is_low_contrast = False
        is_blurry = False
        
        # Deterministic quality check based on document_id
        # In production, this would analyze actual image
        if "POOR" in state.document_id.upper():
            quality_score = 0.45
            is_skewed = True
            is_crumpled = True
            is_low_contrast = True
        elif "SKEWED" in state.document_id.upper():
            quality_score = 0.62
            is_skewed = True
        elif "BLURRY" in state.document_id.upper():
            quality_score = 0.58
            is_blurry = True
        
        # Generate recommendations
        recommendations = []
        validation_errors = []
        
        if quality_score < 0.5:
            validation_errors.append("CRITICAL: Document quality too poor for reliable extraction")
            recommendations.append("Request higher quality scan or photo")
        elif quality_score < 0.7:
            validation_errors.append("WARNING: Document quality suboptimal - extraction may be unreliable")
        
        if is_skewed:
            recommendations.append("Apply deskew transformation (rotate -3.2°)")
            validation_errors.append("WARNING: Document appears skewed")
        
        if is_crumpled:
            recommendations.append("Apply perspective correction")
            validation_errors.append("WARNING: Document appears crumpled or folded")
        
        if is_low_contrast:
            recommendations.append("Apply adaptive histogram equalization")
            validation_errors.append("WARNING: Low contrast - text may be difficult to extract")
        
        if is_blurry:
            recommendations.append("Apply sharpening filter (unsharp mask)")
            validation_errors.append("WARNING: Image appears blurry")
        
        # Calculate cost
        input_tokens = 500  # Image analysis
        output_tokens = 150  # Quality assessment
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[DOCUMENT_QUALITY] TOKEN_COST_USD: ${cost:.6f} (in={input_tokens}, out={output_tokens})")
        print(f"[DOCUMENT_QUALITY] Quality Score: {quality_score:.2f}")
        print(f"[DOCUMENT_QUALITY] Issues: Skewed={is_skewed}, Crumpled={is_crumpled}, Low Contrast={is_low_contrast}, Blurry={is_blurry}")
        
        agent_output = AgentOutput(
            agent_name="document_quality_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={
                "quality_score": quality_score,
                "is_skewed": is_skewed,
                "is_crumpled": is_crumpled,
                "is_low_contrast": is_low_contrast,
                "is_blurry": is_blurry,
                "recommendations": recommendations
            }
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "document_quality_score": quality_score,
            "is_skewed": is_skewed,
            "is_crumpled": is_crumpled,
            "validation_errors": state.validation_errors + validation_errors,
            "agent_outputs": agent_outputs,
            "total_tokens": state.total_tokens + input_tokens + output_tokens,
            "total_cost": state.total_cost + cost
        }
        
    except Exception as e:
        print(f"[DOCUMENT_QUALITY] ERROR: {str(e)}")
        agent_output = AgentOutput(
            agent_name="document_quality_agent",
            status="error",
            tokens_used=0,
            usd_cost=0.0,
            timestamp=datetime.now(),
            data={"error": str(e)}
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "document_quality_score": 0.0,
            "validation_errors": state.validation_errors + [f"Quality assessment failed: {str(e)}"],
            "agent_outputs": agent_outputs
        }


def suggest_ocr_fallback(state: DocumentExtractionState) -> dict:
    """
    ROBUST ERROR HANDLING: If primary OCR fails, try alternative methods
    1. Tesseract OCR (open source)
    2. AWS Textract (cloud)
    3. Google Vision API (cloud)
    4. Manual entry workflow
    """
    try:
        fallback_methods = []
        
        if state.document_quality_score < 0.5:
            fallback_methods = [
                "Manual data entry recommended",
                "Request new document scan/photo",
                "Apply image preprocessing before retry"
            ]
        elif state.document_quality_score < 0.7:
            fallback_methods = [
                "Retry with AWS Textract (handles poor quality better)",
                "Apply image enhancement and retry",
                "Manual verification of extracted data required"
            ]
        else:
            fallback_methods = [
                "Retry OCR with different engine",
                "Spot-check extracted data against original"
            ]
        
        # Calculate cost
        input_tokens = 100
        output_tokens = 100
        cost = calculate_token_cost(input_tokens, output_tokens)
        
        print(f"[OCR_FALLBACK] TOKEN_COST_USD: ${cost:.6f}")
        print(f"[OCR_FALLBACK] Suggested methods: {len(fallback_methods)}")
        
        agent_output = AgentOutput(
            agent_name="ocr_fallback_agent",
            status="success",
            tokens_used=input_tokens + output_tokens,
            usd_cost=cost,
            timestamp=datetime.now(),
            data={"fallback_methods": fallback_methods}
        )
        
        agent_outputs = state.agent_outputs.copy()
        agent_outputs.append(agent_output)
        
        return {
            "agent_outputs": agent_outputs,
            "total_tokens": state.total_tokens + input_tokens + output_tokens,
            "total_cost": state.total_cost + cost
        }
        
    except Exception as e:
        print(f"[OCR_FALLBACK] ERROR: {str(e)}")
        return {"validation_errors": state.validation_errors + [f"Fallback suggestion failed: {str(e)}"]}
