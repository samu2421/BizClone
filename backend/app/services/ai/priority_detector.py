"""
Priority Detection Service for identifying emergency situations.

Scans transcripts for emergency keywords and patterns to automatically
flag urgent calls that need immediate attention.
"""
import re
from typing import List, Optional
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PriorityResult:
    """Result of priority detection."""
    is_emergency: bool
    urgency_level: str  # "low", "medium", "high", "urgent", "emergency"
    confidence: float  # 0.0 to 1.0
    detected_keywords: List[str]
    reason: str


class PriorityDetector:
    """
    Detects emergency situations and urgency levels from transcript text.
    
    Uses keyword matching and pattern recognition to identify:
    - Emergency situations (flooding, burst pipes, gas leaks)
    - High urgency (water damage, no water, backed up sewage)
    - Medium urgency (slow drains, minor leaks)
    - Low urgency (routine maintenance, questions)
    """
    
    # Emergency keywords (immediate response needed)
    EMERGENCY_KEYWORDS = {
        "flooding", "flood", "flooded",
        "burst pipe", "burst", "bursting",
        "water everywhere", "water pouring",
        "gas leak", "smell gas", "gas smell",
        "no water", "water shut off",
        "sewage backup", "sewage", "raw sewage",
        "ceiling leak", "ceiling dripping",
        "major leak", "massive leak",
        "emergency", "urgent", "asap", "immediately",
        "right now", "help", "disaster",
    }
    
    # High urgency keywords (same day response)
    HIGH_URGENCY_KEYWORDS = {
        "leak", "leaking", "leaky",
        "dripping", "drip",
        "clogged", "clog", "blocked",
        "backed up", "backup",
        "overflow", "overflowing",
        "water damage", "damage",
        "broken", "broke",
        "not working", "doesn't work",
        "today", "this morning", "this afternoon",
    }
    
    # Medium urgency keywords (within a few days)
    MEDIUM_URGENCY_KEYWORDS = {
        "slow drain", "slow", "sluggish",
        "running toilet", "toilet running",
        "dripping faucet", "faucet drip",
        "minor", "small",
        "this week", "soon", "when you can",
    }
    
    # Low urgency keywords (routine/questions)
    LOW_URGENCY_KEYWORDS = {
        "question", "wondering", "curious",
        "estimate", "quote", "price", "cost",
        "schedule", "appointment", "availability",
        "maintenance", "inspection", "checkup",
        "next week", "next month", "whenever",
        "no rush", "not urgent",
    }
    
    def __init__(self):
        """Initialize the priority detector."""
        logger.info("priority_detector_initialized")
    
    def detect(
        self,
        text: str,
        intent: Optional[str] = None
    ) -> PriorityResult:
        """
        Detect priority level from transcript text.
        
        Args:
            text: Transcript text to analyze
            intent: Optional intent classification to consider
            
        Returns:
            PriorityResult: Detection results with urgency level
            
        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        text_lower = text.lower()
        
        # Check for emergency keywords
        emergency_matches = self._find_keywords(
            text_lower,
            self.EMERGENCY_KEYWORDS
        )
        
        # Check for high urgency keywords
        high_urgency_matches = self._find_keywords(
            text_lower,
            self.HIGH_URGENCY_KEYWORDS
        )
        
        # Check for medium urgency keywords
        medium_urgency_matches = self._find_keywords(
            text_lower,
            self.MEDIUM_URGENCY_KEYWORDS
        )
        
        # Check for low urgency keywords
        low_urgency_matches = self._find_keywords(
            text_lower,
            self.LOW_URGENCY_KEYWORDS
        )
        
        # Determine urgency level based on matches
        if emergency_matches or intent == "emergency":
            urgency_level = "emergency"
            is_emergency = True
            confidence = min(1.0, 0.7 + (len(emergency_matches) * 0.1))
            detected_keywords = emergency_matches
            reason = self._build_reason(emergency_matches, "emergency")
        elif high_urgency_matches:
            urgency_level = "urgent" if len(high_urgency_matches) >= 2 else "high"
            is_emergency = False
            confidence = min(1.0, 0.6 + (len(high_urgency_matches) * 0.1))
            detected_keywords = high_urgency_matches
            reason = self._build_reason(high_urgency_matches, urgency_level)
        elif medium_urgency_matches:
            urgency_level = "medium"
            is_emergency = False
            confidence = 0.5 + (len(medium_urgency_matches) * 0.05)
            detected_keywords = medium_urgency_matches
            reason = self._build_reason(medium_urgency_matches, "medium")
        elif low_urgency_matches:
            urgency_level = "low"
            is_emergency = False
            confidence = 0.4 + (len(low_urgency_matches) * 0.05)
            detected_keywords = low_urgency_matches
            reason = self._build_reason(low_urgency_matches, "low")
        else:
            # Default to medium if no clear indicators
            urgency_level = "medium"
            is_emergency = False
            confidence = 0.3
            detected_keywords = []
            reason = "No specific urgency indicators found"

        logger.info(
            "priority_detected",
            urgency_level=urgency_level,
            is_emergency=is_emergency,
            confidence=confidence,
            keyword_count=len(detected_keywords)
        )

        return PriorityResult(
            is_emergency=is_emergency,
            urgency_level=urgency_level,
            confidence=confidence,
            detected_keywords=detected_keywords,
            reason=reason
        )

    def _find_keywords(
        self,
        text: str,
        keywords: set
    ) -> List[str]:
        """
        Find matching keywords in text.

        Args:
            text: Text to search (should be lowercase)
            keywords: Set of keywords to find

        Returns:
            List[str]: List of matched keywords
        """
        matches = []
        for keyword in keywords:
            # Use word boundaries for better matching
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text):
                matches.append(keyword)
        return matches

    def _build_reason(
        self,
        keywords: List[str],
        level: str
    ) -> str:
        """
        Build a human-readable reason for the urgency level.

        Args:
            keywords: Detected keywords
            level: Urgency level

        Returns:
            str: Reason string
        """
        if not keywords:
            return f"Classified as {level} priority"

        if len(keywords) == 1:
            return f"Detected '{keywords[0]}' indicating {level} priority"
        elif len(keywords) <= 3:
            keyword_str = "', '".join(keywords)
            return f"Detected keywords: '{keyword_str}' indicating {level} priority"
        else:
            keyword_str = "', '".join(keywords[:3])
            return (
                f"Detected multiple keywords including '{keyword_str}' "
                f"indicating {level} priority"
            )

    def should_escalate(self, result: PriorityResult) -> bool:
        """
        Determine if the call should be escalated to human.

        Args:
            result: Priority detection result

        Returns:
            bool: True if should escalate
        """
        return result.is_emergency or (
            result.urgency_level == "urgent" and result.confidence > 0.7
        )

