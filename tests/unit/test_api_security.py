from services.query.handler import lambda_handler


def test_query_handler_rejects_missing_jwt_claims() -> None:
    response = lambda_handler({"body": '{"question":"valid question"}'}, None)
    assert response["statusCode"] == 401
    assert response["headers"]["cache-control"] == "no-store"
