import os
import time

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from flaskblog.logger.config_log import ConfigLogger

logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")

from flaskblog.new_articles.schema_art import (
    ArticleLang,
    get_art,
    get_articles,
    get_path_dir,
    get_registry_error,
    render_article,
    save_articles,
    scan_content_art,
)

art_main = Blueprint("art_main", __name__)


# ----------------------------------------------------------------------------------
@art_main.route("/art_home")
def art_home():
    title_list = [
        art.model_dump(exclude={"content"})
        for art in get_articles()
        if _is_complete(art)
    ]
    logFC.info(f"new_art : '/art_home' = {title_list}")

    return render_template("new_art/art_home.html", title_list=title_list)


# ----------------------------------------------------------------------------------
@art_main.route("/art/<string:author>/<int:art_id>")
def art_author(author, art_id):
    logFC.info(f"art_author : '/art/<string:author>/<int:art_id>' = {author} - {art_id}")

    art = get_art(art_id)
    if art is None:
        abort(404)

    if not _is_complete(art):
        abort(404)

    content_dir = get_path_dir()
    if not os.path.exists(os.path.join(content_dir, art.file_name)):
        abort(404)

    content = render_article(art.file_name, content_dir)
    art_for_template = art.model_copy(update={"content": content})

    return render_template("new_art/art_author.html", lang=art_for_template.lang, art=art_for_template)


# ----------------------------------------------------------------------------------
@art_main.route("/art_manage")
@login_required
def art_manage():
    articles = get_articles()
    disk_files = set(scan_content_art())
    registered_files = {art.file_name for art in articles}

    unassigned_files = [name for name in scan_content_art() if name not in registered_files]

    articles_context = [
        {
            "art_id": art.art_id,
            "file_name": art.file_name,
            "title": art.title,
            "author": art.author,
            "lang": art.lang,
            "complete": _is_complete(art),
            "file_exists": art.file_name in disk_files,
        }
        for art in articles
    ]

    missing_entries = [
        {
            "art_id": art.art_id,
            "file_name": art.file_name,
            "title": art.title,
            "author": art.author,
            "lang": art.lang,
            "complete": _is_complete(art),
            "file_exists": False,
        }
        for art in articles
        if art.file_name not in disk_files
    ]

    return render_template(
        "new_art/art_manage.html",
        articles=articles_context,
        unassigned_files=unassigned_files,
        missing_entries=missing_entries,
        yaml_error=get_registry_error(),
    )


# ----------------------------------------------------------------------------------
@art_main.route("/art_manage/add_all", methods=["POST"])
@login_required
def art_manage_add_all():
    disk_files = set(scan_content_art())
    articles = list(get_articles())
    registered_files = {art.file_name for art in articles}

    new_files = [name for name in sorted(disk_files) if name not in registered_files]
    if not new_files:
        flash("Нет новых файлов для добавления", "info")
        return redirect(url_for("art_main.art_manage"))

    existing_ids = {art.art_id for art in articles}
    added = 0
    for file_name in new_files:
        title = os.path.splitext(file_name)[0]
        new_id = _allocate_art_id(existing_ids)
        existing_ids.add(new_id)
        articles.append(
            ArticleLang(art_id=new_id, file_name=file_name, title=title, author="", lang="")
        )
        added += 1

    save_articles(articles)
    flash(f"Добавлено файлов: {added}", "success")
    return redirect(url_for("art_main.art_manage"))


# ----------------------------------------------------------------------------------
@art_main.route("/art_manage/meta", methods=["POST"])
@login_required
def art_manage_meta():
    file_name = request.form.get("file_name", "").strip()
    author = request.form.get("author", "").strip()
    lang = request.form.get("lang", "").strip()
    title = request.form.get("title", "").strip()

    disk_files = set(scan_content_art())
    articles = list(get_articles())
    registry_by_file = {art.file_name: art for art in articles}

    if file_name not in disk_files and file_name not in registry_by_file:
        flash(f"Недопустимое имя файла: {file_name}", "danger")
        return redirect(url_for("art_main.art_manage"))

    existing_ids = {art.art_id for art in articles}

    if file_name in registry_by_file:
        old_art = registry_by_file[file_name]
        updated_art = old_art.model_copy(
            update={"author": author, "lang": lang, "title": title}
        )
        articles = [updated_art if art.file_name == file_name else art for art in articles]
        action_word = "Обновлена"
    else:
        new_id = _allocate_art_id(existing_ids)
        if not title:
            title = os.path.splitext(file_name)[0]
        articles.append(
            ArticleLang(art_id=new_id, file_name=file_name, title=title, author=author, lang=lang)
        )
        action_word = "Добавлена"

    save_articles(articles)
    flash(f"{action_word} запись для {file_name}", "success")
    return redirect(url_for("art_main.art_manage"))


# ----------------------------------------------------------------------------------
def _is_complete(art: ArticleLang) -> bool:
    return bool(art.author.strip() and art.lang.strip() and art.title.strip())


def _allocate_art_id(existing_ids: set[int]) -> int:
    new_id = int(time.time())
    while new_id in existing_ids:
        new_id += 1
    return new_id
