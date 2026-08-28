from flask import Blueprint, flash, redirect, render_template, request, url_for

from flaskblog.logger.config_log import ConfigLogger

logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")

from flaskblog import db

main = Blueprint("main", __name__)


@main.route("/")
@main.route("/home")
def home():
    return redirect(url_for("art_main.art_home"))
    # return render_template('home.html', art_list=art_list)


@main.route("/about")
def about():
    logFC.info(f"'about'")
    flash("About flash message! - success", "success")
    flash("About flash message! - danger", "danger")
    flash("About flash message! - message", "message")
    flash("About flash message! - info", "info")
    flash("About flash message! - warning", "warning")
    return render_template("about.html", title="About")


@main.route("/createDB")
@main.route("/createDB/")
@main.route("/createDB/<int:post_id>")
def createDB(post_id=999):
    page = request.args.get("id", 0, type=int)  # http://127.0.0.1:5000/createDB/88?id=77
    db.create_all()
    db.session.commit()
    logFC.info(f"'createDB' = {post_id} = {page}")
    return render_template("about.html", title="About")
