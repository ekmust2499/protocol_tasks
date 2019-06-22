import socket
import base64
import ssl
import re
from configparser import ConfigParser, NoOptionError, NoSectionError
import sys
import urllib.request


LOGIN = ''
PASSWORD = ''
IP_PORT = ()
BOUNDARY = "#______________________________________________________#"


def get_headers_from_message(data):
    print(header_parser(r'(From: )=\?utf-8\?B\?(.*?)\?=', data, 'From: '))
    print(re.findall(r'To: .*?\n', data)[0])
    print(re.findall(r'Date: .*?\n', data)[0])
    print(header_parser(r'(Subject: |\t)=\?utf-8\?B\?(.*?)\?=', data, 'Subject: '))


def header_parser(regex, data, header):
    new_data = data.replace('\r\n ', '')
    new_data = new_data.replace("?==?", "?=\t=?")
    if re.findall(header + r'=\?utf-8\?B', new_data, re.IGNORECASE):
        string = [x[1] for x in re.findall(regex, new_data, re.IGNORECASE)]
        string = [bytes(x, 'utf-8') for x in string]
        result = header + ''.join([base64.b64decode(x).decode('utf-8') for x in string])
        string.clear()
        return result
    else:
        return re.findall(header + '.*\n', data, re.IGNORECASE)[0]


def write(masbytes, filename):
    result = base64.b64decode(masbytes)
    with open(filename, 'wb') as file:
        file.write(result)


def get_full_message_with_attachments(message):
    boundary = re.search('boundary="(.*?)"', message)
    if boundary:
        boundary = boundary.group(1).replace('.', '\.')
        blocks = re.split('--' + boundary, message)[1:-1]
        split_by = '\r\n\r\n'
    else:
        blocks = [message]
        split_by = '\r\n\r\n'
    for block in blocks:
        try:
            headers, masbytes = block.split(split_by, 1)
            if '\r\nContent-Disposition: attachment;' in headers:
                print(headers)
                filename = re.findall('filename="(.*)"', headers)[0]
                write(bytes(masbytes, 'utf-8'), filename)
                print('File download! You can open them!')
            else:
                print(headers)
                if 'Content-Transfer-Encoding: base64' in headers:
                    text_message = base64.b64decode(masbytes).decode()
                else:
                    text_message = masbytes
                if text_message[0] == '.':
                    text_message = text_message[1:]
                text_message = text_message.replace('\n..', '\n.')
                print(text_message.rstrip()[:-1])
        except:
            print("The message sent is too large. Only the number of octets is transmitted.")


def send_recv(command, sock):
    command_to_send = bytes(command, 'utf-8') + b'\n'
    sock.send(command_to_send)
    data_to_send = b''
    while True:
        try:
            data = sock.recv(1024)
        except socket.timeout:
            break
        data_to_send += data
        if not data:
            break
    data = data_to_send.decode(encoding='utf-8')
    if data.startswith('+OK') or '+OK' in data:
        return data
    else:
        return str(data) + '\n' + "INVALID COMMAND FORMAT!!!"
        #sys.exit(0)


def read_data_from_config():
    global LOGIN, PASSWORD, IP_PORT
    try:
        with open('config.cfg', "r") as file:
            file.read()
    except FileNotFoundError:
        sys.exit("Конфигурационный файл не найден!")

    parser = ConfigParser()
    parser.read('config.cfg')

    try:
        IP_PORT = (parser.get("Address", "mail"), int(parser.get("Address", "port")))
        LOGIN = parser.get("Source", "login")
        PASSWORD = parser.get("Source", "password")
    except NoSectionError or NoOptionError:
        sys.exit("Конфигурационный файл содержит неверные данные!")


def connected(host='http://google.com'):
    try:
        urllib.request.urlopen(host)
        return True
    except IOError:
        raise ConnectionError


def main():
    try:
        connected()
    except ConnectionError:
        sys.exit("Отсутствует подключение к интернету!")

    read_data_from_config()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock = ssl.wrap_socket(sock)
        sock.settimeout(1)
        try:
            sock.connect(IP_PORT)
            print(sock.recv(1024).decode(encoding='utf-8'))
            print(send_recv("USER " + LOGIN, sock))
            print(send_recv("PASS " + PASSWORD, sock))
        except socket.timeout:
            sys.exit("Timeout!")
        except socket.error:
            sys.exit("Error with socket!")
        except Exception:
            sys.exit("Fail on try connect!")

        while True:
            command = sys.stdin.readline().rstrip()
            if command.startswith('RETR'):
                #Требует в качестве аргумента номер существующего и не помеченного для удаления сообщения.
                #В ответ сервер присылает запрошенное сообщение.
                print(BOUNDARY)
                print(send_recv(command, sock))
                print(BOUNDARY)
                continue
            if command.startswith('HEAD'):
                # Выдает заголовки: from, to, date and subject
                print(BOUNDARY)
                get_headers_from_message(send_recv('TOP ' + command.split()[1] + ' 1', sock))
                print(BOUNDARY)
                continue
            if command.startswith('TOP'):
                #Позволяет клиенту получить заголовок и первые строки тела указанного в аргументе сообщения.
                #Формат команды:
                #ТОР номер_сообщения число_строк
                #Если второй аргумент больше, чем число строк в теле сообщения, то клиент получает сообщение целиком.
                print(BOUNDARY)
                print(send_recv(command, sock))
                print(BOUNDARY)
                continue
            if command.startswith('FULL '):
                #Передает полное сообщение с номером в аргументе, достает вложения из сообщений, сохраняя с возможным последующим их просмотром
                print(BOUNDARY)
                response = send_recv('RETR ' + command.split()[1], sock)
                if "INVALID COMMAND FORMAT!!!" in response:
                    print(response)
                else:
                    get_full_message_with_attachments(response)
                print(BOUNDARY)
                continue
            if command == 'STAT':
                #Количество сообщение в почтовом ящике и общий размер ящика в октетах.
                print(BOUNDARY)
                print(send_recv("STAT", sock))
                print(BOUNDARY)
                continue
            if command.startswith('LIST'):
                #Cписок сообщений в почтовом ящике, содержащий их порядковые номера и размеры в октетах.
                #Если в качестве аргумента команды LIST указать номер сообщения, то в ответе будет содержаться информация только об одном запрошенном сообщении.
                print(BOUNDARY)
                if len(command.split()) < 2:
                    adds = ""
                else:
                    adds = " " + command.split()[1]
                print(send_recv("LIST" + adds, sock))
                print(BOUNDARY)
                continue
            if command == 'QUIT':
                #Завершение сеанса. Если в ходе сеанса какие-то сообщения были помечены для удаления, то после выполнения команды QUIT они удаляются из ящика.
                print(send_recv("QUIT", sock))
                break
            print('UNKNOWN COMMAND!!!')
            print(BOUNDARY)


if __name__ == '__main__':
    main()
