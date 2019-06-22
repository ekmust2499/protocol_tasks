from http.cookiejar import CookieJar
import urllib.parse
import urllib.request
import urllib

from html.parser import HTMLParser

VK_OAUTH_URL = "http://oauth.vk.com/oauth/authorize"
VK_OAUTH_REDIRECT_URI = "http://oauth.vk.com/blank.html"


class VK_Auth:

    def auth_user(self, email, password, client_id, scope, opener):

        response = opener.open(f"{VK_OAUTH_URL}?redirect_uri={VK_OAUTH_REDIRECT_URI}&response_type=token"
                               f"&client_id={client_id}&scope={scope}&display=page")
        html = response.read() #читаем код страницы авторизации
        parser = VK_Parser()
        parser.feed(html)
        parser.close()
        if not parser.form_parsed or parser.url is None or "pass" not in parser.params or \
                "email" not in parser.params:
            raise RuntimeError("!!! Проблема с парсером. Невозможно разобрать форму авторизации приложения ВК!")
        parser.params["email"] = email
        parser.params["pass"] = password

        #Подставляем в параметры запроса email и пароль пользователя и отправляем форму
        if parser.method == "POST" or parser.method == "post":
            response = opener.open(parser.url, urllib.parse.urlencode(parser.params).encode("utf-8"))
        else:
            raise NotImplementedError(f"!!! Метод '{parser.method}' для авторизации пользователя "
                                      f"не поддерживается. Используйте его по необходимости!")
        return response.read(), response.geturl()

    def give_access(self, html, opener):
        parser = VK_Parser()
        parser.feed(html)
        parser.close()

        if not parser.form_parsed or parser.url is None:
            raise RuntimeError("!!! Проблема с парсером. Невозможно разобрать форму авторизации приложения ВК!")

        if parser.method == "POST" or parser.method == "post":
            response = opener.open(parser.url, urllib.parse.urlencode(parser.params).encode("utf-8"))
        else:
            raise NotImplementedError(f"!!! Метод '{parser.method}' для авторизации пользователя "
                                      f"не поддерживается. Используйте его по необходимости!")
        return response.geturl()

    def auth(self, email, password, app_id, scope):

        def split_key_value(kv_pair):
            kv = kv_pair.split("=")
            return kv[0], kv[1]

        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()),
                                             urllib.request.HTTPRedirectHandler())

        html, url = self.auth_user(email, password, app_id, scope, opener) #авторизация пользователя

        #даем приложению те права, которые мы запрашивали в параметре scope (подтверждение от ВК)
        if urllib.request.urlparse(url).path != "/blank.html":
            url = self.give_access(html, opener)
        if urllib.request.urlparse(url).path != "/blank.html":
            raise RuntimeError("!!! Ошибка от сервера OAuth. Произошла ошибка при получении access_token.")

        answer = dict(split_key_value(kv_pair) for kv_pair in urllib.request.urlparse(url).fragment.split("&"))

        #Получаем access_token и user_id
        if "access_token" not in answer or "user_id" not in answer or "expires_in" not in answer:
            raise RuntimeError("!!! Отсутствует access_token или user_id в отклике.")
        return {"access_token": answer["access_token"],
                "user_id": answer["user_id"],
                "expires_in": answer["expires_in"]}


class VK_Parser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.url = None
        self.params = {}
        self.in_form = False
        self.form_parsed = False
        self.method = "GET"

    def handle_starttag(self, tag, attributes):
        tag = tag.lower()

        if tag == "form":
            if self.form_parsed:
                raise RuntimeError("!!! Вторая form на странице!")
            if self.in_form:
                raise RuntimeError("!!! form уже создана")
            self.in_form = True

        if not self.in_form:
            return
        attributes = dict((name.lower(), value) for name, value in attributes)

        if tag == "form":
            self.url = attributes["action"] #https://login.vk.com/?act=login&soft=1&utf8=1
            if "method" in attributes:
                self.method = attributes["method"] #POST
        elif tag == "input" and "type" in attributes and "name" in attributes:
            if attributes["type"] in ["hidden", "text", "password"]:
                self.params[attributes["name"]] = attributes["value"] if "value" in attributes else ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "form":
            if not self.in_form:
                raise RuntimeError("!!! Неожиданный конец <form>")
            self.in_form = False
            self.form_parsed = True