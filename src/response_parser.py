import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ResponseParser:
    """
    Parses teacher outputs of the form:

    Problem: <text>
    Reasoning: <text>
    Final Answer: <int>

    Returns a dict with keys: problem, reasoning, final_answer.

    Design goals:
    - strict by default (good for dataset quality)
    - minimal heuristics to salvage common formatting issues
    """

    _SECTION_RE = re.compile(
        r"(?is)"                       # i=case-insensitive, s=dot matches newline
        r"Problem:\s*(.*?)\s*"
        r"Reasoning:\s*(.*?)\s*"
        r"Final Answer:\s*([+-]?\d+)\s*$"
    )

    # Backup regex if model adds trailing text after the number
    _FINAL_ANSWER_RE = re.compile(r"(?is)Final Answer:\s*([+-]?\d+)")

    def parse(self, raw_text: str, strict: bool = True) -> Optional[Dict[str, Any]]:
        """
        Args:
            raw_text: The teacher's raw response.
            strict: If True, require full section match.
                    If False, attempt best-effort extraction.

        Returns:
            dict or None if parsing fails.
        """
        if not raw_text or not raw_text.strip():
            logger.warning("Empty raw_text; cannot parse.")
            return None

        text = raw_text.strip()

        text = re.sub(r"(?i)\bfinal\s*answer\b", "Final Answer", text)
        text = re.sub(r"(?i)\breasoning\b", "Reasoning", text)
        text = re.sub(r"(?i)\bproblem\b", "Problem", text)

        m = self._SECTION_RE.match(text)
        if m:
            problem = m.group(1).strip()
            reasoning = m.group(2).strip()
            final_answer_str = m.group(3).strip()

            try:
                final_answer = int(final_answer_str)
            except ValueError:
                logger.error(f"Final answer not an int: {final_answer_str!r}")
                return None

            if strict:
                if not problem or not reasoning:
                    logger.warning(f"Strict parse failed: missing probem or reasoning.")
                    return None
                
            return {
                "problem": problem,
                "reasoning": reasoning,
                "final_answer": final_answer
            }
        
        if strict:
            logger.warning(f"Strict parsing failed. Head: {text[:120]!r}")
            return None

        # Best effort fallback:
        # try to at least find "final asnwer" and split around markers
        ans_m = self._FINAL_ANSWER_RE.search(text)
        if not ans_m:
            logger.warning(f"Best-effort parsing failed: no Final Answer found")
            return None
        
        try:
            final_answer = int(ans_m.group(1).strip())
        except ValueError:
            logger.error(f"Best-effor parsing failed: final asnwer not int.")
            return None

        # Attempt to carve out sections by the first occurrence of markers
        # This is not perfect but best we can do for malformed sentences
        problem = ""
        reasoning = ""

        # Split on Reasoning:
        parts = re.split(r"(?i)\bReasoning:\s*", text, maxsplit=1)
        if len(parts) == 2:
            before_reasoning, after_reasoning = parts
            # Extract problem from before_reasoning after "Problem:"
            p2 = re.split(r"(?i)\bProblem:\s*", before_reasoning, maxsplit=1)
            if len(p2) == 2:
                problem = p2[1].strip()

            # Remove final answer section from reasoning block
            reasoning = re.split(r"(?i)\bFinal Answer:\s*", after_reasoning, maxsplit=1)[0].strip()
        else:
            # Could not find Reasoning marker; treat everything before Final Answer as "problem"
            problem = re.split(r"(?i)\bFinal Answer:\s*", text, maxsplit=1)[0].strip()

        return {
            "problem": problem,
            "reasoning": reasoning,
            "final_answer": final_answer,
        }
