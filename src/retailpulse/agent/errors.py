"""Safe errors expose stable categories, never SQL, paths or provider payloads."""


class AgentError(Exception):
    def __init__(self, category, message, status="clarification"):
        super().__init__(message)
        self.category, self.status = category, status
