n = 105312291668557186697918027513529248857806893649219117400977309697
e = 65537
c = 56084235340151536769364177314071579165242999204895873082547191150

for exponent in range(2, n.bit_length()):
    p = (1 << exponent) - 1
    if n % p == 0:
        q = n // p
        d = pow(e, -1, (p - 1) * (q - 1))
        message = pow(c, d, n)
        print(message.to_bytes((message.bit_length() + 7) // 8, 'big').decode())
        break
else:
    raise ValueError('Aucun facteur trouvé.')
