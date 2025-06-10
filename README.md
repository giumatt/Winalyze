# Winalyze — Wine Quality Prediction Platform

Winalyze is a full-stack platform designed to predict the quality of wine through supervised machine learning models. It enables users to upload custom datasets, train models separately for red and white wine, and perform inference through a modern, responsive interface.

---

## Features

- Upload custom CSV datasets (`;` separated) for red or white wine (included in `/data/raw` folder).
- Automatic preprocessing and model training via Azure Functions.
- Persistent model status tracking and polling system.
- Prediction interface with input validation and real-time feedback.
- Fully containerized frontend and backend using Docker.
- Integration-ready for CI/CD and MLOps pipelines.

---

## Technologies

### Frontend
- Vue 3 + TypeScript
- Vite
- Tailwind-like custom CSS
- Hosted via Azure Static Web Apps or Docker with Nginx

### Backend
- Python (Azure Functions runtime)
- Pandas and Scikit-learn
- Azure Blob Storage for raw, cleaned data and model artifacts
- Modular structure (preprocessing, training, validation, promotion)
- CORS enabled for development

---

## Project Structure

- `/frontend`: Vue-based user interface
- `/backend`: Azure Functions for data handling, model training, validation and inference
- `/shared`: Common Python modules used across backend functions

---

## Testing and Validation

Each model trained is validated through a separate function. If the validation passes, the model is promoted from a staging container (`models-testing`) to the production container (`models`), where it becomes accessible for inference.

---

## Future Work

Possible future directions include full deployment on Azure Container Apps or Docker/Kubernetes, integration of advanced model tuning and selection strategies, visualization of training metrics, and support for user authentication with persistent history of predictions.

---

## License

MIT License © 2025 — [Your Name or Organization]

---

## Contact

For inquiries or contributions, please open an issue or contact [giumatt99@gmail.com].
