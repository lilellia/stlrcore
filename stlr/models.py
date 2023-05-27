import stable_whisper
import whisper


class ModelManager:
    def __init__(self):
        self.models: dict[str, whisper.Whisper] = dict()

    def load(self, model_name: str, device: str | None) -> whisper.Whisper:
        if model_name not in self.models:
            model = stable_whisper.load_model(model_name, device=device)
            self.models[model_name] = model

        return self.models[model_name]
