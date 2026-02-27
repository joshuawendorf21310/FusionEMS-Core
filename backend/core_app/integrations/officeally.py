from __future__ import annotations

import io
from dataclasses import dataclass

import paramiko


@dataclass(frozen=True)
class OfficeAllySftpConfig:
    host: str
    port: int
    username: str
    password: str
    remote_dir: str = "/"


class OfficeAllyClientError(RuntimeError):
    pass


def submit_837_via_sftp(*, cfg: OfficeAllySftpConfig, file_name: str, x12_bytes: bytes) -> str:
    """
    Uploads an 837 X12 file to an SFTP server (Office Ally-style connectivity).
    This is a generic SFTP uploader; the correct remote directory and credentials must
    be provisioned by the trading partner relationship.
    Returns the remote path uploaded.
    """
    if not cfg.host or not cfg.username or not cfg.password:
        raise OfficeAllyClientError("office_ally_sftp_not_configured")

    transport = paramiko.Transport((cfg.host, cfg.port))
    try:
        transport.connect(username=cfg.username, password=cfg.password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        try:
            remote_path = f"{cfg.remote_dir.rstrip('/')}/{file_name}"
            with io.BytesIO(x12_bytes) as bio:
                sftp.putfo(bio, remote_path)
            return remote_path
        finally:
            try:
                sftp.close()
            except Exception:
                pass
    finally:
        try:
            transport.close()
        except Exception:
            pass
