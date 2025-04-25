from dataclasses import dataclass
from typing import Optional


@dataclass
class StudentInfo:
    myedu_id: int
    full_name: Optional[str]
    faculty: Optional[str]
    faculty_id: Optional[int]
    specialty: Optional[str]
    specialty_id: Optional[int]
