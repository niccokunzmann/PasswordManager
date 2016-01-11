import json
from dialog import ask_password, ask_add_password
from encryption import hash_binary, hash_hex
from encryption import encrypt_password, decrypt_password
from encryption import new_salt, new_random_password

import base64
import threading
import os
import traceback
from contextlib import suppress

MASTER_PASSWORD_IN_MEMORY_SECONDS = 10

class InvalidMasterPassword(Exception):
    pass

class TransactionAbort(Exception):
    pass

class Cancel(Exception):
    pass

class MasterPassword(object):

    _deletion_timer = None
    _bytes = None
    _hash = None
    
    def __init__(self, hash = None):
        """hash must be a unicode hexdigest or None"""
        
        self.hash = hash

    @property
    def seconds_in_memory(self):
        return MASTER_PASSWORD_IN_MEMORY_SECONDS

    def open_ask_dialog(self):
        return ask_password('master password:')

    def ask(self):
        password = self.open_ask_dialog()
        if password is None:
            raise Cancel("The dialog was canceled.")
        try:
            self.password = password
        except InvalidMasterPassword:
            self.ask()

    def initialize_master_password(self):
        password1 = ask_password('set master password:')
        password2 = ask_password('retype master password:')
        if password1 is None or password2 is None:
            raise Cancel("The dialog was canceled.")
        if password1 == password2:
            self.password = password1
        else:
            self.initialize_master_password()
            
    @property
    def password(self):
        raise TypeError('the password can not be used. Use bytes instead.')

    @password.setter
    def password(self, password):
        # do not use the original password but the hash instead
        password_bytes = password.encode('UTF-8')
        self.bytes = hash_binary(password_bytes)
        self.hash = hash_hex(self.bytes)
        assert password_bytes != self.bytes
        assert password_bytes != self.hash_bytes
        assert self.bytes != self.hash_bytes

    @property
    def bytes(self):
        if self._bytes is None:
            self.ask()
        else:
            self.refresh_timer()
        return self._bytes

    @bytes.setter
    def bytes(self, bytes):
        self.refresh_timer()
        self._bytes = bytes

    def has_bytes(self):
        return self._bytes is not None

    def refresh_timer(self):
        if self._deletion_timer is not None:
            self._deletion_timer.cancel()
        self._deletion_timer = threading.Timer(self.seconds_in_memory,
                                             self.delete)
        self._deletion_timer.start()

    @property
    def hash(self):
        if self._hash is None:
            self.initialize_master_password()
        if self.has_bytes(): # negligible race condition
            assert self._hash == hash_hex(self.bytes)
        return self._hash

    @hash.setter
    def hash(self, hash):
        assert hash is None or all(character in "0123456789abcdef" for character in hash)
        if self._hash is None:
            self._hash = hash
        elif self._hash != hash:
            raise InvalidMasterPassword("The entered master password does not match the original.")

    @property
    def hash_bytes(self):
        return base64.b16decode(self.hash.encode('UTF-8').upper())
        
    def delete(self):
        self._bytes = None

    def decrypt_password(self, encrypted_password, salt):
        return decrypt_password(encrypted_password, salt, self.bytes)

    def encrypt_password(self, password, salt):
        return encrypt_password(password, salt, self.bytes)

class Database(object):

    _config = None
    _master_password = None
    javascript_template_path = 'passwords_viewer_template.js'
    javascript_path = 'passwords_viewer.js'
    auto_save_to_javascript = True

    new_master_password = MasterPassword

    def __init__(self, file_name):
        self.file_name = file_name
        self.with_nesting = 0

    def save_to_javascript(self):
        with suppress(PermissionError):
            with open(self.file_name) as source_file, \
                 open(self.javascript_template_path) as javascript_template_file, \
                 open(self.javascript_path, 'w') as javascript_file:
                json = source_file.read()
                template = javascript_template_file.read()
                source = template.format(passwords = json)
                javascript_file.write(source)

    @property
    def master_password(self):
        """the master password of the database"""
        if self._master_password is None:
            with self:
                hash = self.config.get('master_password_hash', None)
                self._master_password = self.new_master_password(hash)
                self.config['master_password_hash'] = self._master_password.hash
        return self._master_password

    @property
    def config(self):
        if self._config is None:
            raise ValueError('Use the with statement!')
        return self._config

    @config.setter
    def config(self, value):
        self._config = value

    def new_config(self):
        return {u'passwords':[]}

    def __enter__(self):
        if self.with_nesting == 0:
            if os.path.isfile(self.file_name):
                with open(self.file_name) as file:
                    self.config = json.load(file)
            else:
                self.config = self.new_config()
        self.with_nesting += 1

    def __exit__(self, ty, err, tb):
        self.with_nesting -= 1
        assert self.with_nesting >= 0
        if self.with_nesting == 0:
            config = self.config
            self.config = None
            if ty is not None or err is not None or tb is not None:
                raise TransactionAbort('An error aborted the transaction.')
            with open(self.file_name, 'w') as file:
                json.dump(config, file)
            if self.auto_save_to_javascript:
                self.save_to_javascript()

    @property
    def _passwords(self):
        return self.config[u'passwords']

    def new_password_entry(self, entry = {}):
        return PasswordEntry(self, entry, self.master_password)

    def add_password_entry(self, entry):
        dict = entry.asDict()
        if dict not in self._passwords:
            self._passwords.append(dict)

    def remove_password_entry(self, entry):
        dict = entry.asDict()
        while dict in self._passwords:
            self._passwords.remove(dict)

    @property
    def passwords(self):
        """the passwords in the database"""
        with self:
            entries = [self.new_password_entry(entry) for entry in self._passwords]
        entries.sort(key = lambda entry: str(entry.name).lower())
        return entries

    def add_new_password_from_user(self):
        return self.new_password_entry().fill_from_user()

    def add_new_password_from_export(self, export):
        return self.new_password_entry().fill_from_export(export)

    def export_all(self):
        return [entry.export() for entry in self.passwords]

    def export_all_json(self, file):
        return json.dump(self.export_all(), file, sort_keys=True, indent=4)

    def import_all(self, passwords, log_file):
        successes = []
        for password in passwords:
            with self:
                try:
                    with self:
                        entry = self.add_new_password_from_export(password)
                        successes.append(password.get("name", str(password)))
                except:
                    traceback.print_exc(file = log_file)
                    print("Failed: ", password, file = log_file)
        for success in successes:
            print("Success:", success, file = log_file)

    def import_all_json(self, file, log_file):
        try:
            passwords = json.load(file)
            self.import_all(passwords, log_file)
        except:
            traceback.print_exc(file = log_file)

class PasswordEntry(object):

    attributes = set()

    def fill_from_user(self):
        result = ask_add_password(password = new_random_password())
        if result is None:
            return
        name, password, text = result
        return self.fill_from_arguments(name = name,
                                        password = password,
                                        text = text,
                                        deleted = False)

    def fill_from_arguments(self, **attributes):
        return self.fill_from_dict(attributes)

    def fill_from_export(self, export):
        export = export.copy()
        for attribute in list(export.keys()):
            if attribute not in self.attributes:
                export.pop(attribute)
        export['deleted'] = False
        return self.fill_from_dict(export)

    def fill_from_dict(self, dictionairy):
        if not set(dictionairy.keys()) <= self.attributes:
            print(self.attributes)
            print(set(dictionairy.keys()))
            raise ValueError('Unknown attributes {} should be {}'.format(
                ', '.join(set(dictionairy.keys()) - self.attributes),
                ', '.join(self.attributes)))
        for attribute in self.attributes:
            if attribute in dictionairy:
                setattr(self, attribute, dictionairy[attribute])
        self.database.add_password_entry(self)
        return self

    def __init__(self, database, dictionairy, master_password):
        self.database = database
        self.dictionairy = dictionairy
        self.master_password = master_password

    @property
    def name(self):
        return self.dictionairy[u'name']
    @name.setter
    def name(self, value):
        with self.database:
            self.dictionairy[u'name'] = value
    attributes.add('name')

    @property
    def password(self):
        encrypted_password = self.dictionairy[u'encrypted_password']
        password_salt = self.dictionairy[u'password_salt']
        return self.master_password.decrypt_password(encrypted_password, password_salt)
    @password.setter
    def password(self, password):
        "encrypt the password"
        with self.database:
            password_salt = self.new_salt()
            encrypted_password = self.master_password.encrypt_password(password, password_salt)
            self.dictionairy[u'password_salt'] = password_salt
            self.dictionairy[u'encrypted_password'] = encrypted_password
    attributes.add('password')

    new_salt = staticmethod(new_salt)

    @property
    def text(self):
        return self.dictionairy[u'text']
    @text.setter
    def text(self, value):
        with self.database:
            self.dictionairy[u'text'] = value
    attributes.add('text')

    @property
    def deleted(self):
        return self.dictionairy[u'deleted']
    
    @deleted.setter
    def deleted(self, value):
        with self.database:
            self.dictionairy[u'deleted'] = value
    attributes.add('deleted')

    def asDict(self):
        return self.dictionairy

    def remove(self):
        self.database.remove_password_entry(self)

    def export(self):
        return dict(name = self.name, password = self.password, text = self.text)

    def __eq__(self, other):
        return other == self.dictionairy

    def __hash__(self):
        return hash(self.dictionairy)

    def new_entry(self, entry = {}):
        return self.database.new_password_entry(entry)

    def duplicate(self, **attributes):
        new_entry = self.new_entry(self.dictionairy.copy())
        new_entry.fill_from_dict(attributes)
        return new_entry

    @property
    def as_list_entry(self):
        return self.name
