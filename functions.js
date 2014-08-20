var passwords;
var master_password_hash;
var master_password;

function parse_passwords() {
  // empty password list
  // http://stackoverflow.com/questions/3955229/remove-all-child-elements-of-a-dom-node-in-javascript
  var password_list = document.getElementById("password_list");
  password_list.innerHTML = '';
  // empty password information
  document.getElementById("password_name").textContent = "";
  document.getElementById("password_text").textContent = "";
  document.getElementById("decrypted_password").textContent = "";
  // get the password json
  password_json_textarea = document.getElementsByName("password_json")[0];
  password_json_textarea.style.background = 'red';
  password_json = password_json_textarea.value;
  // parse json
  // http://stackoverflow.com/questions/4935632/how-to-parse-json-in-javascript
  password_database = JSON.parse(password_json);
  if (password_database.passwords === undefined) {
    if (password_database[0] === undefined) {
      alert("Could not find passwords.");
      return;
    }
    passwords = password_database;
    master_password_hash = undefined;
  } else {
    passwords = password_database.passwords;
    master_password_hash = password_database.master_password_hash;
  }
  // sort passwords
  // http://stackoverflow.com/questions/8837454/sort-array-of-objects-by-single-key-with-date-value
  passwords.sort(function(p1, p2){
    if(p1.name < p2.name) return -1;
    if(p1.name > p2.name) return 1;
    return 0;
  });
  // insert passwords
  // http://stackoverflow.com/questions/3010840/loop-through-array-in-javascript
  for (var i = 0; i < passwords.length; i++) {
    password = passwords[i];
    password_list.innerHTML += '<input type="button" id="password_' + i + '" onclick="show_password_at(' + i + ')" class="password_button"/>\n';
    document.getElementById('password_' + i).value = password.name;
  }
  password_json_textarea.style.background = 'green';
  update_master_password();
};

// hex encoding and decoding
// http://snipplr.com/view/30964/hex-encode--decode-string-prototype/
String.prototype.hexDecode = function() {
  var r='';
  for( var i = 0; i < this.length; i += 2 ) {
    r += unescape( '%' + this.substr(i, 2));
  }
  return r;
}
String.prototype.hexEncode = function(){
  var r = '';
  var h;
  for( var i = 0; i < this.length; i++ ) {
    h = this.charCodeAt(i).toString(16);
    if (h.length < 2){
      h = "0" + h;
    } 
    r += h;
  }
  return r;
}

var s = "000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F202122232425262728292A2B2C2D2E2F303132333435363738393A3B3C3D3E3F404142434445464748494A4B4C4D4E4F505152535455565758595A5B5C5D5E5F606162636465666768696A6B6C6D6E6F707172737475767778797A7B7C7D7E7F808182838485868788898A8B8C8D8E8F909192939495969798999A9B9C9D9E9FA0A1A2A3A4A5A6A7A8A9AAABACADAEAFB0B1B2B3B4B5B6B7B8B9BABBBCBDBEBFC0C1C2C3C4C5C6C7C8C9CACBCCCDCECFD0D1D2D3D4D5D6D7D8D9DADBDCDDDEDFE0E1E2E3E4E5E6E7E8E9EAEBECEDEEEFF0F1F2F3F4F5F6F7F8F9FAFBFCFDFEFF".toLowerCase();
if (!(s.hexDecode().hexEncode() == s)) {
  alert("hex encoding not working");
}

function update_master_password() {
  if (master_password_hash === undefined) {
    return;
  }
  master_password_input = document.getElementById('master_password')
  raw_master_password = encode_utf8(master_password_input.value);
  //alert(raw_master_password);
  _master_password_hash = sha512(raw_master_password);
  //alert(_master_password_hash);
  master_password = _master_password_hash.hexDecode();
  master_password_hash2 = sha512(master_password);
  //alert(master_password_hash2 + " == " + master_password_hash);
  // change background color
  // http://stackoverflow.com/questions/197748/how-do-i-change-the-background-color-with-javascript
  if (master_password_hash2.toLowerCase() == master_password_hash.toLowerCase()) {
    master_password_input.style.background = "green";
  } else {
    master_password_input.style.background = "red";
  }
}

// encode and decode UTF-8
// http://ecmanaut.blogspot.ca/2006/07/encoding-decoding-utf8-in-javascript.html
// via http://stackoverflow.com/questions/13356493/decode-utf-8-with-javascript
function encode_utf8(s) {
  return unescape(encodeURIComponent(s));
}

function decode_utf8(s) {
  return decodeURIComponent(escape(s));
}

function show_password_at(index) {
  password = passwords[index];
  document.getElementById("password_name").textContent = password.name;
  document.getElementById("password_text").textContent = password.text;
  document.getElementById("decrypted_password").innerHTML = '<input type="button" onclick="show_password(' + index + ');" value="show password" id="show_password_button" /><div class="plain_password" id="plain_password"></div>';
}

function decrypt(password) {
  /* Python code
    encrypted_password = base64.b64decode(encrypted_password.encode('UTF-8'))
    salt = salt.encode('UTF-8')
    encryption_stream = hash_binary(master_password, salt) + \
                        hash_binary(salt, master_password)
    decrypted_password = []
    for i in range(len(encrypted_password)):
        decrypted_password.append(encrypted_password[i] ^ encryption_stream[i])
    decrypted_password = bytes(decrypted_password).decode('UTF-8')
  */
  
  // base64 decode
  // https://developer.mozilla.org/de/docs/Web/JavaScript/Base64_encoding_and_decoding
  encrypted_password = atob(password.encrypted_password);
  salt = encode_utf8(password.password_salt);
  encryption_stream = (sha512(master_password + salt) + sha512(salt + master_password)).hexDecode();
  decrypted_password = "";
  for (var i = 0; i < encrypted_password.length; i++) {
    character = encrypted_password.charCodeAt(i) ^ encryption_stream.charCodeAt(i); 
    decrypted_password += String.fromCharCode(character);
  }
  return decode_utf8(decrypted_password);
}

function show_password(index) {
  plain_password_container = document.getElementById('plain_password');
  password_button = document.getElementById('show_password_button');
  if (plain_password_container.textContent == "") {
    password = passwords[index];
    decrypted_password = decrypt(password);
    plain_password_container.textContent = decrypted_password;
    selectElementContents(plain_password_container);
    password_button.value = "hide password";
  } else {
    plain_password_container.textContent = "";
    password_button.value = "show password";
  }
}

// select password
// http://stackoverflow.com/questions/4183401/can-you-set-and-or-change-the-user-s-text-selection-in-javascript#4183448
function selectElementContents(el) {
    if (window.getSelection && document.createRange) {
        var sel = window.getSelection();
        var range = document.createRange();
        range.selectNodeContents(el);
        sel.removeAllRanges();
        sel.addRange(range);
    } else if (document.selection && document.body.createTextRange) {
        var textRange = document.body.createTextRange();
        textRange.moveToElementText(el);
        textRange.select();
    }
}