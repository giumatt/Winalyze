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
      <div class="training-info">
        <div class="training-title">Model training in progress...</div>
      </div>
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

// Nuove variabili per il tracking del training
const trainingAttempts = ref(0)
const maxTrainingAttempts = ref(120)
const trainingStartTime = ref<number | null>(null)

// Funzioni per la persistenza dello stato
function saveTrainingState() {
  const state = {
    isTraining: step.value === 'training',
    wineType: type.value,
    startTime: Date.now()
  }
  localStorage.setItem('winalyze_training_state', JSON.stringify(state))
}

function loadTrainingState() {
  const saved = localStorage.getItem('winalyze_training_state')
  if (!saved) return null
  
  try {
    const state = JSON.parse(saved)
    // Se è passata più di 1 ora, considera il training fallito
    if (Date.now() - state.startTime > 60 * 60 * 1000) {
      localStorage.removeItem('winalyze_training_state')
      return null
    }
    return state
  } catch {
    localStorage.removeItem('winalyze_training_state')
    return null
  }
}

function clearTrainingState() {
  localStorage.removeItem('winalyze_training_state')
}

// Funzione per formattare il tempo trascorso
function formatTrainingTime(startTime: number | null): string {
  if (!startTime) return '0s'
  const elapsed = Math.floor((Date.now() - startTime) / 1000)
  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  return `${minutes}m ${seconds}s`
}

onMounted(async () => {
  // Controlla se c'era un training in corso
  const trainingState = loadTrainingState()
  if (trainingState && trainingState.isTraining) {
    type.value = trainingState.wineType
    step.value = 'training'
    // Riprendi il polling
    try {
      await trainModel()
      clearTrainingState()
    } catch (e) {
      clearTrainingState()
    }
  } else {
    // Controllo normale dello stato del modello
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
  // Pulisci anche lo stato del training quando vai in home
  clearTrainingState()
  trainingStartTime.value = null
  trainingAttempts.value = 0
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

    // Salva lo stato prima di iniziare il training
    step.value = 'training'
    saveTrainingState()
    
    await trainModel()
    clearTrainingState() // Pulisci lo stato quando finisce con successo
  } catch (e: any) {
    clearTrainingState() // Pulisci lo stato in caso di errore
    error.value = e.message || 'Error while uploading file'
    step.value = 'upload'
  } finally {
    loading.value = false
  }
}

async function trainModel() {
  trainingStartTime.value = Date.now()
  trainingAttempts.value = 0
  
  try {
    let attempts = 0
    const maxAttempts = 120  // 10 minuti totali
    const pollInterval = 5000  // 5 secondi
    const endpoint = `https://winalyzefunc.azurewebsites.net/api/model_status?wine_type=${type.value}`

    console.log(`Starting polling for ${type.value} wine model...`)

    return new Promise<void>((resolve, reject) => {
      const interval = setInterval(async () => {
        attempts++
        trainingAttempts.value = attempts // Aggiorna il contatore reattivo
        
        console.log(`Polling attempt ${attempts}/${maxAttempts} for ${type.value} model`)
        
        try {
          const statusRes = await fetch(endpoint, { 
            method: 'GET',
            // Timeout per singole richieste per evitare richieste bloccate
            signal: AbortSignal.timeout(10000) // 10 secondi timeout per richiesta
          })
          
          console.log(`📡 Response status: ${statusRes.status}`)
          
          if (!statusRes.ok) {
            console.warn(`HTTP error: ${statusRes.status} ${statusRes.statusText}`)
            // Non interrompere per errori HTTP temporanei, continua il polling
            if (attempts >= maxAttempts) {
              clearInterval(interval)
              error.value = `Training timeout: max attempts reached (${maxAttempts})`
              step.value = 'upload'
              trainingStartTime.value = null
              reject(new Error(`Training timeout: max attempts reached`))
            }
            return // Continua il polling
          }

          const status = await statusRes.json()
          console.log(`📋 Status response:`, status)
          
          const modelStatus = status.status || status[type.value]
          console.log(`Model status: ${modelStatus}`)
          
          if (modelStatus === 'ready') {
            console.log(`✅ Model ${type.value} is ready!`)
            clearInterval(interval)
            modelReady.value = true
            step.value = 'predict'
            trainingStartTime.value = null // Reset del timer
            resolve() // Il polling si ferma qui definitivamente
          } else if (attempts >= maxAttempts) {
            console.error(`Timeout: training took too long (${attempts} attempts)`)
            clearInterval(interval)
            error.value = `Training timeout: exceeded ${maxAttempts} attempts (${(maxAttempts * pollInterval) / 60000} minutes)`
            step.value = 'upload'
            trainingStartTime.value = null
            reject(new Error("Training timeout exceeded"))
          } else {
            console.log(`Model still training... (attempt ${attempts}/${maxAttempts})`)
          }
        } catch (err: any) {
          console.warn(`Error during polling attempt ${attempts}:`, err.message)
          
          // Se è un errore di rete/timeout, continua il polling invece di fermarsi
          if (err.name === 'AbortError' || err.name === 'TimeoutError' || err.message.includes('fetch')) {
            console.log('Network error, continuing polling...')
            if (attempts >= maxAttempts) {
              clearInterval(interval)
              error.value = 'Training timeout: network issues prevented status check'
              step.value = 'upload'
              trainingStartTime.value = null
              reject(new Error('Training timeout: network issues'))
            }
            return // Continua il polling
          }
          
          // Solo per errori critici, ferma il polling
          console.error(`Critical error during polling:`, err)
          clearInterval(interval)
          error.value = err.message || 'Error while checking model status'
          step.value = 'upload'
          trainingStartTime.value = null
          reject(err)
        }
      }, pollInterval)
    })
  } catch (e: any) {
    console.error(`Error in trainModel:`, e)
    error.value = e.message || 'Error while training model'
    step.value = 'upload'
    trainingStartTime.value = null
    throw e
  }
}

async function handlePredictSubmit() {
  error.value = null
  prediction.value = null
  loading.value = true
  try {
    const cleanedValues: Record<string, number> = {}

    // Verifica che tutte le features richieste siano presenti
    for (const feature of features) {
      const val = values.value[feature];
      if (val === undefined || typeof val !== 'number' || isNaN(val)) {
        throw new Error(`Missing or invalid input for '${feature}'`);
      }
      cleanedValues[feature] = val;
    }

    // FIX: Invia i dati nel formato corretto
    const requestData = {
      type: type.value,
      ...cleanedValues  // Spread delle features direttamente nel corpo della richiesta
    }

    const response = await fetch('https://winalyzefunc.azurewebsites.net/api/infer_function', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(requestData)  // Ora i dati sono nel formato corretto
    })
    
    const data = await response.json();
    if(!response.ok) throw new Error(data.detail || 'API error')

    prediction.value = data.prediction

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
  transition: all 0.8s ease;
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
  font-size: 16px;
}

.main-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  position: relative;
  max-width: 800px;
  margin: 0 auto;
  width: 100%;
  min-height: 100vh;
  padding: 2rem;
}

.top-bar {
  position: fixed;
  top: 2rem;
  left: 2rem;
  right: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 10;
}

.branding {
  font-size: 1.4rem;
  font-weight: bold;
  cursor: pointer;
  padding: 0.5rem;
}

.section-title {
  font-size: 1.4rem;
  opacity: 0.8;
  cursor: pointer;
  padding: 0.5rem;
}

.glass-card {
  background: rgba(255, 255, 255, 0.2);
  margin: 0 auto;
  border-radius: 1rem;
  padding: 2rem;
  backdrop-filter: blur(15px);
  width: 700px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  transition: background 0.5s ease, color 0.5s ease, backdrop-filter 0.5s ease;
}

.predict-section .glass-card {
  top: 120px;
  bottom: 40px;
  height: auto;
  transform: translateX(-50%);
  overflow-y: auto;
  padding: 1.5rem 2rem;
}

.page-title {
  font-size: 2.2rem;
  font-weight: bold;
  margin-bottom: 1rem;
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
  gap: 0.75rem 2rem;
  width: 100%;
  margin: 0.5rem 0;
  text-align: left;
}

.form-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 0;
}

.form-group label {
  font-weight: 500;
  margin-bottom: 0.25rem;
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.9);
}

.form-group input {
  padding: 0.5rem 1rem;
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
  padding: 0.9rem 2rem;
  border-radius: 999px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 1.1rem;
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
  padding: 2rem 3rem;
  background: #3c3c55;
  border-radius: 1rem;
  color: #ffdd57;
  font-weight: 600;
  display: flex;
  gap: 1.5rem;
  align-items: center;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  min-width: 500px;
  justify-content: center;
  font-size: 1.2rem;
}

.training-alert img {
  width: 24px;
  height: 24px;
}

.training-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.training-title {
  font-size: 1.2rem;
  font-weight: 600;
}

.training-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.9rem;
  opacity: 0.8;
}

.training-time {
  font-family: monospace;
  color: #ffdd57;
}

.prediction-result {
  margin-top: 1.5rem;
  font-weight: 700;
  font-size: 1.4rem;
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
  opacity: 0;
  transition: opacity 1s ease-in-out;
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

.white-theme .training-time {
  color: #d4af37;
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
  
  .top-bar {
    left: 1rem;
    right: 1rem;
    flex-direction: row;
    gap: 0;
  }
  
  .top-button {
    font-size: 1.2rem;
    padding: 0.5rem;
  }
  
  .branding {
    font-size: 1.2rem;
  }
  
  .predict-section .glass-card {
    top: 100px;
    bottom: 20px;
    width: 90%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
    gap: 0.75rem;
  }

  .training-alert {
    min-width: 90%;
    padding: 1.5rem 2rem;
  }
}
</style>