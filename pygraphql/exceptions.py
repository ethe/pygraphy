class GraphQLError(Exception):
    def __init__(self, message, location):
        super(GraphQLError, self).__init__(message)
        self.location = location
