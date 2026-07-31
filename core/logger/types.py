import abc


class Logger(abc.ABC):
    @abc.abstractmethod
    def log(self, session_id, msg):
        pass
