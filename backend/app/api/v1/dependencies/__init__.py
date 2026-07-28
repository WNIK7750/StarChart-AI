__all__ = ["require_permission"]


def __getattr__(name: str):
    if name == "require_permission":
        from app.api.v1.dependencies.authorization import require_permission

        return require_permission
    raise AttributeError(name)
