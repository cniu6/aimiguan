"""
AES-GCM 凭据加密存储服务。
支持 key_version，便于密钥轮换时旧密钥可解、新密钥重加密。
"""
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 密钥注册表：版本号 -> 32字节密钥（生产环境应从 Vault/HSM 获取）
_KEY_REGISTRY: dict[str, bytes] = {}
_CURRENT_VERSION = "v1"


def _ensure_keys():
    """初始化密钥。优先从环境变量读取，否则自动生成。"""
    global _CURRENT_VERSION
    if _KEY_REGISTRY:
        return

    env_key = os.getenv("CREDENTIAL_KEY_V1")
    if env_key:
        _KEY_REGISTRY["v1"] = base64.urlsafe_b64decode(env_key)
    else:
        _KEY_REGISTRY["v1"] = AESGCM.generate_key(bit_length=256)

    env_key_v2 = os.getenv("CREDENTIAL_KEY_V2")
    if env_key_v2:
        _KEY_REGISTRY["v2"] = base64.urlsafe_b64decode(env_key_v2)
        _CURRENT_VERSION = "v2"


def get_current_key_version() -> str:
    _ensure_keys()
    return _CURRENT_VERSION


def encrypt(plaintext: str) -> tuple[str, str]:
    """
    AES-256-GCM 加密。
    返回 (ciphertext_base64, key_version)
    """
    _ensure_keys()
    key = _KEY_REGISTRY[_CURRENT_VERSION]
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # 格式: nonce(12) + ciphertext+tag
    blob = nonce + ct
    return base64.urlsafe_b64encode(blob).decode("ascii"), _CURRENT_VERSION


def decrypt(ciphertext_b64: str, key_version: str) -> str:
    """
    AES-256-GCM 解密。
    根据 key_version 选择对应密钥。
    """
    _ensure_keys()
    key = _KEY_REGISTRY.get(key_version)
    if not key:
        raise ValueError(f"未知密钥版本: {key_version}")

    blob = base64.urlsafe_b64decode(ciphertext_b64)
    nonce = blob[:12]
    ct = blob[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ct, None)
    return plaintext.decode("utf-8")


def re_encrypt(ciphertext_b64: str, old_version: str) -> tuple[str, str]:
    """
    密钥轮换：用旧密钥解密，再用当前密钥重新加密。
    返回 (new_ciphertext_base64, new_key_version)
    """
    plaintext = decrypt(ciphertext_b64, old_version)
    return encrypt(plaintext)
