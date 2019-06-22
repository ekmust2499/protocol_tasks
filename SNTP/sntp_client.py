import socket
import struct
import time


def main():
    try:
        with socket.socket() as sock:
            sock.connect(('localhost', 55))
            sock.send(b'want time')
            data = sock.recv(512)
            if data:
                lis = struct.unpack('!12I', data)
                time_from_server = struct.unpack('!12I', data)[10]
                print(time.ctime(time_from_server))
            sock.close()
    except socket.timeout:
        print("Timeout!")
    except socket.error:
        print("Error with socket")

main()

