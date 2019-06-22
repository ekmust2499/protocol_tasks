import subprocess
import argparse
import socket
import re
import urllib.request
import json
import sys


def parse_ip_tracert(ip):
    p = subprocess.Popen(['tracert', ip], stdout=subprocess.PIPE)
    number = 0
    while True:
        line = p.stdout.readline()
        if not line:
            break
        line = "".join(line.decode("866").split())
        if "Неудаетсяразрешитьсистемноеимяузла" in line:
            raise ValueError("Невозможно распознать IP-адрес!")
        elif "Заданныйузелнедоступен" in line:
            raise ValueError("Отсутствует подключение к интернету")
        elif "Ошибкапередачи" in line:
            raise ValueError("Ошибка передачи данных.")

        if len(re.findall(r'\*\*\*', line)) == 0:
            ip = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", line)
            if len(ip) != 0:
                if number > 0:
                    yield number, ip[0]
                    number += 1
                else:
                    number += 1
        else:
            break


def tracert(number, ip):
    site = "http://ipinfo.io/{}/json".format(ip)
    try:
        response = urllib.request.urlopen(site)
        data = json.loads(response.read())
        if 'bogon' in data.keys():
            return '{:>3}'.format(number) + '    {:>15}'.format(ip)
        elif 'error' in data.keys():
            return ValueError("Data is not correct!")
        else:
            country = data['country']
            as_and_provider = re.split(r' ', data['org'], maxsplit=1)
            if len(as_and_provider) == 2:
                as_name = as_and_provider[0][2:]
                provider = as_and_provider[1]
            elif len(as_and_provider) == 1 and as_and_provider[0][:2] == "AS":
                as_name = as_and_provider[0]
                provider = ""
            elif len(as_and_provider) == 1:
                as_name = ""
                provider = as_and_provider[0]
            return '{:>3}'.format(number) + '    {:>15}'.format(ip) + '    {:>5}'.format(as_name) +\
                   '    {:>3}'.format(country) + '    {:>20}'.format(provider)
    except urllib.error.HTTPError:
        return "IP does not exist!"


def main():
    parser = argparse.ArgumentParser(description="Program for Autonomous Systems tracing")
    parser.add_argument("host", action="store", help="IP address or domain, to which need to check whois.")
    args = parser.parse_args()
    try:
        urllib.request.urlopen("http://ipinfo.io/")
        try:
            x = re.findall(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", args.host)
            ip = ""
            if not x:
                try:
                    ip = socket.gethostbyname(args.host)
                    print(f"Трассировка автономных систем к {args.host} [{ip}]:")
                except socket.gaierror:
                    print("Невозможно распознать домен!")
                    sys.exit(2)
            else:
                ip = args.host
                print(f"Трассировка автономных систем к {ip}:")
            print('{:>3}'.format("№") + '    {:>15}'.format("IP") + '    {:>5}'.format("AS") + \
                  '    {:>3}'.format("Country") + '    {:>15}'.format("Provider"))
            for number, ip in parse_ip_tracert(ip):
                print(tracert(number, ip))
        except ValueError as e:
            print(e)
    except IOError:
        print("Отсутствует подключение к интернету")


if __name__ == "__main__":
    main()
