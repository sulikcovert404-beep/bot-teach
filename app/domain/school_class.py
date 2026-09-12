"""Pure School/Class domain contracts; persistence adapters are out of scope."""
from dataclasses import dataclass


@dataclass(frozen=True)
class School:
    school_id: str
    name: str


@dataclass(frozen=True)
class TeacherProfile:
    teacher_id: str
    school_id: str


@dataclass(frozen=True)
class StudentProfile:
    student_id: str


@dataclass(frozen=True)
class Classroom:
    classroom_id: str
    school_id: str
    teacher_id: str


@dataclass(frozen=True)
class ClassMembership:
    classroom_id: str
    student_id: str


def teacher_belongs_to_school(teacher: TeacherProfile, school: School) -> bool:
    return teacher.school_id == school.school_id


def can_access_class_content(*, classroom: Classroom, student_id: str, memberships: frozenset[ClassMembership]) -> bool:
    return any(m.classroom_id == classroom.classroom_id and m.student_id == student_id for m in memberships)


def can_publish_to_class(*, teacher: TeacherProfile, classroom: Classroom) -> bool:
    return teacher.teacher_id == classroom.teacher_id and teacher.school_id == classroom.school_id
