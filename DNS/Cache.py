import time
import pickle


#В кэше хранятся только ответы на запросы!

class Cache:
    def __init__(self):
        self.cache = dict(dict())
        self.load_file()

    def write_file(self):
        with open('pickle.p', 'wb') as file:
            pickle.dump(self.cache, file)

    def load_file(self):
        with open('pickle.p', 'rb') as file:
            try:
                cache = pickle.load(file)
                print("CACHE IS LOADED")
                self.cache = cache
            except EOFError:
                self.cache = dict(dict())
            except Exception:
                print('Проблемы с кэшем на диске')

    def append(self, answer, flags):
        if answer.name in self.cache:
            if answer.type in self.cache[answer.name]:
                self.cache[answer.name][answer.type].append((answer, time.time() + answer.ttl, flags))
            else:
                self.cache[answer.name][answer.type] = [(answer, time.time() + answer.ttl, flags)]
        else:
            self.cache[answer.name] = {answer.type: [(answer, time.time() + answer.ttl, flags)]}

    def __contains__(self, item):
        if item.name in self.cache:
            if item.type in self.cache[item.name]:
                for answer in self.cache[item.name][item.type]:
                    if answer[1] < time.time(): #если время кэширования истекло, то удаляем запись из кэша
                        #time.time() -  количество секунд, прошедших с момента начала эпохи (01.01.1970)
                        self.cache[item.name].pop(item.type)
                        return False
                return True
            if 'SOA' in self.cache[item.name]:
                for answer in self.cache[item.name]['SOA']:
                    if answer[1] < time.time():
                        self.cache[item.name].pop('SOA')
                        return False
                return True
