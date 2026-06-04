import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_BASE_URL = 'http://localhost:8080'


def default_config_path() -> Path:
    return Path.home() / '.cli-anything-openwebui' / 'session.json'


def _locked_save_json(path: Path, data: dict[str, Any], **dump_kwargs) -> None:
    path = Path(path)
    try:
        f = path.open('r+', encoding='utf-8')
    except FileNotFoundError:
        path.parent.mkdir(parents=True, exist_ok=True)
        f = path.open('w+', encoding='utf-8')
    with f:
        locked = False
        try:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.flush()
            os.fsync(f.fileno())
        finally:
            if locked:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


@dataclass
class SessionState:
    base_url: str = DEFAULT_BASE_URL
    token: str | None = None
    current_chat_id: str | None = None
    undo_stack: list[dict[str, Any]] = field(default_factory=list)
    redo_stack: list[dict[str, Any]] = field(default_factory=list)
    last_user: dict[str, Any] | None = None
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    default_profile: str | None = None

    @classmethod
    def empty(cls) -> 'SessionState':
        return cls()

    @classmethod
    def load(cls, path: str | Path | None = None) -> 'SessionState':
        config_path = Path(path) if path else default_config_path()
        if not config_path.exists():
            return cls.empty()
        try:
            data = json.loads(config_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f'Invalid OpenWebUI harness config at {config_path}: {exc}') from exc
        return cls(
            base_url=data.get('base_url') or DEFAULT_BASE_URL,
            token=data.get('token'),
            current_chat_id=data.get('current_chat_id'),
            undo_stack=list(data.get('undo_stack') or []),
            redo_stack=list(data.get('redo_stack') or []),
            last_user=data.get('last_user'),
            profiles=dict(data.get('profiles') or {}),
            default_profile=data.get('default_profile'),
        )

    def save(self, path: str | Path | None = None) -> Path:
        config_path = Path(path) if path else default_config_path()
        _locked_save_json(config_path, self.to_dict(), indent=2)
        return config_path

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def masked(self) -> dict[str, Any]:
        data = self.to_dict()
        data['token'] = '***' if self.token else None
        data['undo_stack'] = [self._masked_snapshot(snapshot) for snapshot in self.undo_stack]
        data['redo_stack'] = [self._masked_snapshot(snapshot) for snapshot in self.redo_stack]
        data['profiles'] = {
            name: {
                **profile,
                'token': '***' if profile.get('token') else None,
            }
            for name, profile in self.profiles.items()
        }
        return data

    @staticmethod
    def _masked_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
        data = dict(snapshot)
        if data.get('token'):
            data['token'] = '***'
        return data

    def snapshot(self) -> dict[str, Any]:
        return {
            'base_url': self.base_url,
            'token': self.token,
            'current_chat_id': self.current_chat_id,
            'last_user': self.last_user,
        }

    def restore_snapshot(self, snapshot: dict[str, Any]) -> None:
        self.base_url = snapshot.get('base_url') or DEFAULT_BASE_URL
        self.token = snapshot.get('token')
        self.current_chat_id = snapshot.get('current_chat_id')
        self.last_user = snapshot.get('last_user')

    def remember(self) -> None:
        self.undo_stack.append(self.snapshot())
        self.redo_stack.clear()

    def select_chat(self, chat_id: str | None) -> None:
        if chat_id == self.current_chat_id:
            return
        self.remember()
        self.current_chat_id = chat_id

    def remember_auth(self, token: str | None, user: dict[str, Any] | None = None) -> None:
        self.remember()
        self.token = token
        self.last_user = user

    def set_profile(
        self,
        name: str,
        base_url: str | None = None,
        token: str | None = None,
        make_default: bool = False,
    ) -> None:
        profile = dict(self.profiles.get(name) or {})
        if base_url:
            profile['base_url'] = base_url
        if token:
            profile['token'] = token
        self.profiles[name] = profile
        if make_default:
            self.default_profile = name

    def apply_profile(self, name: str | None) -> bool:
        if not name:
            return False
        profile = self.profiles.get(name)
        if not profile:
            return False
        if profile.get('base_url'):
            self.base_url = profile['base_url']
        if profile.get('token'):
            self.token = profile['token']
        return True

    def delete_profile(self, name: str) -> bool:
        if name not in self.profiles:
            return False
        del self.profiles[name]
        if self.default_profile == name:
            self.default_profile = None
        return True

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.snapshot())
        self.restore_snapshot(self.undo_stack.pop())
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.snapshot())
        self.restore_snapshot(self.redo_stack.pop())
        return True
