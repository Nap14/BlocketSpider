from parser import AllPageParser

if __name__ == '__main__':
    data = AllPageParser(limit=2)
    data.write_to_json()
