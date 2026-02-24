from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(slots=True)
class EncryptedPayload:
    ciphertext: bytes
    encrypted_data_key: bytes
    nonce_b64: str
    key_id: str
    encryption_context: dict[str, str]


class Encryptor(Protocol):
    def encrypt_json(self, *, payload: dict, encryption_context: dict[str, str]) -> EncryptedPayload: ...

    def decrypt_json(self, *, encrypted_payload: EncryptedPayload) -> dict: ...


class FakeEncryptor:
    def encrypt_json(self, *, payload: dict, encryption_context: dict[str, str]) -> EncryptedPayload:
        serialized = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return EncryptedPayload(
            ciphertext=serialized[::-1],
            encrypted_data_key=b"fake-encrypted-key",
            nonce_b64=base64.b64encode(b"fake-nonce").decode("utf-8"),
            key_id="fake-kms-key",
            encryption_context=encryption_context,
        )

    def decrypt_json(self, *, encrypted_payload: EncryptedPayload) -> dict:
        return json.loads(encrypted_payload.ciphertext[::-1].decode("utf-8"))


class KmsEnvelopeEncryptor:
    def __init__(self, *, kms_key_id: str, region_name: str) -> None:
        import boto3

        self.kms_key_id = kms_key_id
        self.client = boto3.client("kms", region_name=region_name)

    def encrypt_json(self, *, payload: dict, encryption_context: dict[str, str]) -> EncryptedPayload:
        data_key_response = self.client.generate_data_key(
            KeyId=self.kms_key_id,
            KeySpec="AES_256",
            EncryptionContext=encryption_context,
        )
        plaintext_data_key = data_key_response["Plaintext"]
        encrypted_data_key = data_key_response["CiphertextBlob"]

        nonce = os.urandom(12)
        aesgcm = AESGCM(plaintext_data_key)
        serialized = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        ciphertext = aesgcm.encrypt(nonce, serialized, None)
        return EncryptedPayload(
            ciphertext=ciphertext,
            encrypted_data_key=encrypted_data_key,
            nonce_b64=base64.b64encode(nonce).decode("utf-8"),
            key_id=self.kms_key_id,
            encryption_context=encryption_context,
        )

    def decrypt_json(self, *, encrypted_payload: EncryptedPayload) -> dict:
        decrypt_response = self.client.decrypt(
            CiphertextBlob=encrypted_payload.encrypted_data_key,
            EncryptionContext=encrypted_payload.encryption_context,
        )
        plaintext_data_key = decrypt_response["Plaintext"]
        aesgcm = AESGCM(plaintext_data_key)
        nonce = base64.b64decode(encrypted_payload.nonce_b64)
        plaintext = aesgcm.decrypt(nonce, encrypted_payload.ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))
