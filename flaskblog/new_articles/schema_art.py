import os
import tempfile
from datetime import datetime
from pathlib import Path

import yaml
from markdown import markdown
from pydantic import BaseModel

from flaskblog.logger.config_log import ConfigLogger

logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")


# ==============================================================================
# ++++++++++++++++++ BaseModel - ArticleLang - pydantic ++++++++++++++++++++++++
# ------------------------ open files with content -----------------------------
# ------------------------------------------------------------------------------
class ArticleLang(BaseModel):
    author: str = "author"
    lang: str
    art_id: int
    title: str
    file_name: str = ""
    content: str = ""


# ------------------------------------------------------------------------
def get_path_dir():
    cwd_dir = os.getcwd()
    pack_dir = os.path.join("", "flaskblog/templates")  # "flaskblog\\templates"
    content_dir = "content_art"
    return os.path.join(cwd_dir, pack_dir, content_dir)


def read_html(name_html: str, name_dir: str = get_path_dir()) -> str:
    path_html = os.path.join(name_dir, name_html)
    logFC.info(f"read_html : \n{name_dir} : {name_html}\n{path_html}")

    with open(path_html, "r", encoding="utf8") as file:  # file: TextIO
        all_file: str = file.read()
    return all_file


def render_article(name_file: str, name_dir: str = get_path_dir()) -> str:
    content = read_html(name_file, name_dir)
    file_extension = os.path.splitext(name_file)[1].lower()

    if file_extension in {".md", ".markdown"}:
        return markdown(content, extensions=["fenced_code", "tables"])

    return content


# ------------------------------ registry with mtime cache
articles_path = Path(__file__).with_name("articles.yaml")

_registry_cache: list[ArticleLang] = []
_registry_error: str | None = None
_last_stat: tuple[int, int] | None = None

_FIELDS_FOR_YAML = {"author", "lang", "art_id", "title", "file_name"}


def _load_registry() -> list[ArticleLang]:
    """Read articles.yaml from disk and return list of ArticleLang."""
    with articles_path.open("r", encoding="utf8") as articles_file:
        articles_data = yaml.safe_load(articles_file)

    if not isinstance(articles_data, dict) or "articles" not in articles_data:
        raise ValueError("articles.yaml: expected top-level key 'articles'")

    return [ArticleLang(**article) for article in articles_data["articles"]]


def get_articles() -> list[ArticleLang]:
    """Return current registry, reloading from disk if yaml changed."""
    global _registry_cache, _registry_error, _last_stat

    try:
        stat = articles_path.stat()
        current_key = (stat.st_mtime_ns, stat.st_size)
    except FileNotFoundError:
        logFC.error(f"articles.yaml not found: {articles_path}")
        _registry_error = "Файл реестра articles.yaml не найден"
        return _registry_cache
    except OSError as exc:
        logFC.error(f"Cannot stat articles.yaml: {exc}")
        _registry_error = f"Ошибка доступа к реестру: {exc}"
        return _registry_cache

    if _last_stat == current_key:
        return _registry_cache

    try:
        _registry_cache = _load_registry()
        _registry_error = None
        _last_stat = current_key
        logFC.info(f"articles.yaml reloaded: {len(_registry_cache)} entries")
    except (OSError, yaml.YAMLError, ValueError, TypeError, KeyError) as exc:
        logFC.error(f"Failed to parse articles.yaml: {exc}")
        _registry_error = f"Ошибка чтения articles.yaml: {exc}"
        # Keep previous working state; force reload on next call by clearing stat.
        _last_stat = None

    return _registry_cache


def get_art(art_id: int) -> ArticleLang | None:
    """Return article by id or None."""
    for art in get_articles():
        if art.art_id == art_id:
            return art
    return None


def get_registry_error() -> str | None:
    """Return last yaml loading error, if any."""
    get_articles()  # ensure error state is fresh
    return _registry_error


def save_articles(articles: list[ArticleLang]) -> None:
    """Atomically write articles list back to articles.yaml."""
    data = {
        "articles": [
            art.model_dump(include=_FIELDS_FOR_YAML, exclude_unset=False)
            for art in articles
        ]
    }

    # Write to a temp file in the same directory, then atomically replace.
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=articles_path.parent,
        prefix=".articles_",
        suffix=".yaml.tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf8") as tmp_file:
            yaml.safe_dump(
                data,
                tmp_file,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
        os.replace(tmp_path, articles_path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Invalidate cached stat so next get_articles() re-reads from disk.
    global _last_stat
    _last_stat = None
    logFC.info(f"articles.yaml saved: {len(articles)} entries")


def scan_content_art() -> list[str]:
    """Return sorted list of .md/.markdown file names in content_art."""
    content_dir = Path(get_path_dir())
    if not content_dir.exists():
        return []

    files = [
        entry.name
        for entry in content_dir.iterdir()
        if entry.is_file() and entry.suffix.lower() in {".md", ".markdown"}
    ]
    return sorted(files)


# ==============================================================================
# +++++++++++++++++++++++++++ BaseModel - pydantic +++++++++++++++++++++++++++++
# ------------------------------------------------------------------------------
class UserUpdateBody(BaseModel):
    nickname: str | None = ""
    email: str | None = ""


class PostUpdateBody(BaseModel):
    id: int
    title: int | None = 1
    content: str | None = ""


class UserPostBase(BaseModel):
    class Config:
        from_attributes = True


class UserSchemaResp(UserPostBase):
    id: int
    nickname: str


class PostSchemaResp(UserPostBase):
    id: int
    time_created: datetime
    title: str


class UserSchemaPostsResp(UserSchemaResp):
    posts: list[PostSchemaResp]


class PostSchemaAuthorResp(PostSchemaResp):
    author: UserSchemaResp
