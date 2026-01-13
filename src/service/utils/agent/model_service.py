from pydantic_ai.models import Model


class ModelService:
    models: dict[str, Model]

    def __init__(self):
        self.models = {}

    def add_model(self, name: str, model: Model):
        """Adds or updates a model by name."""
        self.models[name] = model

    def get_model(self, name: str) -> Model | None:
        """Retrieves a model by name."""
        return self.models.get(name)
