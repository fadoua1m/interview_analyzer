import enum

class SeniorityLevel(str, enum.Enum):
    JUNIOR = "junior"
    MID    = "mid"
    SENIOR = "senior"
    LEAD   = "lead"