from src.services import webhook


def test_valid_signature_is_accepted():
    body = b'{"indicators": []}'
    assert webhook.verify_signature(body, webhook.expected_signature(body))


def test_tampered_body_is_rejected():
    body = b'{"indicators": []}'
    signature = webhook.expected_signature(body)
    assert not webhook.verify_signature(b'{"indicators": [1]}', signature)


def test_wrong_signature_is_rejected():
    assert not webhook.verify_signature(b"anything", "0" * 64)
