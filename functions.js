var passwords;
var master_password_hash;
var master_password;

function parse_passwords() {
  // empty password list
  // http://stackoverflow.com/questions/3955229/remove-all-child-elements-of-a-dom-node-in-javascript
  var password_list = document.getElementById("password_list");
  password_list.innerHTML = '';
  // get the password json
  password_json_textarea = document.getElementsByName("password_json")[0];
  password_json = password_json_textarea.value;
  // parse json
  // http://stackoverflow.com/questions/4935632/how-to-parse-json-in-javascript
  password_database = JSON.parse(password_json);
  if (password_database.passwords === undefined) {
    if (password_database[0] === undefined) {
      alert("Could not parse passwords");
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
  for (var i = 0; i < passwords.Length; i++) {
    password = passwords[i];
    password_list.innerHTML += '' + 
      '<div class="password_entry">'+
    +   '<input type="button" name="password_' + i + '" value="' + password.name + '" onclick="decrypt_password_at(' + i + ')" />'
    + '</div>'
  }
  update_master_password();
};

// hex encoding and decoding
// http://snipplr.com/view/30964/hex-encode--decode-string-prototype/
String.prototype.hexDecode = function(){var r='';for(var i=0;i<this.length;i+=2){r+=unescape('%'+this.substr(i,2));}return r;}
String.prototype.hexEncode = function(){var r='';var i=0;var h;while(i<this.length){h=this.charCodeAt(i++).toString(16);while(h.length<2){h=h;}r+=h;}return r;}

function update_master_password() {
  if (master_password_hash === undefined) {
    return;
  }
  master_password_input = document.getElementById('master_password')
  raw_master_password = master_password_input.value;
  _master_password_hash = sha512(raw_master_password);
  master_password = _master_password_hash.hexDecode();
  master_password_hash2 = sha512(master_password);
  // change background color
  // http://stackoverflow.com/questions/197748/how-do-i-change-the-background-color-with-javascript
  if (master_password_hash2.toLowerCase() == master_password_hash.toLowerCase()) {
    master_password_input.style.background = "green";
  } else {
    master_password_input.style.background = "red";
  }
}