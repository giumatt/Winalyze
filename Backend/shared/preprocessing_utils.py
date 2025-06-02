import pandas as pd
from sklearn.preprocessing import StandardScaler

def preprocess_dataset(path):
    df = pd.read_csv(path)
    df.dropna(inplace=True)

    X = df.drop("quality", axis=1)
    y = df["quality"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    cleaned = pd.concat([pd.DataFrame(X_scaled, columns=X.columns), y.reset_index(drop=True)], axis=1)

    return cleaned, scaler