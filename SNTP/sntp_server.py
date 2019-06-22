import socket
import struct
import sys
import time
import urllib.request

conf_file = "conf.txt"
TIME1970 = 2208988800      # 01-01-1970 00:00:00


def helper_server(server="time.windows.com"):
    port = 123
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    msg = '\x1b' + 47 * '\0'
    try:
        client.sendto(msg.encode("utf-8"), (server, port))
        client.settimeout(2)
        try:

            data, address = client.recvfrom(512)
            unpack_data = struct.unpack('!12I', data)
            cur_time = unpack_data[10] - TIME1970
            return cur_time, unpack_data
        except socket.timeout:
            print("Timed out!")
            exit(3)
    except (socket.gaierror, socket.error):
        print("Server <%s> not correct" % (server))
        exit(2)


def read_from_conf_file():
    try:
        with open("conf.txt", "r") as f:
            data = f.read().rstrip()
            if len(data) != 0:
                try:
                    seconds = int(data)
                    return seconds
                except ValueError:
                    raise
            else:
                return 0
    except FileNotFoundError:
        raise


def server(sec):
    with socket.socket() as sock:
        sock.bind(('localhost', 55))
        sock.listen(1)
        connection, address = sock.accept()
        while True:
            data = connection.recv(512)
            if not data:
                break
            time_from_server, unpack_data = helper_server()
            time_with_error = time_from_server + sec
            list_unpack_data = list(unpack_data)
            list_unpack_data[10] = time_with_error
            result = b""
            for x in tuple(list_unpack_data):
                result = result + struct.pack('!I', x)
            print(time.ctime(time_with_error))
            connection.send(result)
        connection.close()


def main():
    try:
        urllib.request.urlopen("https://vk.com/")
    except IOError:
        print("Отсутствует соединение с интернетом...")
        exit(1)
    try:
        sec = read_from_conf_file()
        server(sec)
    except FileNotFoundError:
        print("Конфигурационный файл отсутствует!")
    except ValueError:
        print("В вашем конфигурационном файле неверные данные! Укажите число секунд.")


if __name__ == "__main__":
    main()
