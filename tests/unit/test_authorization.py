from services.query.authorization import AuthorizationContext


def test_department_filter_is_secure_by_default() -> None:
    anonymous_department = AuthorizationContext(subject="u1", groups=frozenset())
    assert anonymous_department.retrieval_filter() == {
        "equals": {"key": "confidentiality", "value": "public"}
    }
    assert (
        anonymous_department.can_read(confidentiality="internal", departments=["commercial"])
        is False
    )


def test_admin_is_unfiltered() -> None:
    admin = AuthorizationContext(subject="u1", groups=frozenset({"admin"}))
    assert admin.retrieval_filter() is None
    assert admin.can_read(confidentiality="restricted", departments=["finance"]) is True


def test_department_member_can_read_internal_document() -> None:
    commercial = AuthorizationContext(subject="u1", groups=frozenset({"commercial"}))
    assert commercial.can_read(confidentiality="internal", departments=["commercial"]) is True
    assert commercial.can_read(confidentiality="restricted", departments=["commercial"]) is False
    assert commercial.retrieval_filter() == {
        "orAll": [
            {"equals": {"key": "confidentiality", "value": "public"}},
            {
                "andAll": [
                    {"equals": {"key": "confidentiality", "value": "internal"}},
                    {"listContains": {"key": "departments", "value": "commercial"}},
                ]
            },
        ]
    }
