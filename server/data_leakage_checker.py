import re
from presidio_analyzer import AnalyzerEngine


class DataLeakageDetector:
    """Detector for detecting data leakage and sensitive information."""

    def __init__(self):
        try:
            self.analyzer = AnalyzerEngine()
        except Exception as e:
            # If Presidio fails to initialize, fall back to regex-only checks
            print(f"Warning: Presidio Analyzer initialization failed: {e}")
            print("Falling back to regex-only security checks.")
            self.analyzer = None

    def check_data_leakage(
        self, data: str, entities: list[str] | None = None
    ) -> tuple[bool, str]:
        """Check if the data contains sensitive information.

        Uses both regex-based patterns and Presidio Analyzer for PII detection.

        Args:
            data: The data string to check.
            entities: Optional list of Presidio entity types to detect.
                     If None, detects all available entities.
                     Available types: CREDIT_CARD, EMAIL_ADDRESS, PHONE_NUMBER, PERSON,
                     LOCATION, DATE_TIME, IP_ADDRESS, URL, US_SSN, US_PASSPORT, etc.

        Returns:
            tuple[bool, str]: (is_safe, reason) - True if safe, False with reason if unsafe.
        """
        # First, check with regex-based patterns (fast, catches common patterns)
        is_safe, reason = self._check_regex_patterns(data)
        if not is_safe:
            return False, reason

        # Then, check with Presidio Analyzer if available (catches PII entities)
        if self.analyzer:
            is_safe, reason = self._check_with_presidio(data, entities=entities)
            if not is_safe:
                return False, reason

        return True, ""

    def _check_regex_patterns(self, data: str) -> tuple[bool, str]:
        """Check for sensitive patterns using regex.

        Args:
            data: The data string to check.

        Returns:
            tuple[bool, str]: (is_safe, reason) - True if safe, False with reason if unsafe.
        """
        # Common sensitive patterns (case-insensitive)
        sensitive_patterns = [
            (r"api[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{10,}", "API key detected"),
            (
                r"secret[_-]?key\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{10,}",
                "Secret key detected",
            ),
            (r"password\s*[:=]\s*['\"]?[^\s'\"<>]{6,}", "Password detected"),
            (r"token\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{20,}", "Token detected"),
            (r"credential\s*[:=]\s*['\"]?[a-zA-Z0-9_-]{10,}", "Credential detected"),
            (r"private[_-]?key\s*[:=]", "Private key detected"),
            (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key block detected"),
        ]

        for pattern, description in sensitive_patterns:
            if re.search(pattern, data, re.IGNORECASE):
                return False, f"Data leakage detected: {description}"

        return True, ""

    def _check_with_presidio(
        self, data: str, entities: list[str] | None = None
    ) -> tuple[bool, str]:
        """Check for PII using Presidio Analyzer.

        Args:
            data: The data string to check.
            entities: Optional list of entity types to detect. If None, detects all available entities.
                     Available entity types:
                     - CREDIT_CARD, CRYPTO, DATE_TIME, EMAIL_ADDRESS, IBAN_CODE, IP_ADDRESS
                     - LOCATION, MEDICAL_LICENSE, NRP, PERSON, PHONE_NUMBER, UK_NHS
                     - URL, US_BANK_NUMBER, US_DRIVER_LICENSE, US_ITIN, US_PASSPORT, US_SSN

        Returns:
            tuple[bool, str]: (is_safe, reason) - True if safe, False with reason if unsafe.
        """
        if not self.analyzer:
            return True, ""

        try:
            # Analyze the text for PII entities
            # If entities list is provided, only detect those specific types
            if entities:
                results = self.analyzer.analyze(
                    text=data, language="en", entities=entities
                )
            else:
                # Detect all available entities
                results = self.analyzer.analyze(text=data, language="en")

            if results:
                # Get unique entity types found
                entity_types = set(result.entity_type for result in results)
                entity_list = ", ".join(sorted(entity_types))
                return False, f"PII detected by Presidio Analyzer: {entity_list}"

            return True, ""
        except Exception as e:
            # If Presidio fails, log but don't block (fallback to regex only)
            print(f"Warning: Presidio Analyzer error: {e}")
            return True, ""


# Global instance
_data_leakage_checker = None


def get_data_leakage_detector() -> DataLeakageDetector:
    global _data_leakage_checker
    if _data_leakage_checker is None:
        _data_leakage_checker = DataLeakageDetector()
    return _data_leakage_checker


def detect_data_leakage(data: str, entities: list[str]) -> tuple[bool, str]:
    detector = get_data_leakage_detector()
    return detector.check_data_leakage(data, entities=entities)
