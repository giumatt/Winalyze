import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

# Test upload_function to ensure correct file upload and response
@pytest.mark.asyncio
async def test_upload_function(monkeypatch):
    from functions.upload_function import __init__ as upload_func

    class DummyReq:
        def __init__(self):
            self.method = "POST"
            self.files = {}
            self.params = {"wine_type": "red"}
        async def form(self):
            return {"file": DummyUploadFile()}

    class DummyUploadFile:
        filename = "test.csv"
        async def read(self):
            return b"test,data"

    # Mock dependencies used by the target function
    mock_blob_client = AsyncMock()
    mock_container = MagicMock()
    mock_container.get_blob_client.return_value = mock_blob_client
    mock_blob_service = MagicMock()
    mock_blob_service.get_container_client.return_value = mock_container

    monkeypatch.setattr("functions.upload_function.__init__.BlobServiceClient.from_connection_string",
                        lambda _: mock_blob_service)
    monkeypatch.setattr("functions.upload_function.__init__.func.HttpRequest", DummyReq)

    req = DummyReq()
    res = await upload_func.main(req)

    print("Upload function returned status code:", res.status_code)
    assert res.status_code == 200 or res.status_code == 201


# Test train_function to ensure training pipeline executes without errors
@pytest.mark.asyncio
async def test_train_function(monkeypatch):
    from functions.train_function import __init__ as train_func

    # Mock dependencies used by the target function
    mock_blob_client = AsyncMock()
    mock_blob_client.exists.return_value = True
    mock_blob_client.download_blob.return_value.readall.return_value = pd.DataFrame({
        "fixed acidity": [7.0],
        "volatile acidity": [0.27],
        "citric acid": [0.36],
        "residual sugar": [20.7],
        "chlorides": [0.045],
        "free sulfur dioxide": [45.0],
        "total sulfur dioxide": [170.0],
        "density": [1.001],
        "pH": [3.0],
        "sulphates": [0.45],
        "alcohol": [8.8],
        "quality": [6]
    }).to_csv(index=False).encode()

    mock_blob_client.upload_blob = AsyncMock()
    mock_container = MagicMock()
    mock_container.get_blob_client.return_value = mock_blob_client
    mock_container.list_blobs = AsyncMock(return_value=[])
    mock_blob_service = MagicMock()
    mock_blob_service.get_container_client.return_value = mock_container

    monkeypatch.setattr("functions.train_function.__init__.BlobServiceClient.from_connection_string",
                        AsyncMock(return_value=mock_blob_service))
    monkeypatch.setattr("functions.train_function.__init__.validate_model", AsyncMock(return_value=True))
    monkeypatch.setattr("functions.train_function.__init__.preprocess_data",
                        lambda df, wt: (df, b'scaler'))
    monkeypatch.setattr("functions.train_function.__init__.train_model",
                        lambda df, wt: b'model')

    class DummyTimer: pass
    await train_func.main(DummyTimer(), cleanedOutput=None)
    print("Train function executed successfully")


# Test validate_function to simulate model validation and promotion
@pytest.mark.asyncio
async def test_validate_function(monkeypatch):
    from functions.validate_function import __init__ as validate_func

    # Mock dependencies used by the target function
    mock_blob_service = MagicMock()
    mock_container = MagicMock()
    mock_container.list_blobs = AsyncMock(return_value=[
        MagicMock(name="model_red.pkl"), MagicMock(name="model_white.pkl")
    ])
    mock_blob_service.get_container_client.return_value = mock_container
    monkeypatch.setattr("functions.validate_function.__init__.BlobServiceClient.from_connection_string",
                        lambda _: mock_blob_service)
    monkeypatch.setattr("functions.validate_function.__init__.validate_model",
                        lambda wt, svc: True)
    monkeypatch.setattr("functions.validate_function.__init__.trigger_merge_to_alpha",
                        lambda: None)

    class DummyStream:
        name = "model_white-testing.pkl"
    await validate_func.main(DummyStream())
    print("Validate function executed successfully")


# Test infer_function to verify prediction endpoint behavior
@pytest.mark.asyncio
async def test_infer_function(monkeypatch):
    from functions.infer_function import __init__ as infer_func

    dummy_input = pd.DataFrame({
        "fixed acidity": [7.0],
        "volatile acidity": [0.27],
        "citric acid": [0.36],
        "residual sugar": [20.7],
        "chlorides": [0.045],
        "free sulfur dioxide": [45.0],
        "total sulfur dioxide": [170.0],
        "density": [1.001],
        "pH": [3.0],
        "sulphates": [0.45],
        "alcohol": [8.8],
    })

    req_body = dummy_input.to_json(orient="records")
    mock_req = MagicMock()
    mock_req.get_body.return_value = req_body.encode()
    mock_req.params = {"wine_type": "red"}

    # Mock dependencies used by the target function
    monkeypatch.setattr("functions.infer_function.__init__.load_model_and_scaler",
                        lambda wt: ("model", "scaler"))
    monkeypatch.setattr("functions.infer_function.__init__.preprocess_for_inference",
                        lambda df, sc: df)

    res = await infer_func.main(mock_req)
    print("Infer function returned status code:", res.status_code)
    assert res.status_code == 200