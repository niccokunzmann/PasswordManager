import hashlib
import os
import base64

hash_algorithm = hashlib.sha512

def hash_hex(*all_bytes):
    algorithm = hash_algorithm()
    for bytes in all_bytes:
        algorithm.update(bytes)
    return algorithm.hexdigest()

def hash_binary(*all_bytes):
    algorithm = hash_algorithm()
    for bytes in all_bytes:
        algorithm.update(bytes)
    return algorithm.digest()

def _encrypt_password(password, salt, master_password):
    assert isinstance(password, bytes)
    assert isinstance(salt, bytes)
    assert isinstance(master_password, bytes)
    encryption_stream = hash_binary(master_password, salt) + \
                        hash_binary(salt, master_password)
    print(base64.b16encode(encryption_stream))
    assert len(encryption_stream) >= len(password)
    encrypted_password = []
    for i in range(len(password)):
        encrypted_password.append(password[i] ^ encryption_stream[i])
    return bytes(encrypted_password)

def encrypt_password(password, salt, master_password):
    password = password.encode('UTF-8')
    salt = salt.encode('UTF-8')
    encrypted_password = _encrypt_password(password, salt, master_password)
    decrypted_password = _encrypt_password(encrypted_password, salt, master_password)
    assert decrypted_password == password
    return base64.b64encode(encrypted_password).decode('UTF-8')

def decrypt_password(encrypted_password, salt, master_password):
    encrypted_password = base64.b64decode(encrypted_password.encode('UTF-8'))
    salt = salt.encode('UTF-8')
    decrypted_password = _encrypt_password(encrypted_password, salt, master_password)
    encrypted_password2 = _encrypt_password(decrypted_password, salt, master_password)
    assert encrypted_password == encrypted_password2
    return decrypted_password.decode('UTF-8')

def new_salt():
    return hash_hex(os.urandom(20))

# "".join(map(chr, range(33, 127))) without "
PASSWORD_CHARACTERS =  '''!#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'''

def new_random_password(length = 25, characters = PASSWORD_CHARACTERS):
    s = ""
    assert len(characters) <= 256
    while len(s) < length:
        index = ord(os.urandom(1))
        if index >= len(characters):
            continue
        s += characters[index]
    return s


__all__ = ['hash_hex', 'encrypt_password', 'decrypt_password', 'new_salt',
           'new_random_password']
