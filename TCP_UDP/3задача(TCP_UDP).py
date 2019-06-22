import argparse
import socket
import sys
import binascii
from subprocess import Popen, PIPE, run, TimeoutExpired
import struct
import re
import urllib.request
from functools import partial
import time
from multiprocessing import Pool, Process
from threading import Thread

answer_from_DNS = binascii.unhexlify("AA AA".replace(" ", "").replace("\n", ""))

message = "AA AA 01 00 00 01 00 00 00 00 00 00 07 65 78 " \
          "61 6d 70 6c 65 03 63 6f 6d 00 00 01 00 01".replace(" ", "").replace("\n", "")
          #запрос ресурсной записи типа АААА домена example.com

TCP = {
       'POP3': b'USER ekmust', #110
       'HTTP': b'GET http://vk.com/ http/1.1\r\n\r\n', #80 yandex.ru
       'SMTP': b'EHLO\r\n\r\n', #25, 587
       'DNS': binascii.unhexlify(message) #53
       }

msg = '\x1b' + 47 * '\0'

UDP = {
       'SNTP': msg.encode("utf-8"), #123 time.windows.com
       'DNS': binascii.unhexlify(message) #53 dns.yandex.ru, e1.ru
}

answer_from_SMTP = [b'211', b'214', b'220', b'221', b'250', b'251',
                    b'252', b'354', b'421', b'450', b'451', b'452',
                    b'500', b'501', b'502', b'503', b'504', b'550',
                    b'551', b'552', b'553', b'554'] #ответы, возможные от сервера SMTP

answer = {
          'HTTP': lambda packet: b'HTTP' in packet or b'html' in packet,
          'SMTP': lambda packet: packet[0:3] in answer_from_SMTP,
          'POP3': lambda packet: packet.startswith(b'+OK') or packet.startswith(b'-ERR'),
          'SNTP': lambda packet: sntp_check(packet),
          'DNS': lambda packet: packet.startswith(answer_from_DNS)
}


def sntp_check(packet):
    try:
        struct.unpack("!12I", packet)
        return True
    except struct.error:
        return False


def get_protocol_from_tcp(addr, port, proto_and_pack):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect((addr, port))
            sock.send(proto_and_pack[1])
            sock.settimeout(60)
            answ = sock.recv(512)

            if answer[proto_and_pack[0]](answ):
                return proto_and_pack[0]
        except socket.error or socket.timeout:
            return None


def get_protocol_from_udp(addr, port, proto_and_pack):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.sendto(proto_and_pack[1], (addr, port))
            sock.settimeout(2)
            answ = sock.recv(1024)

            if answer[proto_and_pack[0]](answ):
                return proto_and_pack[0]
        except socket.error or socket.timeout:
            return None


def check_tcp_ports(addr, start, end):
    for port in range(start, end+1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            try:
                sock.connect((addr, port))
                pool = Pool(processes=4)
                pr = partial(get_protocol_from_tcp, addr, port)
                x = pool.map(pr, zip(TCP.keys(), TCP.values()))
                result = [i for i in x if i is not None]
                if len(result) > 0:
                    print(f"TCP port number {port} is open - {result[0]}")
                else:
                    print(f"TCP port number {port} is open - unknown")
            except socket.error or socket.timeout:
                pass
            except socket.gaierror:
                sys.exit("Отсутствует подключение к интернету!")


def start_get_udp_protocol(addr, port):
    pool = Pool(processes=2)
    pr = partial(get_protocol_from_udp, addr, port)
    x = pool.map(pr, zip(UDP.keys(), UDP.values()))
    result = [i for i in x if i is not None]
    if len(result) > 0:
        print(f"UDP port number {port} is open - {result[0]}")
    else:
        print(f"UDP port number {port} is open - unknown")


def check_udp_ports(addr, start, end):
    for port in range(start, end+1):
        with socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP) as sniffer:
            sniffer.bind(('localhost', 0))
            sniffer.settimeout(1)
            sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
            sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                try:
                    sock.sendto(b"from ekmust", (addr, port))
                    data = sniffer.recv(1024)
                    type, code = struct.unpack('bb', data[20:22])
                    if type == 3 and code == 3: #порт недостижим
                        pass
                    elif type == 3 and code in [1, 2, 9, 10, 13]: #порт фильтруется
                        start_get_udp_protocol(addr, port)
                    else:
                        pass
                except socket.timeout:
                    start_get_udp_protocol(addr, port)
                except socket.gaierror:
                    sys.exit("Отсутствует подключение к интернету!")
                sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)


def connected(host='http://google.com'):
    try:
        urllib.request.urlopen(host)
        return True
    except IOError:
        raise ConnectionError


def main():
    parser = argparse.ArgumentParser(description="Program for Autonomous Systems tracing")
    parser.add_argument("address", action="store", help="IP address or domain, to which you want to connect.")
    parser.add_argument("start", action="store", help="Beginning of port range.")
    parser.add_argument("end", action="store", help="End of port range.")
    args = parser.parse_args()

    try:
        start = int(args.start)
        end = int(args.end)
    except ValueError:
        sys.exit("Некорректный ввод данных: введите 2 числа, чтобы задать начало и конец диапазона портов.")
    if start > 65535 or start < 0:
        sys.exit("Некорректный ввод данных: начало диапазона выходит за пределы допустимых значений.")
    if end > 65535 or end < 0:
        sys.exit("Некорректный ввод данных: конец диапазона выходит за пределы допустимых значений.")
    if start > end:
        sys.exit("Некорректный ввод данных: начало диапазона портов превышает конец.")
    print(f'Сканер TCP и UDP портов на адресе: {args.address} в диапазоне [{args.start}:{args.end}]')

    try:
        connected()
    except ConnectionError:
        sys.exit("Отсутствует подключение к интернету!")

    try:
        socket.gethostbyname(args.address)
    except socket.gaierror:
        sys.exit("Неверное имя домена!")

    try:
        process1 = Process(target=check_tcp_ports, args=(args.address, start, end))
        process2 = Process(target=check_udp_ports, args=(args.address, start, end))
        process1.start()
        process2.start()
    except socket.gaierror:
        sys.exit("Отсутствует подключение к интернету!")


if __name__ == "__main__":
    main()
