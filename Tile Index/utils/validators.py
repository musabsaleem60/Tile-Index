"""
Validation utilities
"""


def validate_positive_number(value, field_name="Value"):
    """Validate that a value is a positive number"""
    try:
        num = float(value)
        if num < 0:
            raise ValueError(f"{field_name} cannot be negative")
        return num
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid number")


def validate_integer(value, field_name="Value", min_value=0):
    """Validate that a value is a non-negative integer"""
    try:
        num = int(value)
        if num < min_value:
            raise ValueError(f"{field_name} must be at least {min_value}")
        return num
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid integer")


def validate_required(value, field_name="Field"):
    """Validate that a required field is not empty"""
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field_name} is required")
    return value.strip() if isinstance(value, str) else value


def validate_grade(grade):
    """Validate that grade is valid"""
    from utils.grade_constants import VALID_GRADES, GRADE_MAPPING, normalize_grade
    
    # Normalize old format to new format
    normalized = normalize_grade(grade)
    
    if normalized not in VALID_GRADES:
        raise ValueError(f"Grade must be one of: {', '.join(VALID_GRADES)}")
    return normalized

