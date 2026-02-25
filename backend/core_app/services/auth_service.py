from core_app.core.security import create_access_token, verify_password
from core_app.repositories.user_repository import UserRepository
from core_app.schemas.auth import LoginRequest, TokenResponse


class InvalidCredentialsError(ValueError):
    pass


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    def login(self, payload: LoginRequest) -> TokenResponse:
        user = self.user_repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password")

        token = create_access_token(str(user.id), str(user.tenant_id), user.role)
        return TokenResponse(access_token=token)
