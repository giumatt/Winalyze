from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
import joblib
import numpy as np
import pandas as pd
import os
from dotenv import load_dotenv
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"]
)

# Paths 
DATA_DIR = os.getenv("DATA_DIR", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
CLEANED_DIR = os.path.join(DATA_DIR, "cleaned")
SCALERS_DIR = os.path.join(DATA_DIR, "scalers")
MODELS_DIR = os.path.join(DATA_DIR, "models")

# Folders check
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEANED_DIR, exist_ok=True)
os.makedirs(SCALERS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURES = [
    "fixed acidity", "volatile acidity", "citric acid", "residual sugar",
    "chlorides", "free sulfur dioxide", "total sulfur dioxide",
    "density", "pH", "sulphates", "alcohol"
]


class WineFeatures(BaseModel):
    fixed_acidity: float = Field(..., alias="fixed acidity")
    volatile_acidity: float = Field(..., alias="volatile acidity")
    citric_acid: float = Field(..., alias="citric acid")
    residual_sugar: float = Field(..., alias="residual sugar")
    chlorides: float
    free_sulfur_dioxide: float = Field(..., alias="free sulfur dioxide")
    total_sulfur_dioxide: float = Field(..., alias="total sulfur dioxide")
    density: float
    pH: float
    sulphates: float
    alcohol: float
class WineInput(BaseModel):
    type: Literal["red", "white"]
    input: dict

# Dataset upload entrypoint
@app.post("/upload-dataset")
async def upload_dataset(file: UploadFile = File(...), wine_type: Literal["red", "white"] = "red"):
    filename = f"{wine_type}_uploaded.csv"
    filepath = os.path.join(RAW_DIR, filename)
    try:
        contents = await file.read()
        with open(filepath, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    return {"message": f"File uploaded successfully as {filename}"}

# Background task for training
def preprocess_and_train(wine_type: str):
    raw_path = os.path.join(RAW_DIR, f"{wine_type}_uploaded.csv")
    cleaned_path = os.path.join(CLEANED_DIR, f"cleaned_{wine_type}.csv")
    scaler_path = os.path.join(SCALERS_DIR, f"scaler_{wine_type}.pkl")
    model_path = os.path.join(MODELS_DIR, f"model_{wine_type}.pkl")

    df = pd.read_csv(raw_path, sep=";")

    if df.isnull().values.any():
        print("[!] Warning: Dataset contains NULL values. Dropping them")
        df = df.dropna()

    X = df[FEATURES]
    y = df["quality"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    joblib.dump(scaler, scaler_path)

    df_cleaned = pd.DataFrame(X_scaled, columns=FEATURES)
    df_cleaned["quality"] = y.values
    df_cleaned.to_csv(cleaned_path, index=False)

    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight='balanced'
    )

    model.fit(X_scaled, y)

    joblib.dump(model, model_path)

# Train endpoint
@app.post("/train-model")
async def train_model(wine_type: Literal["red", "white"], background_tasks: BackgroundTasks):
    raw_path = os.path.join(RAW_DIR, f"{wine_type}_uploaded.csv")
    if not os.path.exists(raw_path):
        raise HTTPException(status_code=404, detail="Dataset not found. Upload it first.")
    background_tasks.add_task(preprocess_and_train, wine_type)
    return {"message": "Preprocess and train started in background"}

# Model status endpoint
@app.get("/model-status")
def model_status(wine_type: Literal["red", "white"] = Query(...)):
    try:
        cleaned_path = os.path.join(CLEANED_DIR, f"cleaned_{wine_type}.csv")
        model_path = os.path.join(MODELS_DIR, f"model_{wine_type}.pkl")
        scaler_path = os.path.join(SCALERS_DIR, f"scaler_{wine_type}.pkl")

        cleaned_exists = os.path.exists(cleaned_path)
        model_exists = os.path.exists(model_path)
        scaler_exists = os.path.exists(scaler_path)

        if cleaned_exists and model_exists and scaler_exists:
            return {"status": "ready"}
        else:
            return {"status": "training"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.post("/predict")
def predict(data: WineInput):
    wine_type = data.type.lower()
    if wine_type not in ['white', 'red']:
        raise HTTPException(status_code=400, detail="Invalid wine type. Must be 'white' or 'red'.")
    
    # Check input keys
    missing = [feat for feat in FEATURES if feat not in data.input]
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing features: {missing}")
    
    try:
        # Load model and scaler
        model_path = os.path.join(MODELS_DIR, f"model_{wine_type}.pkl")
        scaler_path = os.path.join(SCALERS_DIR, f"scaler_{wine_type}.pkl")

        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)

        # Extract and scale input
        input_values = [data.input[feat] for feat in FEATURES]
        input_df = pd.DataFrame([input_values], columns=FEATURES)
        input_scaled = scaler.transform(input_df)

        prediction = model.predict(input_scaled)
        return {"predicted_quality": int(prediction[0])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")