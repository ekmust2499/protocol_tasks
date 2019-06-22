class Query:
    def __init__(self, name, type, internet, byte):
        self.name = name
        self.type = type
        self.class_int = internet
        self.in_bytes = byte #сам запрос в виде байтов

    def __str__(self):
        return f" name: {self.name}, type: {self.type}, class_int: {self.class_int}"
