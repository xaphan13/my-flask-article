from flask import render_template, Blueprint

from flaskblog.logger.config_log import ConfigLogger
logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")

from flaskblog.new_articles.schema_art import art_dict_file, ArticleLang, render_article

art_main = Blueprint('art_main', __name__)


@art_main.route("/art_home")
def art_home():
    # title_list = [(x.author, x.title, x.art_id, x.lang) for x in articles]
    title_list = [x.dict(exclude_unset=True, exclude={'content'}) for x in art_dict_file.values()]
    logFC.info(f"new_art : '/art' = {title_list}")

    return render_template('new_art/art_home.html', title_list=title_list)


@art_main.route("/art/<string:author>/<int:art_id>")
def art_author(author, art_id):
    logFC.info(f"art_author : '/art/<string:username>' = {author} - {art_id}")

    art: ArticleLang = art_dict_file[art_id]
    content: str = render_article(art.file_name)
    art.content = content

    return render_template('new_art/art_author.html', lang=art.lang, art=art)
