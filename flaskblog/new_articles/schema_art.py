from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from markdown import markdown
import os

from flaskblog.logger.config_log import ConfigLogger
logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")

from flaskblog.new_articles.arts_content import art1, art2, art3


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


# ------------------------------ NEW version
art_files: List[ArticleLang] = [
    ArticleLang(author="Max",  lang="Python", art_id=1,
                title="Генераторы и декораторы", file_name="art1.html"),
    ArticleLang(author="Alex", lang="Rust",   art_id=2,
                title="Кортежи и массивы", file_name="art2.html"),
    ArticleLang(author="Max",  lang="Python", art_id=3,
                title="Логирование в многопроцессном приложении", file_name="art3.html"),
    ArticleLang(author="Max",  lang="Python", art_id=4,
                title="Глубокое погружение в метаклассы", file_name="art4.html"),
    ArticleLang(author="Max",  lang="Python", art_id=5,
                title="Репозиторий для Telegram-магазина", file_name="gemini-pro-fastapi-1.md")
]

art_dict_file: Dict[int, ArticleLang] = {art.art_id: art for art in art_files}


# ----------------------------- old version
articles: List[ArticleLang] = [
    ArticleLang(author="Max",  lang="Python", art_id=1, title="Генераторы и декораторы", content=art1),
    ArticleLang(author="Alex", lang="Rust",   art_id=2, title="Кортежи и массивы", content=art2),
    ArticleLang(author="Max",  lang="Python", art_id=3, title="Логирование в много процессном приложении", content=art3)
]

articles_dict = {article.art_id: article for article in articles}


# ==============================================================================
# +++++++++++++++++++++++++++ BaseModel - pydantic +++++++++++++++++++++++++++++
# ------------------------------------------------------------------------------
class UserUpdateBody(BaseModel):
    nickname: Optional[str] = ""
    email: Optional[str] = ""


class PostUpdateBody(BaseModel):
    id: int
    title: Optional[int] = 1
    content: Optional[str] = ""


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
    posts: List[PostSchemaResp]


class PostSchemaAuthorResp(PostSchemaResp):
    author: UserSchemaResp
