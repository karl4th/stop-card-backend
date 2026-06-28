class FieldValidationError(ValueError):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("validation error")
        self.fields = fields
