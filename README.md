# 🎬 OpenShorts

**Turn Long Videos into Viral Shorts in Seconds.**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React-61DAFB)](https://react.dev/)
[![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash-8E44AD)](https://deepmind.google/technologies/gemini/)
[![FFmpeg](https://img.shields.io/badge/Powered%20by-FFmpeg-007808)](https://ffmpeg.org/)

OpenShorts is an AI-powered pipeline that automatically repurposes long-form video content (from YouTube or local files) into engaging, vertical short-form videos ready for TikTok, Instagram Reels, and YouTube Shorts.

It uses advanced computer vision to track speakers and keeps them perfectly framed, while leveraging **Google's Gemini 2.5 Flash** to identify the most viral-worthy moments and generate captions.

---

## ✨ Features

- **🧠 AI-Powered Content Analysis**: Uses **Gemini 2.5 Flash** to analyze video transcripts and identify the most engaging, viral segments.
- **🎥 Intelligent Vertical Cropping**: Automatically detects faces and tracks the active speaker to create professional 9:16 vertical cuts.
- **🗣️ Active Speaker Detection**: Distinguishes between multiple people in a frame and cuts to whoever is talking.
- **📜 Automatic Transcription**: Integrates with **Faster-Whisper** for local transcription or fetches **YouTube Captions** directly.
- **🎨 Style Presets**: Choose content styles (e.g., educational, funny, motivational) via prompt engineering.
- **💾 Google Drive Integration**: Seamlessly syncs generated clips to your Google Drive (perfect for Colab users).
- **🚀 Modern Web Dashboard**: A clean, responsive **React** interface to manage uploads, view analysis, and generate clips.
- **⚡ Dual-Mode Processing**: 
    - **Analyze First**: Review potential clips before rendering.
    - **One-Click Magic**: Go from URL to final video in one go.

---

## 🛠️ Prerequisites

To run OpenShorts locally, you'll need:

- **Python 3.8+**
- **Node.js v20+** (for the dashboard)
- **FFmpeg** installed and added to your system PATH.
- A **Google Gemini API Key** (Get one [here](https://aistudio.google.com/)).

---

## 🚀 Installation & Usage

### 💻 Local Machineo

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/mr-mk47/openshorts.git
    cd openshorts
    ```

2.  **Set Up Environment Variables**
    Create a `.env` file in the root directory:
    ```bash
    cp .env.example .env  # If not available, create one manually
    ```
    Add your API key:
    ```env
    GEMINI_API_KEY=your_actual_api_key_here
    MAX_CONCURRENT_JOBS=2
    ```

3.  **Install Backend Dependencies**
    It's recommended to use a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Install Frontend Dependencies**
    ```bash
    cd dashboard
    npm install
    cd ..
    ```

5.  **Run the Application**
    You need to run both the backend (API) and frontend (UI).

    **Terminal 1 (Backend):**
    ```bash
    uvicorn app:app --reload --host 0.0.0.0 --port 8000
    ```

    **Terminal 2 (Frontend):**
    ```bash
    cd dashboard
    npm run dev
    ```

    Open your browser and navigate to `http://localhost:5173`.

---

### ☁️ Google Colab (Cloud)

OpenShorts is optimized for Google Colab, allowing you to use free GPU resources for faster processing.

1.  Open a new Notebook in Google Colab.
2.  **Clone the Repo**:
    ```python
    !git clone https://github.com/mr-mk47/openshorts.git
    %cd openshorts
    ```
3.  **Set your API Key**:
    - Go to the **Secrets** (key icon) in the left sidebar.
    - Add a new secret named `Gemini` with your API key value.
    - Toggle "Notebook access" to ON.

4.  **Run the Setup Script**:
    The included `colab.py` script handles everything (deps, tunnel, servers).
    ```python
    !python colab.py
    ```

5.  **Access the UI**:
    - The script will output a **Tunnel Password** (an IP address) and a **Green URL**.
    - Click the URL.
    - Enter the Tunnel Password when prompted.
    - You're in! Generated clips will automatically save to your Google Drive under `Context/Drive/MyDrive/CLIPS`.

---

## 📂 Project Structure

```
openshorts/
├── app.py              # FastAPI Backend & Job Manager
├── main.py             # Core Video Processing Pipeline
├── colab.py            # Colab Automation Script
├── prompts.py          # AI Prompt Library
├── dashboard/          # React Frontend
│   ├── src/            # UI Components
│   └── package.json    # Frontend Deps
├── requirements.txt    # Python Deps
└── Dockerfile          # Container Config
```

## 🎯 Credits

This repo is forked and worked on by me but the original repo is developed by [mutonby](https://github.com/mutonby/openshorts).  

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
