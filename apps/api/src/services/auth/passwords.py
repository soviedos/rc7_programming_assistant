import string

from pwdlib import PasswordHash

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def validate_password_rules(password: str) -> str | None:
    if len(password) < 8:
        return "La nueva contraseña debe tener al menos 8 caracteres."

    if len(password) > 16:
        return "La nueva contraseña debe tener como máximo 16 caracteres."

    if not any(character.isupper() for character in password):
        return "La nueva contraseña debe incluir al menos una letra mayúscula."

    if not any(character.islower() for character in password):
        return "La nueva contraseña debe incluir al menos una letra minúscula."

    if not any(character.isdigit() for character in password):
        return "La nueva contraseña debe incluir al menos un número."

    if not any(character in string.punctuation for character in password):
        return "La nueva contraseña debe incluir al menos un carácter especial."

    return None
