from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from markdown import markdown
from pathlib import Path
import os
import yaml

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


# ------------------------------ NEW version
articles_path = Path(__file__).with_name("articles.yaml")
with articles_path.open("r", encoding="utf8") as articles_file:
    articles_data = yaml.safe_load(articles_file)

art_files: List[ArticleLang] = [ArticleLang(**article) for article in articles_data["articles"]]
art_dict_file: Dict[int, ArticleLang] = {art.art_id: art for art in art_files}


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
