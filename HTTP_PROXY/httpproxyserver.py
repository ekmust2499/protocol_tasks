import socket
import select
import re
import ssl

input_list = []
channel = {}
get_page_host = re.compile('CONNECT (.+) ')
BOUNDARY = "#______________________________________________________#"


def on_accept(server):
    connection, addr = server.accept()
    print("Соединение с " + str(connection.getpeername()) + " установлено")
    try:
        data = connection.recv(4096).decode('utf-8')
        if not data:
            return
        data_new = data.encode()
        print(data)
    except:
        return
    if data.startswith('CONNECT'):
        page, port = re.findall(get_page_host, data)[0].split(" ")[0].split(":")
        if page.startswith("reklama") \
                or page.startswith("ad")\
                or page.startswith("top") \
                or page.startswith("zen")\
                or page.startswith("an") \
                or page.startswith("ib") \
                or page.startswith("cstatic")\
                or page.startswith("sync") \
                or page.startswith("secure") \
                or page.startswith("privacy"):
            connection.close()
            print("РЕКЛАМА ЗАБЛОКИРОВАНА!!!")
            print(BOUNDARY)
            return
        try:
            #открываем соединение с кем клиенту надо подключиться
            conn_with_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn_with_serv.connect((page, int(port)))
            input_list.append(connection)
            input_list.append(conn_with_serv)
            channel[connection] = conn_with_serv
            channel[conn_with_serv] = connection
            connection.send(b'HTTP/1.1 200 Connection established\r\n\r\n') #посылаем ответ, что соединение установлено и можно продолжать
        except Exception as e:
            print(e)
            print("Не удается установить соединение с удаленным сервером.")
            print("Закрытие соединения со стороны клиента: ", addr)
            connection.close()
            return
    else:
        #если это не CONNECT, а GET например запрос
        spl = data.split('\n')
        host = ''
        for el in spl:
            if "Host: " in el:
                host = el.split(' ')[1].strip()
                break
        conn_with_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_with_serv.connect((host, 80))
        input_list.append(connection)
        input_list.append(conn_with_serv)
        channel[connection] = conn_with_serv
        channel[conn_with_serv] = connection
        conn_with_serv.send(data_new) #отправляем от клиента данные куда надо
    print(BOUNDARY)


def on_close(sock):
    #Разрываем соединение (нет данных от него)
    print("Соединение с " + str(sock.getpeername()) + " разорвано")
    print(BOUNDARY + "\n")
    input_list.remove(sock)
    input_list.remove(channel[sock])
    out = channel[sock]
    channel[out].close()
    channel[sock].close()
    del channel[out]
    del channel[sock]


def main_loop(server):
    input_list.append(server)
    while True:
        try:
            input, output, except_ = select.select(input_list, [], [])
            for sock in input:
                if sock == server:
                    on_accept(server)
                    break
                try:
                    data = sock.recv(4096) #читаем данные
                    if len(data) == 0:
                        on_close(sock)
                    else:
                        channel[sock].send(data) #отправляем данные
                except:
                    pass
        except ValueError:
             pass


def main():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(('127.0.0.1', 80))
        server.listen(200)

        main_loop(server)
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
