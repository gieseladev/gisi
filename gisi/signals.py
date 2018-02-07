class GisiSignal(BaseException):
    pass


class ShutdownSignal(GisiSignal):
    pass


class RestartSignal(GisiSignal):
    pass
