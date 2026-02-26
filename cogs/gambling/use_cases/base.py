from database.repository import UserRepository

class BaseGamblingUseCase:
    def __init__(self, repository: UserRepository = None):
        self.repo = repository or UserRepository()
