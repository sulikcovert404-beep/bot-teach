from app.domain.school_class import (
    ClassMembership,
    Classroom,
    School,
    StudentProfile,
    TeacherProfile,
    can_access_class_content,
    can_publish_to_class,
    teacher_belongs_to_school,
)


def test_teacher_must_belong_to_school() -> None:
    teacher = TeacherProfile("t1", "s1")
    assert teacher_belongs_to_school(teacher, School("s1", "A"))
    assert not teacher_belongs_to_school(teacher, School("s2", "B"))


def test_membership_is_required_for_class_content() -> None:
    classroom = Classroom("c1", "s1", "t1")
    StudentProfile("u1")
    memberships = frozenset({ClassMembership("c1", "u1")})
    assert can_access_class_content(classroom=classroom, student_id="u1", memberships=memberships)
    assert not can_access_class_content(classroom=classroom, student_id="u2", memberships=memberships)


def test_teacher_can_publish_only_to_owned_school_class() -> None:
    teacher = TeacherProfile("t1", "s1")
    assert can_publish_to_class(teacher=teacher, classroom=Classroom("c1", "s1", "t1"))
    assert not can_publish_to_class(teacher=teacher, classroom=Classroom("c2", "s2", "t1"))
