class WarehouseError(Exception):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


class QueryTooExpensive(WarehouseError):
    pass


class QueryFailed(WarehouseError):
    def __init__(self, user_message: str, reason: str):
        super().__init__(user_message)
        self.reason = reason[:500]


class WarehouseUnavailable(WarehouseError):
    pass
