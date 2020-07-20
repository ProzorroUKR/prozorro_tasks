from abc import ABC, abstractmethod


class Base(ABC):
    @abstractmethod
    def run(self):
        raise NotImplementedError
