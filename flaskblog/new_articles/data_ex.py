from flaskblog.logger.config_log import ConfigLogger

logFC = ConfigLogger.getLogger("FileStdout", "ClientHTTPS")


class ArticleEx:
    def __init__(self, username, article):
        self.username = username
        self.article = article

    def get_username(self):
        logFC.info(f"ArticleEx username = {self.username}")
        return self.username

    def get_article(self):
        logFC.info(f"ArticleEx article = {self.article}")
        return self.article


art_list = [ArticleEx("user1", "article1"), ArticleEx("user2", "article2"), ArticleEx("user3", "article3")]


class ArticleLang22:
    def __init__(self, username, article):
        self.username = username
        self.article = article

    def get_username(self):
        logFC.info(f"ArticleEx username = {self.username}")
        return self.username

    def get_article(self):
        logFC.info(f"ArticleEx article = {self.article}")
        return self.article
