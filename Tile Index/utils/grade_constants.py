"""
Grade Constants
Centralized grade definitions for the system
"""

# Grade definitions
GRADE_1 = "Grade 1 (Prime)"
GRADE_2 = "Grade 2 (Standard)"
GRADE_3 = "Grade 3 (Regular)"

# List of all valid grades
VALID_GRADES = [GRADE_1, GRADE_2, GRADE_3]

# Grade mapping for backward compatibility (old -> new)
GRADE_MAPPING = {
    'G1': GRADE_1,
    'G2': GRADE_2,
    'G3': GRADE_3
}

# Reverse mapping (new -> old) for display purposes if needed
REVERSE_GRADE_MAPPING = {v: k for k, v in GRADE_MAPPING.items()}


def get_grade_display_name(grade):
    """Get display name for grade"""
    return grade  # Already in display format


def normalize_grade(grade):
    """Normalize grade (convert old format to new if needed)"""
    if grade in GRADE_MAPPING:
        return GRADE_MAPPING[grade]
    return grade


def is_valid_grade(grade):
    """Check if grade is valid"""
    return grade in VALID_GRADES or grade in GRADE_MAPPING

