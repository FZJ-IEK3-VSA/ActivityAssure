"""
Helper script to encrypt HETUS data
"""

import getpass
from pathlib import Path
from cryptography.fernet import Fernet

from activity_validator.hetus_data_processing import load_data

# print(Fernet.generate_key().decode())

key = getpass.getpass("HETUS encryption key: ")
if key[-1] != "=":
    key += "="

fernet = Fernet(key.encode())

hetus_path = Path(r"D:\Daten\HETUS Data\HETUS 2010 full set\DATA")
enc_path = hetus_path.parent / "Data_encrypted"
enc_path.mkdir(parents=True, exist_ok=True)

for path in load_data.get_hetus_file_names().values():
    file_orig = Path(path)
    with open(file_orig) as f:
        content = f.read()
    encrypted = fernet.encrypt(content.encode())
    file_enc = enc_path / file_orig.name
    with open(file_enc, "wb") as f:
        f.write(encrypted)
