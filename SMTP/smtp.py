import socket
import ssl
import base64
import os
import datetime
import sys
import urllib.request
from configparser import ConfigParser, NoSectionError, NoOptionError

config_file = "config.cfg"
ip_port = ('smtp.mail.ru', 465)
LOGIN = ""
PASSWORD = ""
dir_with_files = os.path.normpath(os.path.join(os.path.dirname(__file__), 'files'))
format_file = {
    "jpg": "image/jpeg",
    "gif": "image/gif",
    "png": "image/png",
    "pdf": "application/pdf"
}


def get_attachments(list_attachments):
    attachments = b""
    for attachment in list_attachments:
        with open(os.path.join(dir_with_files, attachment), "rb") as file:
            b_file = base64.b64encode(file.read())
            attachments += b"Content-Type: " + format_file[
                attachment[-3:]].encode() + f'; name="{attachment}"'.encode() + b'\n' #тип передаваемых данных
            attachments += f'Content-Disposition: attachment; filename="{attachment}"'.encode() + b'\n' # указываем исходное имя прикрепленного файла
            attachments += b"Content-Transfer-Encoding: base64" + b'\n' #кодировка передачи содержимого
            attachments += b"\n" + b_file + b'\n'
            attachments += b"--eunhyuk0404\n"
    return attachments


def create_text_in_byte(text):
    with open(os.path.join(dir_with_files, text), 'r', encoding='utf-8') as f:
        message = f.read()
        if message[0] == '.': #все точки в сообщении экранируем (т.е. вместо n делаем n+1)
            message = '.' + message
        message = message.replace('\n.', '\n..')
        text = message.encode()
        return text


def create_message(source, destination, subject, list_attachments, text):
    date = datetime.datetime.now()
    result = b'Date: ' + bytes(date.strftime("%a, %d %b %y %H%M"), 'utf-8') + b'\n' #Дата в формате: Tue, 25 Apr 19 1426
    result += b'From: ' + bytes(source, "utf-8") + b'\n'
    result += b'To: ' + bytes(destination, "utf-8") + b'\n'
    result += b'Subject: ' + b'=?utf-8?B?' + base64.b64encode(bytes(subject, "utf-8")) + b'?=\n'

    attachments = get_attachments(list_attachments)
    result += b'MIME-Version: 1.0' + b'\n'
    if len(attachments) != 0:
        result += b'Content-Type: multipart/mixed; boundary="eunhyuk0404"\n\n'
        result += b'--eunhyuk0404\n'
    result += b'Content-Type: text/plain;\n\n'
    result += create_text_in_byte(text) + b'\n'
    if len(attachments) != 0:
        result += b'--eunhyuk0404'
        result += b'\n' + attachments
        result += b'--'
    result += b'\n.'
    return result


def get_data_from_config():
    global LOGIN, PASSWORD
    try:
        config = os.path.join(dir_with_files, config_file)
        with open(config, "r") as file:
            file.read()
    except FileNotFoundError:
        sys.exit("Конфигурационный файл не найден!")

    parser = ConfigParser()
    parser.read(config)
    try:
        source_login = parser.get("Source", "login")
        LOGIN = base64.b64encode(source_login.encode())

        source_password = parser.get("Source", "password")
        PASSWORD = base64.b64encode(source_password.encode())

        list_destination = list()
        destination = parser.items("Destination")
        for i in destination:
            list_destination.append(i[1])

        subject = parser.get("Subject", "subject")

        list_attachments = list()
        attachments = parser.items("Attachments")
        for attachment in attachments:
            list_attachments.append(attachment[1])

        text = parser.get("Text", "text")
    except NoSectionError or NoOptionError:
        sys.exit("Конфигурационный файл содержит неверные данные!")

    return source_login, list_destination, subject, list_attachments, text


def connected(host='http://google.com'):
    try:
        urllib.request.urlopen(host)
        return True
    except IOError:
        raise ConnectionError


def send_and_read(message, sock):
    message += b'\n'
    sock.send(message)
    return sock.recv(1024).decode(encoding='utf-8')


def main():
    try:
        connected()
    except ConnectionError:
        sys.exit("Отсутствует подключение к интернету!")

    source_login, list_destination, subject, list_attachments, text = get_data_from_config()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock = ssl.wrap_socket(sock) #в защищенном режиме(ssl)
        sock.connect(ip_port)
        sock.settimeout(25)
        try:
            print(sock.recv(1024).decode())
            print(send_and_read(b'EHLO ekmust', sock)) #или сделать input() для ввода с консоли
            print(send_and_read(b'AUTH LOGIN', sock))
            print(send_and_read(LOGIN, sock))
            print(send_and_read(PASSWORD, sock))
            for destination in list_destination: #отправляем письмо каждому адресату
                print(send_and_read(b'MAIL FROM: ' + bytes(source_login, "utf-8"), sock))
                print(send_and_read(b'RCPT TO: ' + bytes(destination, "utf-8"), sock))
                print(send_and_read(b'DATA ', sock))
                message = create_message(source_login, destination, subject, list_attachments, text)
                print(send_and_read(message, sock))
                print('MESSAGE SENT!')
        except socket.timeout:
            sys.exit("Timeout!")
        except socket.error:
            sys.exit("Error with socket!")


if __name__ == "__main__":
    main()
