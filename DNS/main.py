import struct
import sys

import socket
from Query import *
from Answer import *
from Cache import *


IP_PORT = ("127.0.0.2", 53)

TYPES = {
    1: 'A',
    2: 'NS',
    6: 'SOA',
    12: 'PTR',
    28: 'AAAA'
}

REVERSE_TYPES = {
    'A': 1,
    'NS': 2,
    'SOA': 6,
    'PTR': 12,
    'AAAA': 28
}


class DNSParser:

    def __init__(self, data, cache):
        "Заголовок"
        self.data = data
        self.transaction_id = data[:2] #идентификатор записи
        self.flags = data[2:4] #флаги
        self.questions = int.from_bytes(data[4:6], 'big') #число запросов
        self.answer_rrs = int.from_bytes(data[6:8], 'big') #число ответов
        self.authority_rrs = int.from_bytes(data[8:10], 'big') #число авторитетных записей (Присутствует в ответе.
        # Информация в авторитетных записях включает имя сервера, хранящего авторитетные данные.)
        self.additional_rrs = int.from_bytes(data[10:12], 'big') #число дополнительных записей (Присутствует в ответе и содержит адреса авторитетных серверов.)

        "Запрос"
        index, query = read_query(data)
        self.query = query #Запрос, содержащий: имя (Имя домена или IP-адрес в поддереве IN-ADDR.ARPA), тип запроса (например А или NS), класс (IN для Интернета записывается как 1)

        "Отклики"
        self.answers = []
        self.auth = []
        self.add = []

        #Читаем отклики на запросы и сохраняем в кэше
        """
        Ответ содержит: 
        Имя (Имя узла для данной записи), 
        Тип записи, например SOA или А, записанный числовым кодом,
        Класс (IN соответствует 1),
        TTL (Время жизни 32-разрядное целое число со знаком, отражающее время кеширования записи),
        RDLENGTH (Длина записи) - Длина поля данных в записи о ресурсах,
        RDATA (Данные записи) - Например, для записи об адресе — значение IP-адреса. Запись SOA содержит обширные сведения.
        
        """
        if self.answer_rrs != 0:
            for i in range(self.answer_rrs):
                index, answer = self.read_answer(index, data)
                self.answers.append(answer)
                cache.append(answer, self.flags)
                index = index
        # Читаем записи об уполномоченных серверах и сохраняем в кэше
        if self.authority_rrs != 0:
            for i in range(self.authority_rrs):
                index, answer = self.read_answer(index, self.data)
                self.auth.append(answer)
                cache.append(answer, self.flags)
                index = index
        # Читаем ответы на дополнительные записи и сохраняем в кэше
        if self.additional_rrs != 0:
            for i in range(self.additional_rrs):
                index, answer = self.read_answer(index, self.data)
                self.add.append(answer)
                cache.append(answer, self.flags)
                index = index

    def read_answer(self, point, data):
        count_readed, site_name = read_url(point, self.data) #имя хоста в отклике
        type = TYPES[int.from_bytes(data[count_readed:count_readed + 2], 'big')] #тип ресурсной записи
        class_int = int.from_bytes(data[count_readed + 2:count_readed + 4], 'big') #класс ресурсной записи
        ttl = int.from_bytes(data[count_readed + 4:count_readed + 8], 'big') #ttl
        data_len = int.from_bytes(data[count_readed + 8:count_readed + 10], 'big') #длина в байтах последующей секции RDATA

        if type is 'A' or type is 'AAAA':
            rdata = data[count_readed+10:count_readed+10+data_len] #если тип ресусной записи А или АААА, т.е. хотим получить IP-адрес, то считываем его
        else:
            _, rdata = read_url(count_readed + 10, self.data) #если тип ресусной записи NS или PTR, т.е. хотим получить домен, то считываем его
        answer = Answer(site_name, type, class_int, ttl, rdata)
        return count_readed + 10 + data_len, answer

    def create_packet(self, query):
        answers_bytes = b''
        auth_bytes = b''
        count_answ_rrs = 0
        count_auth_rrs = 0
        count_addt_rrs = struct.pack('!h', 0)
        #flags = b""
        flags = b'\x85\x80' #10000101 10000000
        #1 - answer (0 - request)
        #0000 - opcode (стандартный запрос)
        #1 - авторитетный ответ (0 - нет)
        #0 - не обрезано
        #1 - требуется рекурсия (0 - нет)
        #1 - рекурсия возможна (сервер поддерживает рекурсию)
        #000 - всегда нули
        #0000 - rcode (нет ошибок) (3 - ошибка имени)

        if self.query.type in cache.cache[self.query.name]:
            count_answ_rrs = len(cache.cache[self.query.name][self.query.type])
            for answ in cache.cache[self.query.name][self.query.type]:
                answers_bytes += answ[0].in_bytes
                #flags = cache.cache[self.query.name][self.query.type][0][2]
        result = self.transaction_id + flags + b'\x00\x01' #1 запрос
        result += struct.pack('!h', count_answ_rrs) \
                  + struct.pack('!h', count_auth_rrs)\
                  + count_addt_rrs \
                  + query.in_bytes
        result += answers_bytes
        result += auth_bytes
        return result

    def __str__(self):
        result = str(self.transaction_id) + "  " + \
                 str(self.flags) + "  " + \
                 str(self.questions) + "  " + \
                 str(self.answer_rrs) + "  " + \
                 str(self.authority_rrs) + "  " + \
                 str(self.additional_rrs) + "\n" + \
                 str(self.query) + "\n"
        for answer in self.answers:
            result += str(answer) + "\n"
        return result


#возвращает имя запрашиваемого хоста и индекс данных после имени
def read_url(d_index, data, recurce=False):
    index = d_index
    url = ""
    count_bytes = data[index]
    while count_bytes != 0 and count_bytes < 192:
        for i in range(count_bytes):
            url += chr(data[1+index+i])
        url += '.'
        index += count_bytes + 1
        count_bytes = data[index]
    if count_bytes >= 192:
        point_offset = int.from_bytes(data[index: index+2], 'big') - 49152
        url += read_url(point_offset, data, True)[1]
        index += 1

    return index+1, url


def url_to_bytes(url):
    chuncs = url.split('.')
    count_bytes = 0
    result = b''
    for chunc in chuncs:
        count_symbol = len(chunc)
        result += int.to_bytes(count_symbol, 1, 'big')
        count_bytes += 1
        for symbol in chunc:
            result += bytes(symbol, 'utf-8')
            count_bytes += 1
    return result, count_bytes


def read_query(data):
    index, url = read_url(12, data) #12 байт на заголовок
    type = TYPES[int.from_bytes(data[index:index + 2], 'big')] #тип запроса
    class_int = int.from_bytes(data[index + 2:index + 4], 'big') #класс запроса
    query = Query(url, type, class_int, data[12:index + 4])
    return index + 4, query #возвращает запрос и индекс данных, после запроса


# 212.193.163.7
def get_data_from_server(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.sendto(data, ('192.168.43.1', 53))
        sock.settimeout(2)
        answer = sock.recvfrom(1024)[0]
        return answer, True
    except socket.timeout or socket.gaierror or socket.error:
        print('Сервер недоступен!')
        return b'', False
    except OSError:
        print('Сеть отключена!')
        return b'', False


def run_server(cache):
    timeout = 2
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(IP_PORT)
        sock.settimeout(timeout)
        try:
            while True:
                try:
                    data, address = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    continue
                    #sys.exit("Соединение разорвано")
                _, query = read_query(data) #читаем и обрабатываем запрос
                if query in cache:
                    print("FROM CACHE")
                    query_parsed = DNSParser(data, cache)
                    data_to_send = query_parsed.create_packet(query)
                else:
                    print("FROM SERVER")
                    data_to_send, status = get_data_from_server(data)
                    if status:
                        DNSParser(data_to_send, cache)
                sock.sendto(data_to_send, address)
                print("SEND")
        finally:
            cache.write_file()


if __name__ == '__main__':
    cache = Cache()
    try:
        run_server(cache)
    except KeyboardInterrupt:
        cache.write_file()
        exit()
