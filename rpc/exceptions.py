
class NeedMore(BaseException):
    pass

class ParseError(BaseException):
    pass

class Abort(BaseException):
    """
    终止连接
    """

class ResponseThenAbort(BaseException):
    """
    返回信息后终止连接
    """

class Response(BaseException):
    """
    返回信息
    """