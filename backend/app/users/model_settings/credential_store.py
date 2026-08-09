from __future__ import annotations

import ctypes
import hashlib
import os
import sys
from ctypes import wintypes
from pathlib import Path
from uuid import uuid4


class CredentialStoreUnavailable(RuntimeError):
    pass


class CredentialStoreOperationError(RuntimeError):
    pass


class UnavailableCredentialStore:
    def _raise(self) -> None:
        raise CredentialStoreUnavailable(
            "No supported operating-system credential store is configured"
        )

    def get(self, _subject: str) -> str | None:
        self._raise()

    def put(self, _subject: str, _secret: str) -> None:
        self._raise()

    def delete(self, _subject: str) -> bool:
        self._raise()


if sys.platform == "win32":
    LPBYTE = ctypes.POINTER(wintypes.BYTE)

    class _CredentialAttribute(ctypes.Structure):
        _fields_ = [
            ("Keyword", wintypes.LPWSTR),
            ("Flags", wintypes.DWORD),
            ("ValueSize", wintypes.DWORD),
            ("Value", LPBYTE),
        ]

    class _Credential(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", wintypes.FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", LPBYTE),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.POINTER(_CredentialAttribute)),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    _PCREDENTIAL = ctypes.POINTER(_Credential)

    class _DataBlob(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", LPBYTE),
        ]


class WindowsCredentialStore:
    """Persists API keys in the current Windows account's Credential Manager."""

    _CRED_TYPE_GENERIC = 1
    _CRED_PERSIST_LOCAL_MACHINE = 2
    _ERROR_NOT_FOUND = 1168

    def __init__(self, service_name: str = "AI Nav Agent Model"):
        if sys.platform != "win32":
            raise CredentialStoreUnavailable("Windows Credential Manager is unavailable")
        self._service_name = service_name
        self._advapi32 = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._advapi32.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
        self._advapi32.CredWriteW.restype = wintypes.BOOL
        self._advapi32.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(_PCREDENTIAL),
        ]
        self._advapi32.CredReadW.restype = wintypes.BOOL
        self._advapi32.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._advapi32.CredDeleteW.restype = wintypes.BOOL
        self._advapi32.CredFree.argtypes = [wintypes.LPVOID]
        self._advapi32.CredFree.restype = None

    def _target(self, subject: str) -> str:
        digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()
        return f"{self._service_name}/{digest}"

    def get(self, subject: str) -> str | None:
        result = _PCREDENTIAL()
        if not self._advapi32.CredReadW(
            self._target(subject), self._CRED_TYPE_GENERIC, 0, ctypes.byref(result)
        ):
            error = ctypes.get_last_error()
            if error == self._ERROR_NOT_FOUND:
                return None
            raise CredentialStoreOperationError(f"Credential read failed ({error})")
        try:
            credential = result.contents
            raw = ctypes.string_at(
                credential.CredentialBlob,
                credential.CredentialBlobSize,
            )
            return raw.decode("utf-16-le")
        finally:
            self._advapi32.CredFree(result)

    def put(self, subject: str, secret: str) -> None:
        raw = secret.encode("utf-16-le")
        blob = ctypes.create_string_buffer(raw)
        credential = _Credential()
        credential.Type = self._CRED_TYPE_GENERIC
        credential.TargetName = self._target(subject)
        credential.CredentialBlobSize = len(raw)
        credential.CredentialBlob = ctypes.cast(blob, LPBYTE)
        credential.Persist = self._CRED_PERSIST_LOCAL_MACHINE
        credential.UserName = "agent-model-api-key"
        if not self._advapi32.CredWriteW(ctypes.byref(credential), 0):
            raise CredentialStoreOperationError(
                f"Credential write failed ({ctypes.get_last_error()})"
            )

    def delete(self, subject: str) -> bool:
        if self._advapi32.CredDeleteW(
            self._target(subject), self._CRED_TYPE_GENERIC, 0
        ):
            return True
        error = ctypes.get_last_error()
        if error == self._ERROR_NOT_FOUND:
            return False
        raise CredentialStoreOperationError(f"Credential delete failed ({error})")


class WindowsDpapiCredentialStore:
    """Stores per-user DPAPI-sealed blobs outside the application database."""

    _CRYPTPROTECT_UI_FORBIDDEN = 0x1

    def __init__(self, directory: Path | str | None = None):
        if sys.platform != "win32":
            raise CredentialStoreUnavailable("Windows DPAPI is unavailable")
        local_app_data = os.getenv("LOCALAPPDATA", "").strip()
        if directory is None and not local_app_data:
            raise CredentialStoreUnavailable("LOCALAPPDATA is unavailable")
        self._directory = Path(directory) if directory else Path(local_app_data) / "AI Nav" / "credentials"
        self._crypt32 = ctypes.WinDLL("Crypt32.dll", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("Kernel32.dll", use_last_error=True)
        self._crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(_DataBlob),
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptProtectData.restype = wintypes.BOOL
        self._crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(_DataBlob),
            wintypes.LPVOID,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(_DataBlob),
        ]
        self._crypt32.CryptUnprotectData.restype = wintypes.BOOL
        self._kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        self._kernel32.LocalFree.restype = wintypes.HLOCAL

    def _path(self, subject: str) -> Path:
        digest = hashlib.sha256(subject.encode("utf-8")).hexdigest()
        return self._directory / f"{digest}.credential"

    @staticmethod
    def _input_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array]:
        buffer = ctypes.create_string_buffer(data)
        return _DataBlob(len(data), ctypes.cast(buffer, LPBYTE)), buffer

    def _protect(self, data: bytes) -> bytes:
        source, source_buffer = self._input_blob(data)
        output = _DataBlob()
        if not self._crypt32.CryptProtectData(
            ctypes.byref(source),
            "AI Nav user model API key",
            None,
            None,
            None,
            self._CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output),
        ):
            raise CredentialStoreOperationError(
                f"DPAPI protect failed ({ctypes.get_last_error()})"
            )
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            self._kernel32.LocalFree(ctypes.cast(output.pbData, wintypes.HLOCAL))
            del source_buffer

    def _unprotect(self, data: bytes) -> bytes:
        source, source_buffer = self._input_blob(data)
        output = _DataBlob()
        if not self._crypt32.CryptUnprotectData(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            self._CRYPTPROTECT_UI_FORBIDDEN,
            ctypes.byref(output),
        ):
            raise CredentialStoreOperationError(
                f"DPAPI unprotect failed ({ctypes.get_last_error()})"
            )
        try:
            return ctypes.string_at(output.pbData, output.cbData)
        finally:
            self._kernel32.LocalFree(ctypes.cast(output.pbData, wintypes.HLOCAL))
            del source_buffer

    def get(self, subject: str) -> str | None:
        path = self._path(subject)
        if not path.exists():
            return None
        try:
            return self._unprotect(path.read_bytes()).decode("utf-8")
        except OSError as exc:
            raise CredentialStoreOperationError("Credential file read failed") from exc

    def put(self, subject: str, secret: str) -> None:
        try:
            self._directory.mkdir(parents=True, exist_ok=True)
            path = self._path(subject)
            temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
            try:
                temporary.write_bytes(self._protect(secret.encode("utf-8")))
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
        except OSError as exc:
            raise CredentialStoreOperationError("Credential file write failed") from exc

    def delete(self, subject: str) -> bool:
        path = self._path(subject)
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise CredentialStoreOperationError("Credential file delete failed") from exc


def create_platform_credential_store():
    backend = os.getenv(
        "AI_NAV_AGENT_CREDENTIAL_STORE",
        "windows_dpapi" if sys.platform == "win32" else "unconfigured",
    ).strip().lower()
    if backend == "windows_dpapi" and sys.platform == "win32":
        directory = os.getenv("AI_NAV_AGENT_CREDENTIAL_DIR", "").strip() or None
        return WindowsDpapiCredentialStore(directory)
    if backend == "windows_credential_manager" and sys.platform == "win32":
        return WindowsCredentialStore()
    return UnavailableCredentialStore()
