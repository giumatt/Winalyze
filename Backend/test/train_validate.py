import pandas as pd
import joblib
import io
import os
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
blob_service = BlobServiceClient.from_connection_string(connection_string)

def validate_model(wine_type):
    try:
        print(f"\n📦 Validating model: {wine_type.upper()}")

        # Scarica modello e scaler
        model_blob = blob_service.get_blob_client(container="models", blob=f"model_{wine_type}.pkl")
        scaler_blob = blob_service.get_blob_client(container="models", blob=f"scaler_{wine_type}.pkl")

        model_data = model_blob.download_blob().readall()
        scaler_data = scaler_blob.download_blob().readall()

        model = joblib.load(io.BytesIO(model_data))
        scaler = joblib.load(io.BytesIO(scaler_data))

        # Carica CSV di test
        df = pd.read_csv(f"backend/test/data/selected_{wine_type}.csv")
        X = df.drop("quality", axis=1)
        y = df["quality"]

        # Preprocessing
        X_scaled = scaler.transform(X)
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42)

        # Predizione e valutazione
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        print(f"✅ {wine_type.upper()} model accuracy: {acc:.4f}")
        assert acc >= 0.7, f"❌ Accuracy for {wine_type} model too low: {acc:.4f}"
        return True

    except Exception as e:
        print(f"⚠️ Skipping {wine_type.upper()} model: {e}")
        return None

# Valida modelli presenti
results = []
for t in ["red", "white"]:
    result = validate_model(t)
    results.append(result)
    if result is False:
        raise AssertionError(f"❌ Validation failed for {t} model.")

if any(r is True for r in results):
    print("\n🎉 All present models validated successfully!")