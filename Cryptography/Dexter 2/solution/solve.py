from functools import reduce
from operator import xor as combine


def xor(*items):
    length = max(map(len, items))
    return bytes(reduce(combine, (item[index % len(item)] for item in items)) for index in range(length))




KEY3 = bytes.fromhex("55a386208a16645a334a766379427a5957786c")
KEY43 = bytes.fromhex("349dcc56e87f262e517920cfa7613833341607")
KEY42 = bytes.fromhex("65d9ac2c253f2e2e25653acdec1a340951065e")
KEY21 = bytes.fromhex("a8849b39003a1b3b10180438007f0101000446")
KEYFLAG = bytes.fromhex("cc561b36ab1c7f50131a149a94725c4660771ed86c0837d83740")

KEY4 = xor(KEY43, KEY3)
KEY2 = xor(KEY42, KEY4)
KEY1 = xor(KEY21, KEY2)

FLAG = xor(KEYFLAG, KEY3, KEY1, KEY4, KEY2)

print(FLAG)
