<template>
  <div id="app" class="main-wrapper" :class="{'red-theme': type === 'red', 'white-theme': type === 'white'}">
    <header class="top-bar">
      <div class="branding" @click="goHome">WINALYZE</div>
      <div class="top-actions">
        <div class="top-button" @click="goHome">Data upload</div>
        <div v-if="modelReady" class="top-button" @click="step = 'predict'">Predict quality</div>
      </div>

    </header>

    <div class="glass-card" v-if="step === 'upload'">
      <h1 class="page-title">Upload a dataset to train the model</h1>
      <div class="upload-controls">
        <div class="file-icon">
          <img src="/assets/file-icon.png" alt="file" />
          <span>{{ file ? file.name : 'No file selected' }}</span>
        </div>
        <div class="radio-group">
          <label><input type="radio" value="red" v-model="type" />Red</label>
          <label><input type="radio" value="white" v-model="type" />White</label>
        </div>
        <div class="action-buttons">
          <button class="btn-dark" @click="triggerFileSelect">
            {{ file ? 'Select new file' : 'Select a file' }}
          </button>
          <button
            class="btn-yellow"
            @click="uploadDataset"
            :disabled="!file || loading"
          >Upload & Train</button>
        </div>
        <input type="file" ref="fileInput" @change="handleFileChange" style="display: none" accept=".csv" />
      </div>
    </div>

    <div v-else-if="step === 'training'" class="training-alert">
      <img src="/assets/warning-icon.png" alt="warning" />
      <span>Model training in progress...</span>
    </div>

    <div v-else-if="step === 'predict'" class="predict-section">
      <form @submit.prevent="handlePredictSubmit" class="glass-card">
        <h2 class="page-title">Predict wine quality</h2>

        <div class="radio-group">
          <label><input type="radio" value="red" v-model="type" />Red</label>
          <label><input type="radio" value="white" v-model="type" />White</label>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <div class="form-grid">
          <div class="form-group" v-for="feature in features" :key="feature">
            <label :for="sanitizeId(feature)">{{ formatLabel(feature) }}</label>
            <input
              type="text"
              :id="sanitizeId(feature)"
              :value="values[feature] ?? ''"
              @input="handleInput(feature, $event)"
              required
            />
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn-yellow" type="submit" :disabled="loading">Predict</button>
        </div>

        <div v-if="prediction !== null" class="prediction-result">
          Predicted quality: <strong>{{ prediction }}</strong>
        </div>
      </form>
    </div>

    <img
      :src="type === 'red' ? '/assets/background-red.png' : '/assets/background-white.png'"
      :key="type"
      alt="background"
      class="bg-illustration"
      :class="{ active: true }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const features = [
  'fixed acidity', 'volatile acidity', 'citric acid', 'residual sugar',
  'chlorides', 'free sulfur dioxide', 'total sulfur dioxide',
  'density', 'pH', 'sulphates', 'alcohol'
]

const step = ref<'upload' | 'training' | 'predict'>('upload')
const file = ref<File | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const modelReady = ref(false)

const type = ref<'red' | 'white'>('red')

onMounted(async () => {
  try {
    const res = await fetch(`https://winalyzefunc.azurewebsites.net/api/model_status?wine_type=${type.value}`)
    if(res.ok) {
      const status = await res.json()
      if (status.status === 'ready') {
        modelReady.value = true
      }
    }
  } catch (e) {
    // Ignore, just don't show the button
  }
})

const values = ref<Record<string, number | undefined>>({})
const prediction = ref<number | null>(null)

const fileInput = ref<HTMLInputElement | null>(null)

function goHome() {
  error.value = null
  prediction.value = null
  values.value = {}
  file.value = null
  step.value = 'upload'
  loading.value = false
}

function sanitizeId(feature: string): string {
  return feature.replace(/\s/g, '-');
}

function triggerFileSelect() {
  if (fileInput.value) {
    fileInput.value.click();
  }
}
function handleInput(feature: string, event: Event) {
  const input = (event.target as HTMLInputElement).value
  const normalized = input.replace(',', '.')
  const number = parseFloat(normalized)
  values.value[feature] = isNaN(number) ? undefined : number
}

function formatLabel(label: string) {
  return label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    file.value = target.files[0]
    error.value = null
  }
}

async function uploadDataset() {
  if (!file.value) {
    error.value = "Select a file before uploading"
    return
  }
  loading.value = true
  error.value = null
  try {
    const formData = new FormData()
    formData.append('file', file.value)

    const res = await fetch(`https://winalyzefunc.azurewebsites.net/api/upload_function?wine_type=${type.value}`, {
      method: 'POST',
      body: formData
    })
    if (!res.ok) throw new Error('Error while uploading file')

    // Passa alla fase training e richiama trainModel
    step.value = 'training'
    await trainModel()
  } catch (e: any) {
    error.value = e.message || 'Error while uploading file'
    step.value = 'upload'
  } finally {
    loading.value = false
  }
}

async function trainModel() {
  try {
    let attempts = 0
    const maxAttempts = 30  // Aumentato il numero di tentativi
    const pollInterval = 3000  // Aumentato l'intervallo a 3 secondi
    const endpoint = `https://winalyzefunc.azurewebsites.net/api/model_status?wine_type=${type.value}`

    console.log(`Starting polling for ${type.value} wine model...`)

    return new Promise<void>((resolve, reject) => {
      const interval = setInterval(async () => {
        attempts++
        console.log(`Polling attempt ${attempts}/${maxAttempts} for ${type.value} model`)
        
        try {
          const statusRes = await fetch(endpoint, { method: 'GET' })
          console.log(`📡 Response status: ${statusRes.status}`)
          
          if (!statusRes.ok) {
            console.error(`HTTP error: ${statusRes.status} ${statusRes.statusText}`)
            const errorText = await statusRes.text()
            console.error(`Error response: ${errorText}`)
            throw new Error(`HTTP ${statusRes.status}: ${statusRes.statusText}`)
          }

          const status = await statusRes.json()
          console.log(`📋 Status response:`, status)
          
          // Gestisci entrambi i formati di risposta per retrocompatibilità
          const modelStatus = status.status || status[type.value]
          console.log(`Model status: ${modelStatus}`)
          
          if (modelStatus === 'ready') {
            console.log(`✅ Model ${type.value} is ready!`)
            clearInterval(interval)
            modelReady.value = true
            step.value = 'predict'
            resolve()
          } else if (attempts >= maxAttempts) {
            console.error(`Timeout: training took too long (${attempts} attempts)`)
            clearInterval(interval)
            error.value = "Timeout: training took too much time"
            step.value = 'upload'
            reject(new Error("Timeout: training took too much time"))
          } else {
            console.log(`Model still training... (attempt ${attempts}/${maxAttempts})`)
          }
        } catch (err: any) {
          console.error(`Error during polling attempt ${attempts}:`, err)
          clearInterval(interval)
          error.value = err.message || 'Error while checking model status'
          step.value = 'upload'
          reject(err)
        }
      }, pollInterval)
      
      // Timeout di sicurezza
      setTimeout(() => {
        clearInterval(interval)
        error.value = "Training timeout exceeded"
        step.value = 'upload'
        reject(new Error("Training timeout exceeded"))
      }, maxAttempts * pollInterval + 10000) // 10 secondi extra di buffer
    })
  } catch (e: any) {
    console.error(`Error in trainModel:`, e)
    error.value = e.message || 'Error while training model'
    step.value = 'upload'
  }
}

async function handlePredictSubmit() {
  error.value = null
  prediction.value = null
  loading.value = true
  try {
    const cleanedValues: Record<string, number> = {}
    for(const key in values.value) {
      const val = values.value[key]
      if (typeof val === 'number' && !isNaN(val)) {
        cleanedValues[key] = val
      } else {
        throw new Error(`Missing or invalid input for '${key}'`)
      }
    }

    const response = await fetch('https://winalyzefunc.azurewebsites.net/api/infer_function', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ type: type.value, input: cleanedValues })
    })
    const data = await response.json()
    if(!response.ok) throw new Error(data.detail || 'API error')

    prediction.value = data.predicted_quality
  } catch (err: any) {
    error.value = err.message || 'Unexpected error'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

* {
  box-sizing: border-box;
}

html, body, #app, .glass-card, .form-group input {
  transition: all 0.8s ease; /* Aumentata la durata da 0.5s a 0.8s */
}

body, html, #app {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100vh;
  font-family: 'Poppins', sans-serif;
  background-size: cover;
  background-position: center;
  color: white;
  font-size: 16px; /* Aumentato il font base */
}

.main-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center; /* Assicura il centramento verticale */
  text-align: center;
  position: relative;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
  min-height: 100vh; /* Cambiato da height a min-height */
  padding: 2rem; /* Aggiunto padding per evitare che il contenuto tocchi i bordi */
}

.top-bar {
  position: fixed;
  top: 2rem;
  left: 50%;
  transform: translateX(-50%);
  width: 95%;  /* Aumentato da 80% a 95% */
  max-width: 1200px;  /* Aumentato da 600px a 1200px */
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.branding {
  font-size: 1.4rem; /* Aggiunto font-size */
  font-weight: bold;
  cursor: pointer;
  padding: 0.5rem;
}

.section-title {
  font-size: 1.4rem; /* Aggiunto font-size */
  opacity: 0.8;
  cursor: pointer;
  padding: 0.5rem;
}

.glass-card {
  background: rgba(255, 255, 255, 0.2);
  margin: 0 auto;
  border-radius: 1rem;
  padding: 2rem; /* Ridotto da 2.5rem a 2rem */
  backdrop-filter: blur(15px);
  width: 700px; /* Aumentato per accomodare le due colonne */
  display: flex;
  flex-direction: column;
  gap: 1rem; /* Ridotto da 1.5rem a 1rem */
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  position: absolute; /* Aggiunto position absolute */
  top: 50%; /* Posiziona al centro verticalmente */
  left: 50%; /* Posiziona al centro orizzontalmente */
  transform: translate(-50%, -50%); /* Centra perfettamente */
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.page-title {
  font-size: 2.2rem; /* Aumentato da 1.8rem */
  font-weight: bold;
  margin-bottom: 1rem; /* Ridotto da 1.5rem a 1rem */
}

.upload-controls {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.file-icon img {
  width: 28px;
  height: 28px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem 2rem; /* Ridotto il gap verticale da 1.25rem a 0.75rem */
  width: 100%;
  margin: 0.5rem 0; /* Ridotto il margine da 1rem a 0.5rem */
  text-align: left;
}

.form-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 0; /* Rimosso il margin-bottom */
}

.form-group label {
  font-weight: 500;
  margin-bottom: 0.25rem; /* Ridotto da 0.5rem a 0.25rem */
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.9);
}

.form-group input {
  padding: 0.5rem 1rem; /* Ridotto il padding verticale da 0.75rem a 0.5rem */
  border: 1.5px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  font-size: 1.1rem;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.radio-group {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.radio-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.radio-group input[type="radio"] {
  accent-color: #d4af37;
  width: 18px;
  height: 18px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.btn-yellow {
  background: #ffdd57;
  color: black;
}

.btn-dark {
  background: #3c3c55;
  color: white;
}

.btn-dark, .btn-yellow {
  padding: 0.9rem 2rem; /* Aumentato padding */
  border-radius: 999px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 1.1rem; /* Aggiunto font-size */
}

.btn-predict {
  background: #ffdd57;
  color: black;
  border: none;
  border-radius: 999px;
  padding: 0.5rem 1.25rem;
  margin-left: 1rem;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
}

.training-alert {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  padding: 1.5rem 3rem;  /* Aumentato padding */
  background: #3c3c55;
  border-radius: 1rem;
  color: #ffdd57;
  font-weight: 600;
  display: flex;
  gap: 1rem;  /* Aumentato gap */
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  min-width: 400px;  /* Aumentato min-width */
  justify-content: center;
  font-size: 1.2rem;  /* Aumentato font-size */
}

.training-alert img {
  width: 24px;  /* Aumentato dimensione icona */
  height: 24px;  /* Aumentato dimensione icona */
}

.prediction-result {
  margin-top: 1.5rem;
  font-weight: 700;
  font-size: 1.4rem; /* Aumentato da 1.2rem */
  text-align: center;
}

.bg-illustration {
  position: fixed;
  bottom: 0;
  left: 0%;
  width: 100%;
  height: 100%;
  z-index: -1;
  object-fit: cover;
  opacity: 0; /* Inizia con opacità 0 */
  transition: opacity 1s ease-in-out; /* Transizione più lunga per l'immagine */
}

.bg-illustration.active {
  opacity: 1;
}

input[type='file'] {
  display: none;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.top-button {
  font-size: 1.4rem;
  font-weight: 500;
  cursor: pointer;
  padding: 0.5rem 1rem;
  color: white;
  background-color: transparent;
  border-radius: 8px;
  transition: background-color 0.3s ease;
}

.top-button:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.white-theme {
  color: #333;
  background: linear-gradient(to right, #fefcea, #f1da36);
  transition: background 0.5s ease, color 0.5s ease;
}

.white-theme .top-button,
.white-theme .form-group label,
.white-theme .radio-group label,
.white-theme .prediction-result {
  color: #333;
}

.white-theme .btn-dark {
  color: #ffffff;
  background-color: #3c3c55;
}

.white-theme .btn-yellow {
  color: #000000;
  background-color: #ffdd57;
}

.white-theme input,
.white-theme .glass-card {
  color: #333;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(15px);
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.white-theme .top-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: black;
}

.white-theme .branding {
  color: #333;
}

.white-theme .branding:hover {
  color: #444
}

.white-theme .training-alert {
  background: #ffffff;
  color: #333;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.white-theme .glass-card {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(15px);
  color: #222;
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.white-theme .form-group input {
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(8px);
  border: 1.5px solid rgba(0, 0, 0, 0.2);
  color: #000;
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.branding:hover {
  opacity: 0.85;
}

.red-theme {
  color: white;
  background: linear-gradient(to right, #f8e1e7, #e7b1b8);
  transition: background 0.5s ease, color 0.5s ease;
}

.red-theme .top-button,
.red-theme .form-group label,
.red-theme .radio-group label,
.red-theme .prediction-result {
  color: white;
}

.red-theme .btn-dark {
  color: white;
  background-color: #3c3c55;
}

.red-theme .btn-yellow {
  color: black;
  background-color: #ffdd57;
}

.red-theme input,
.red-theme .glass-card {
  color: white;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.red-theme .form-group input {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(8px);
  border: 1.5px solid rgba(255, 255, 255, 0.2);
  color: white;
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #ffdd57;
  box-shadow: 0 0 0 2px rgba(255, 221, 87, 0.3);
}

.btn-yellow:hover {
  background-color: #ffe877;
}

.btn-dark:hover {
  background-color: #505070;
}

.radio-group input[type="radio"] {
  transition: accent-color 0.3s ease;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  margin-top: 1rem;
  color: #ff6b6b;
  font-weight: 500;
  text-align: center;
}

@media (max-width: 768px) {
  .glass-card {
    width: 90%;
    padding: 1.5rem;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .top-bar {
    flex-direction: column;
    gap: 1rem;
  }

  .action-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>