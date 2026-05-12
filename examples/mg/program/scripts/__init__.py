from typing import Any


def preprocess(*args: Any, **kwargs: Any) -> bool:
    from .preprocess.transformer import main

    return bool(main(*args, **kwargs))


def postprocess(*args: Any, **kwargs: Any) -> dict[str, str]:
    from .postprocess.postprocess import run_postprocess as run

    return run(*args, **kwargs)


__all__ = ["preprocess", "postprocess"]
