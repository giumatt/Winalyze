import joblib
import io

def save_model(model, scaler):
    buffer = io.BytesIO()
    joblib.dump({"model": model, "scaler": scaler}, buffer)
    buffer.seek(0)
    return buffer

def load_model(blob_data: bytes):
    buffer = io.BytesIO(blob_data)
    model_dict = joblib.load(buffer)
    return model_dict["model"], model_dict["scaler"]