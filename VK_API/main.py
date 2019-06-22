import sys
import os
import requests
import argparse
import json
import urllib.request
import getpass
import click

from vk_appl_auth import VK_Auth


class VK:

    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.uid = None
        self.aid = None
        self.title = None
        self.access_token = None
        self.app_id = '6985172'
        self.scope = 'photos'

    def auth(self):
        """Авторизация при помощи логина и пароля.
        После получение access_token и user_id"""
        try:
            access_data = VK_Auth().auth(self.login, self.password,
                                           self.app_id, self.scope)
            print("\nАвторизация успешна!\n")
            self.uid = access_data["user_id"]
            self.access_token = access_data["access_token"]
        except Exception as e:
            print(str(e) + "\n")
            sys.exit()

    def get_albums(self, user_id):
        """Получение всех альбомов пользователя, включая скрытые и системные"""
        query = f"https://api.vk.com/method/photos.getAlbums?owner_id={user_id}" \
                f"&need_system=1&v=5.95&access_token={self.access_token}"
        return json.loads(urllib.request.urlopen(query).read())["response"]

    def choose_album(self, user_id):
        """Выбираем конкретный альбом"""
        albums = self.get_albums(user_id)
        counter = 1
        list_albums = []
        for album in albums['items']:
            print(str(counter) + ". " + album["title"])
            list_albums.append(album)
            counter += 1
        s_aid = input("\nВведите номер альбома, из которого скачивать фотографии: ")
        self.aid = list_albums[int(s_aid)-1]["id"]
        self.title = str(s_aid) + "_" + str(user_id)

    @staticmethod
    def get_photo_height(photo):
        return photo['height']

    def get_photos(self, user_id):
        """Получаем фотографии из альбома"""
        query = f"https://api.vk.com/method/photos.get?owner_id={user_id}" \
                f"&album_id={self.aid}&v=5.95&count=250&access_token={self.access_token}"
        #response = requests.post(query)
        photos = json.loads(urllib.request.urlopen(query).read())["response"]
        counter = 1
        try:
            os.mkdir(self.title)
        except Exception:
            print("\nДанный альбом уже существует...\n")
        print("\nСкачиваем фотографии...\n")
        with click.progressbar(photos['items']) as bar:
            for photo in bar:
                #print(photo)
                with open(self.title + "/" + str(counter) + ".jpg", "wb") as f:
                    photo['sizes'] = sorted(photo['sizes'], key=VK.get_photo_height)
                    b = self.get_bytes(photo["sizes"][-1]["url"])
                    f.write(b)
                counter += 1
        print("\nУспех!\n")

    def get_bytes(self, url):
        """Байты фоточек"""
        resource = requests.get(url)
        return resource.content


def main():
    try:
        flag = True
        while flag:
            login = input("Введите логин: ")
            password = getpass.getpass(prompt="Введите пароль: ") #чтобы скрыть пароль
            my_vk = VK(login, password)
            try:
                my_vk.auth()
                flag = False
            except:
                print("!!! Неверный логин или пароль!\n")
        while True:
            user_id = input("Введите id пользователя, чьи альбомы хотите посмотреть "
                            "или 'выход', чтобы завершить сеанс: ")
            if user_id == "выход" or user_id == "":
                break
            else:
                my_vk.choose_album(user_id)
                my_vk.get_photos(user_id)
    except Exception as e:
        print("\n!!! Проблем-с...\n")
        print(str(e) + "\n")
        sys.exit()


if __name__ == "__main__":
    main()
