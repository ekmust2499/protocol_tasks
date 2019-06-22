from main import url_to_bytes, REVERSE_TYPES


class Answer:
    def __init__(self, name, type_answ, class_int, ttl, rdata):
        self.name = name
        self.type = type_answ
        self.class_int = class_int
        self.ttl = ttl
        self.rdata = rdata
        self.in_bytes = self.generate_packet()

    def generate_packet(self):
        result, _ = url_to_bytes(self.name)
        result += int.to_bytes(REVERSE_TYPES[self.type], 2, 'big')
        result += int.to_bytes(self.class_int, 2, 'big')
        result += int.to_bytes(self.ttl, 4, 'big')
        if self.type is 'NS' or self.type is 'PTR':
            bytes_name, count_b = url_to_bytes(self.rdata[:-1])
            result += int.to_bytes(count_b+1, 2, 'big') + bytes_name + b'\x00'
        else:
            if type(self.rdata) is str:
                result += int.to_bytes(4, 2, 'big') + bytes(self.rdata, "utf-8")
            else:
                result += int.to_bytes(4, 2, 'big') + self.rdata
        return result

    def __str__(self):
        return f"name: { self.name}, type: {self.type}, class_int: {self.class_int}, " \
               f"ttl: {self.ttl}, sec_name: {self.rdata}"
