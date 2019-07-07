class ValidationError(Exception):
    pass


class RuntimeError(Exception):
    def __init__(self, message, node):
        super().__init__(message)
        self.location = node.loc.source.get_location(node.loc.start)
