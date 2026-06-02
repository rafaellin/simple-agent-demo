"""Intent classification tool for approval/rejection responses."""

import json
import logging
from typing import Literal
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class IntentClassification:
    """Structured output from intent classifier."""
    intent: Literal["approve", "reject", "other"]
    confidence: float  # 0.0 to 1.0
    reason: str  # Brief explanation of classification


class IntentClassifier:
    """Classify user intent during approval checkpoints using LLM."""
    
    def __init__(self, llm):
        """
        Initialize classifier with an LLM instance.
        
        Args:
            llm: LangChain LLM instance (e.g., ChatOpenAI)
        """
        self.llm = llm
    
    def classify(self, message: str) -> IntentClassification:
        """
        Use LLM to classify if user is approving, rejecting, or saying something else.
        
        Args:
            message: User's text response to approval request
            
        Returns:
            IntentClassification with intent, confidence, and reason
        """
        try:
            # Use LLM to classify intent with structured JSON output
            classification_prompt = f"""Given this user message in response to a pending approval request, classify their intent.

User message: "{message}"

Respond with ONLY a JSON object (no markdown, no extra text):
{{
    "intent": "approve" or "reject" or "other",
    "confidence": 0.0 to 1.0,
    "reason": "brief explanation"
}}

Intent definitions:
- "approve" = user is confirming/approving the operation (yes, ok, absolutely, definitely, go ahead, proceed, allow, etc.)
- "reject" = user is denying/canceling the operation (no, nope, don't, cancel, abort, stop, deny, etc.)
- "other" = user said something else (alternative suggestions, questions, edits, etc.)

JSON:"""
            
            response = self.llm.invoke(classification_prompt)
            response_text = response.content.strip()
            
            # Parse JSON response
            try:
                result = json.loads(response_text)
                classification = IntentClassification(
                    intent=result.get("intent", "other"),
                    confidence=float(result.get("confidence", 0.5)),
                    reason=result.get("reason", "")
                )
                
                # Validate intent value
                if classification.intent not in ["approve", "reject", "other"]:
                    logger.warning(f"Invalid intent value: {classification.intent}, treating as 'other'")
                    classification.intent = "other"
                
                # Clamp confidence
                classification.confidence = max(0.0, min(1.0, classification.confidence))
                
                logger.debug(f"Classified '{message}' as {classification.intent} (confidence: {classification.confidence})")
                return classification
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {response_text}, error: {e}")
                return IntentClassification(
                    intent="other",
                    confidence=0.0,
                    reason="Failed to parse classifier response"
                )
        
        except Exception as e:
            logger.error(f"Error classifying user intent: {e}")
            return IntentClassification(
                intent="other",
                confidence=0.0,
                reason=f"Error: {str(e)}"
            )
