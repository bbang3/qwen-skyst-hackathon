"""Prompt injection checker module for detecting prompt injection attempts.

This module provides regex-based detection for common prompt injection patterns.
"""

import re


class PromptInjectionChecker:
    """Checker for detecting prompt injection attempts."""

    def check_prompt_injection(self, data: str) -> tuple[bool, str]:
        """Check if the data contains prompt injection attempts.

        Args:
            data: The data string to check.

        Returns:
            tuple[bool, str]: (is_safe, reason) - True if safe, False with reason if unsafe.
        """
        # Regex-based prompt injection detection
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"forget\s+everything",
            r"you\s+are\s+now",
            r"system\s*:",
            r"assistant\s*:",
            r"user\s*:",
            r"override",
            r"bypass",
            r"jailbreak",
            r"ignore\s+all\s+previous",
            r"disregard\s+previous",
            r"new\s+instructions",
            r"act\s+as\s+if",
            r"pretend\s+to\s+be",
            r"roleplay",
            r"simulate",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                return (
                    False,
                    f"Potential prompt injection detected: matches pattern '{pattern}'",
                )

        return True, ""


# Global instance
_prompt_injection_checker = None


def get_prompt_injection_checker() -> PromptInjectionChecker:
    """Get or create the global PromptInjectionChecker instance.

    Returns:
        PromptInjectionChecker: The prompt injection checker instance.
    """
    global _prompt_injection_checker
    if _prompt_injection_checker is None:
        _prompt_injection_checker = PromptInjectionChecker()
    return _prompt_injection_checker


def check_prompt_injection(data: str) -> tuple[bool, str]:
    """Check if the data contains prompt injection attempts.

    Convenience function that uses the global PromptInjectionChecker instance.

    Args:
        data: The data string to check.

    Returns:
        tuple[bool, str]: (is_safe, reason) - True if safe, False with reason if unsafe.
    """
    checker = get_prompt_injection_checker()
    return checker.check_prompt_injection(data)
