from client.jwt import create_jwt_token
import pytest
import jwt
from freezegun import freeze_time
import calendar
import time
import base64
import hmac
import hashlib
import json


def test_should_reject_token_request_if_missing_request_method():
    with pytest.raises(AssertionError) as err:
        create_jwt_token(None, "path", "key", "client_id", "body")
    assert str(err.value) == "Missing request method"


def test_should_reject_token_request_if_missing_request_path():
    with pytest.raises(AssertionError) as err:
        create_jwt_token("method", None, "key", "client_id", "body")
    assert str(err.value) == "Missing request path"


def test_should_reject_token_request_if_missing_secret():
    with pytest.raises(AssertionError) as err:
        create_jwt_token("method", "path", None, "client_id", "body")
    assert str(err.value) == "Missing secret key"


def test_should_reject_token_request_if_missing_client_id():
    with pytest.raises(AssertionError) as err:
        create_jwt_token("method", "path", "key", None, "body")
    assert str(err.value) == "Missing client id"


def test_token_should_contain_correct_headers():
    token = create_jwt_token("method", "path", "key", "client_id", "body")
    headers = jwt.get_unverified_header(token)
    assert headers['typ'] == 'JWT'
    assert headers['alg'] == 'HS256'


def test_token_should_fail_to_decode_if_wrong_key():
    token = create_jwt_token("method", "path", "key", "client_id", "body")
    with pytest.raises(jwt.DecodeError) as err:
        decode_token(token, "wrong key")
    assert str(err.value) == "Signature verification failed"


def test_token_should_contain_correct_claim_keys():
    token = create_jwt_token("method", "path", "key", "client_id", "body")
    decoded = decode_token(token, "key")
    assert 'iss' in decoded
    assert 'iat' in decoded
    assert 'req' in decoded
    assert 'pay' in decoded


def test_token_should_contain_correct_client_claim():
    token = create_jwt_token("method", "path", "key", "client_id", "body")
    decoded = decode_token(token, "key")
    assert decoded['iss'] == 'client_id'


@freeze_time("2020-01-01 00:00:00")
def test_token_should_contain_correct_issued_at_claim():
    token = create_jwt_token("method", "path", "key", "client_id", "body")
    decoded = decode_token(token, "key")
    assert decoded['iat'] == calendar.timegm(time.gmtime())


def test_token_should_contain_correct_request_claim():
    token = create_jwt_token("POST", "/my-resource", "key", "client_id", "body")
    decoded = decode_token(token, "key")
    expected_request = base64.b64encode(
        hmac.new(
            "key".encode(),
            "POST /my-resource".encode(),
            digestmod=hashlib.sha256
        ).digest())
    assert decoded['req'] == expected_request.decode()


def test_token_should_contain_correct_request_body():
    token = create_jwt_token("POST", "/my-resource", "key", "client_id", "body")
    decoded = decode_token(token, "key")
    expected_request = base64.b64encode(
        hmac.new(
            "key".encode(),
            "body".encode(),
            digestmod=hashlib.sha256
        ).digest())
    assert decoded['pay'] == expected_request.decode()


def test_token_should_contain_correct_request_json_body():
    complex_json = {
        "a": "1234",
        "b": 1234,
        "c": [
            1, 2, 3, 4
        ],
        "d": {
            "1": 1,
            "2": "2"
        }
    }
    serialized_json = json.dumps(complex_json)
    token = create_jwt_token("POST", "/my-resource", "key", "client_id", serialized_json)
    decoded = decode_token(token, "key")
    expected_request = base64.b64encode(
        hmac.new(
            "key".encode(),
            serialized_json.encode(),
            digestmod=hashlib.sha256
        ).digest())
    assert decoded['pay'] == expected_request.decode()


def test_token_should_allow_no_body():
    token = create_jwt_token("POST", "/my-resource", "key", "client_id", None)
    decoded = decode_token(token, "key")
    assert 'pay' not in decoded


def decode_token(token, secret):
    return jwt.decode(token, key=secret.encode(), verify=True, algorithms=['HS256'])
