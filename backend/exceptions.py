# exceptions.py - Custom exceptions for the Agent OS Platform
# This file is reserved for custom exception classes.


class NotFoundError(ValueError):
    """Exception raised when an entity is not found in the database."""

    def __init__(self, entity_name: str, id_: str):
        message = f"{entity_name} not found: {id_}"
        super().__init__(message)


class UnsetVariableError(ValueError):
    """Exception raised when a required variable is unset or not defined."""

    def __init__(self, key: str):
        message = f"Variable {key} is not set. Please set it first."
        super().__init__(message)


class HandledValidationError(ValueError):
    """A base class for all custom validation errors that we handle in the dedicated exception handler."""

    message = "A validation error occurred"

    def __init__(self):
        super().__init__(self.message)


class ValidationErrorEmptyFlows(HandledValidationError):
    """Exception raised when the flows list is empty."""

    message = "Please add at least one agent"


class ValidationErrorSameSenderReceiver(HandledValidationError):
    """Exception raised when the same agent is set as both sender and receiver."""

    message = "Cannot set the same agent as both sender and receiver"


class ValidationErrorMissingSender(HandledValidationError):
    """Exception raised when the sender agent is not set."""

    message = "Sender agent is required"


class ValidationErrorMissingReceiver(HandledValidationError):
    """Exception raised when the receiver agent is not set."""

    message = "Receiver agent is required"
