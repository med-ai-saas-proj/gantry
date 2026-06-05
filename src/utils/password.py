import bcrypt


class PasswordUtils:
    @classmethod
    def hash_password(cls, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode()

    @classmethod
    def verify_password(cls, password: str, hashed_password) -> bool:
        if isinstance(hashed_password, memoryview):
            hashed_password = bytes(hashed_password)
        elif isinstance(hashed_password, str):
            hashed_password = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password)