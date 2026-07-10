from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field

from app.api.v1.routers.auth import ensure_username_available, get_current_user, hash_security_answer, normalize_username
from app.api.v1.routers.auth import validate_password_strength
from app.core.config import AVATAR_MAX_DIMENSION, AVATAR_MAX_OUTPUT_BYTES, AVATAR_MAX_UPLOAD_BYTES, UPLOAD_DIR
from app.core.security import hash_password, random_uid, verify_password
from app.db.database import db_cursor

router = APIRouter(prefix="/users", tags=["users"])

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
ALLOWED_AVATAR_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}


class AccountUpdate(BaseModel):
    username: str = Field(min_length=3, max_length=32)


class PasswordUpdate(BaseModel):
    currentPassword: str = Field(min_length=8, max_length=128)
    newPassword: str = Field(min_length=8, max_length=128)


class ProfileUpdate(BaseModel):
    displayName: str | None = Field(default=None, min_length=1, max_length=40)
    avatarUrl: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=300)
    roleTitle: str | None = Field(default=None, max_length=60)
    learningLevel: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    targetDirection: str | None = Field(default=None, max_length=80)


class PreferencesUpdate(BaseModel):
    theme: str | None = Field(default=None, pattern="^(light|dark|system)$")
    language: str | None = Field(default=None, max_length=20)
    cnFirst: bool | None = None
    freeFirst: bool | None = None
    showExternalResources: bool | None = None
    agentMemoryEnabled: bool | None = None


class SecurityQuestionItem(BaseModel):
    question: str = Field(min_length=2, max_length=80)
    answer: str = Field(min_length=2, max_length=80)


class SecurityQuestionsUpdate(BaseModel):
    currentPassword: str = Field(min_length=8, max_length=128)
    items: list[SecurityQuestionItem] = Field(min_length=1, max_length=3)


def _account(row: dict) -> dict:
    return {
        "userUid": row["user_uid"],
        "username": row["username"],
        "email": row["email"],
        "phone": row["phone"],
        "accountStatus": row["account_status"],
        "updatedAt": row["updated_at"],
    }


def _profile(row: dict) -> dict:
    return {
        "displayName": row["display_name"],
        "avatarUrl": row["avatar_url"],
        "bio": row["bio"],
        "roleTitle": row["role_title"],
        "learningLevel": row["learning_level"],
        "targetDirection": row["target_direction"],
        "updatedAt": row["updated_at"],
    }


def _preferences(row: dict) -> dict:
    return {
        "theme": row["theme"],
        "language": row["language"],
        "cnFirst": bool(row["cn_first"]),
        "freeFirst": bool(row["free_first"]),
        "showExternalResources": bool(row["show_external_resources"]),
        "agentMemoryEnabled": bool(row["agent_memory_enabled"]),
        "preferenceJson": row["preference_json"],
        "updatedAt": row["updated_at"],
    }


def _load_profile(cur, user_id: int) -> dict:
    profile = cur.execute(
        """
        SELECT display_name, avatar_url, bio, role_title, learning_level,
               target_direction, updated_at
        FROM user_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if not profile:
        raise HTTPException(status_code=404, detail="用户资料不存在")
    return profile


@router.get("/me/account")
def get_account(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        account = cur.execute(
            """
            SELECT user_uid, username, email, phone, account_status, updated_at
            FROM user_accounts
            WHERE id = ?
            """,
            (current_user["id"],),
        ).fetchone()
    return {"account": _account(account)}


@router.patch("/me/account")
def update_account(payload: AccountUpdate, current_user: dict = Depends(get_current_user)):
    username = normalize_username(payload.username)
    with db_cursor() as cur:
        ensure_username_available(cur, username, exclude_user_id=current_user["id"])
        cur.execute(
            "UPDATE user_accounts SET username = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (username, current_user["id"]),
        )
        account = cur.execute(
            """
            SELECT user_uid, username, email, phone, account_status, updated_at
            FROM user_accounts
            WHERE id = ?
            """,
            (current_user["id"],),
        ).fetchone()
    return {"account": _account(account)}


@router.patch("/me/password")
def update_password(payload: PasswordUpdate, current_user: dict = Depends(get_current_user)):
    try:
        validate_password_strength(payload.newPassword)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if payload.currentPassword == payload.newPassword:
        raise HTTPException(status_code=422, detail="新密码不能和当前密码相同")
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT password_hash FROM user_auth_passwords WHERE user_id = ?",
            (current_user["id"],),
        ).fetchone()
        if not row or not verify_password(payload.currentPassword, row["password_hash"]):
            raise HTTPException(status_code=401, detail="当前密码不正确")
        cur.execute(
            """
            UPDATE user_auth_passwords
            SET password_hash = ?, failed_attempts = 0, locked_until = NULL,
                password_updated_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (hash_password(payload.newPassword), current_user["id"]),
        )
        cur.execute(
            """
            UPDATE user_accounts
            SET token_version = token_version + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (current_user["id"],),
        )
        cur.execute(
            """
            UPDATE user_sessions
            SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND is_revoked = 0
            """,
            (current_user["id"],),
        )
    return {"status": "ok", "message": "密码已更新，请重新登录"}


@router.get("/me/security-questions")
def get_security_questions(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT question_order AS questionOrder, question_text AS question, updated_at AS updatedAt
            FROM user_security_questions
            WHERE user_id = ?
            ORDER BY question_order
            """,
            (current_user["id"],),
        ).fetchall()
    return {"configured": bool(rows), "items": rows}


@router.put("/me/security-questions")
def update_security_questions(payload: SecurityQuestionsUpdate, current_user: dict = Depends(get_current_user)):
    questions = []
    seen = set()
    for index, item in enumerate(payload.items, start=1):
        question = " ".join(item.question.strip().split())
        answer = item.answer.strip()
        if question in seen:
            raise HTTPException(status_code=422, detail="密保问题不能重复")
        seen.add(question)
        questions.append((index, question, hash_security_answer(answer)))

    with db_cursor() as cur:
        row = cur.execute(
            "SELECT password_hash FROM user_auth_passwords WHERE user_id = ?",
            (current_user["id"],),
        ).fetchone()
        if not row or not verify_password(payload.currentPassword, row["password_hash"]):
            raise HTTPException(status_code=401, detail="当前密码不正确")
        cur.execute("DELETE FROM user_security_questions WHERE user_id = ?", (current_user["id"],))
        cur.executemany(
            """
            INSERT INTO user_security_questions(user_id, question_order, question_text, answer_hash)
            VALUES (?, ?, ?, ?)
            """,
            [(current_user["id"], order, question, answer_hash) for order, question, answer_hash in questions],
        )
        rows = cur.execute(
            """
            SELECT question_order AS questionOrder, question_text AS question, updated_at AS updatedAt
            FROM user_security_questions
            WHERE user_id = ?
            ORDER BY question_order
            """,
            (current_user["id"],),
        ).fetchall()
    return {"configured": True, "items": rows}


@router.get("/me/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        profile = _load_profile(cur, current_user["id"])
    return {"profile": _profile(profile)}


@router.patch("/me/profile")
def update_profile(payload: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    updates = []
    values = []
    mapping = {
        "displayName": ("display_name", payload.displayName),
        "avatarUrl": ("avatar_url", payload.avatarUrl),
        "bio": ("bio", payload.bio),
        "roleTitle": ("role_title", payload.roleTitle),
        "learningLevel": ("learning_level", payload.learningLevel),
        "targetDirection": ("target_direction", payload.targetDirection),
    }
    for _, (column, value) in mapping.items():
        if value is not None:
            updates.append(f"{column} = ?")
            values.append(value.strip() if isinstance(value, str) else value)
    if updates:
        values.append(current_user["id"])
        with db_cursor() as cur:
            cur.execute(
                f"UPDATE user_profiles SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values,
            )
            profile = _load_profile(cur, current_user["id"])
    else:
        return get_profile(current_user)
    return {"profile": _profile(profile)}


@router.post("/me/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if file.content_type not in ALLOWED_AVATAR_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="头像仅支持 JPG、PNG、WebP、GIF 等常见图片格式")

    content = await file.read(AVATAR_MAX_UPLOAD_BYTES + 1)
    if len(content) > AVATAR_MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"头像原图不能超过 {AVATAR_MAX_UPLOAD_BYTES // 1024 // 1024}MB")
    if not content:
        raise HTTPException(status_code=422, detail="上传文件为空")

    try:
        image = Image.open(BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="无法识别上传的图片")

    if image.format not in ALLOWED_AVATAR_FORMATS:
        raise HTTPException(status_code=415, detail="头像图片格式不受支持")

    image = image.convert("RGB")
    image.thumbnail((AVATAR_MAX_DIMENSION, AVATAR_MAX_DIMENSION), Image.Resampling.LANCZOS)

    output = BytesIO()
    quality = 84
    while True:
        output.seek(0)
        output.truncate(0)
        image.save(output, format="WEBP", quality=quality, method=6)
        if output.tell() <= AVATAR_MAX_OUTPUT_BYTES or quality <= 58:
            break
        quality -= 8

    if output.tell() > AVATAR_MAX_OUTPUT_BYTES:
        raise HTTPException(status_code=413, detail="头像压缩后仍然过大，请换一张更小的图片")

    avatar_dir = UPLOAD_DIR / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{random_uid('avatar')}.webp"
    output_path = avatar_dir / filename
    output_path.write_bytes(output.getvalue())
    avatar_url = f"/uploads/avatars/{filename}"

    with db_cursor() as cur:
        old = cur.execute(
            "SELECT avatar_url FROM user_profiles WHERE user_id = ?",
            (current_user["id"],),
        ).fetchone()
        cur.execute(
            "UPDATE user_profiles SET avatar_url = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (avatar_url, current_user["id"]),
        )
        profile = _load_profile(cur, current_user["id"])

    old_url = old["avatar_url"] if old else None
    if old_url and old_url.startswith("/uploads/avatars/"):
        old_path = UPLOAD_DIR / Path(old_url).name
        old_avatar_path = UPLOAD_DIR / "avatars" / Path(old_url).name
        for candidate in (old_path, old_avatar_path):
            if candidate.exists() and candidate != output_path:
                candidate.unlink(missing_ok=True)

    return {
        "avatarUrl": avatar_url,
        "profile": _profile(profile),
        "meta": {
            "originalBytes": len(content),
            "storedBytes": output.tell(),
            "format": "webp",
            "maxDimension": AVATAR_MAX_DIMENSION,
        },
    }


@router.get("/me/preferences")
def get_preferences(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        prefs = cur.execute(
            """
            SELECT theme, language, cn_first, free_first, show_external_resources,
                   agent_memory_enabled, preference_json, updated_at
            FROM user_preferences
            WHERE user_id = ?
            """,
            (current_user["id"],),
        ).fetchone()
    if not prefs:
        raise HTTPException(status_code=404, detail="用户偏好不存在")
    return {"preferences": _preferences(prefs)}


@router.patch("/me/preferences")
def update_preferences(payload: PreferencesUpdate, current_user: dict = Depends(get_current_user)):
    updates = []
    values = []
    mapping = {
        "theme": ("theme", payload.theme),
        "language": ("language", payload.language),
        "cnFirst": ("cn_first", payload.cnFirst),
        "freeFirst": ("free_first", payload.freeFirst),
        "showExternalResources": ("show_external_resources", payload.showExternalResources),
        "agentMemoryEnabled": ("agent_memory_enabled", payload.agentMemoryEnabled),
    }
    for _, (column, value) in mapping.items():
        if value is not None:
            updates.append(f"{column} = ?")
            values.append(int(value) if isinstance(value, bool) else value)
    if updates:
        values.append(current_user["id"])
        with db_cursor() as cur:
            cur.execute(
                f"UPDATE user_preferences SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                values,
            )
            prefs = cur.execute(
                """
                SELECT theme, language, cn_first, free_first, show_external_resources,
                       agent_memory_enabled, preference_json, updated_at
                FROM user_preferences
                WHERE user_id = ?
                """,
                (current_user["id"],),
            ).fetchone()
    else:
        return get_preferences(current_user)
    return {"preferences": _preferences(prefs)}


@router.get("/me/sessions")
def list_sessions(current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        rows = cur.execute(
            """
            SELECT session_uid AS sessionUid, device_name AS deviceName, user_agent AS userAgent,
                   ip_address AS ipAddress, is_revoked AS isRevoked, expires_at AS expiresAt,
                   last_seen_at AS lastSeenAt, created_at AS createdAt
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY is_revoked, last_seen_at DESC, created_at DESC
            """,
            (current_user["id"],),
        ).fetchall()
    for row in rows:
        row["isRevoked"] = bool(row["isRevoked"])
    return {"items": rows}


@router.delete("/me/sessions/{session_uid}")
def revoke_session(session_uid: str, current_user: dict = Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE user_sessions
            SET is_revoked = 1, revoked_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND session_uid = ?
            """,
            (current_user["id"], session_uid),
        )
    return {"status": "ok"}


@router.get("/me/learning/progress")
def learning_progress(current_user: dict = Depends(get_current_user)):
    return {
        "items": [],
        "meta": {
            "userUid": current_user["user_uid"],
            "source": "reserved",
            "nextTable": "user_learning_progress",
            "message": "学习进度接口已预留，当前阶段不写入虚假进度数据。",
        },
    }


@router.get("/me/favorites")
def favorites(current_user: dict = Depends(get_current_user)):
    return {
        "items": [],
        "meta": {
            "userUid": current_user["user_uid"],
            "source": "reserved",
            "nextTable": "user_favorites",
            "message": "收藏接口已预留，当前阶段不写入虚假收藏数据。",
        },
    }


@router.get("/me/workflows")
def saved_workflows(current_user: dict = Depends(get_current_user)):
    return {
        "items": [],
        "meta": {
            "userUid": current_user["user_uid"],
            "source": "reserved",
            "nextTable": "user_saved_workflows",
            "message": "用户工作流接口已预留，后续由 Agent 工作流模块写入真实数据。",
        },
    }
