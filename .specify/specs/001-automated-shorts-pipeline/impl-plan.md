# Implementation Plan: Finalizing the AI-Powered Shorts Automation System

**Branch**: `001-automated-shorts-pipeline` | **Date**: 2026-02-12 | **Spec**: `/home/mk/Desktop/openshorts/.specify/specs/001-automated-shorts-pipeline/spec.md`
**Input**: Feature specification for AI-powered shorts automation.

## Summary

This implementation plan outlines the steps to finalize the AI-powered shorts automation system, incorporating user clarifications for key functionalities. The core tasks include robust Google Sheets integration for persistent data storage and memory, enhancing the AI's content generation with optimized subtitle logic, implementing a flexible video layout system with user-defined text overlays, and establishing a manual scheduling tracker with automated status updates via Google Apps Script. The implementation will build upon the existing Python backend (FastAPI, FFmpeg) and React frontend, ensuring a cohesive and functional system.

## Technical Context

**Language/Version**: Python 3.10+, Node.js v20
**Primary Dependencies**: `fastapi`, `uvicorn`, `gspread`, `oauth2client`, `scenedetect`, `ultralytics`, `torch`, `faster-whisper`, `google-genai`, `mediapipe`, `react`, `vite`
**Storage**: Google Sheets (for metadata, with application managing columns and new sheets per video), Local Filesystem (for video assets)
**Testing**: `pytest` (to be added)
**Target Platform**: Local development and Google Colab
**Project Type**: Web Application (Backend/API + Web Frontend)
**Performance Goals**: Performance is targeted towards efficient processing within the Google Colab environment, aiming for reasonable turnaround times for video and subtitle generation given the constraints of API calls and FFmpeg processing.
**Constraints**: The system operates within the constraints of the Google Colab environment, Python 3.10+, Node.js v20, and relies on Google Sheets for metadata storage and Google Drive for asset storage. Authentication for Google Sheets will use a Service Account JSON key. Scheduling automation relies on Google Apps Script, with security not being a primary concern for this iteration.
**Scale/Scope**: "almost unlimited" records in Google Sheets, "half-complete" project, handling long videos and generating multiple shorts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

-   **1. Professional-Grade User Experience**: The feature enhances UI elements for subtitle generation and scheduling, contributing to a seamless user experience. (Aligns)
-   **2. High-Performance Processing**: Optimized `.srt` generation and idempotent processing contribute to efficient video processing. The Colab environment is chosen for performance. (Aligns)
-   **3. Maintainable and Scalable Codebase**: Google Sheets as a database, modular components, and the overall design for Colab execution support maintainability and scalability. (Aligns)
-   **4. Colab-First Deployment**: Explicitly designed for Google Colab, leveraging `colab.py` for execution and testing, avoiding local setups. (Aligns)
-   **5. Comprehensive Testing and Quality Assurance**: New features (SRT generation, Google Sheets integration, scheduling logic) will require comprehensive testing. (Aligns)

## Project Structure (Additions & Modifications)

This feature will introduce changes to the following files and directories:

```text
.
├── app.py                   # Modify to add Google Sheets integration, scheduling endpoints
├── main.py                  # Modify to update prompts and interact with Google Sheets
├── editor.py                # Modify to add letterbox layout and top/bottom text overlay
├── subtitles.py             # Modify to enhance SRT generation via LLM call
├── prompts.py               # Modify with improved prompts
├── requirements.txt         # Add gspread, oauth2client
├── sheets_client.py         # NEW: Module for all Google Sheets operations
└── dashboard/
    └── src/
        └── components/
            └── ResultCard.jsx # Add UI for bottom text input and scheduling status
```

## Implementation Phases

### Phase 1: Database and System Memory (FR-1 to FR-4)

1.  **G-Sheets Setup**:
    *   Add `gspread` and `oauth2client` to `requirements.txt`.
    *   Create a new module `sheets_client.py` to handle all interactions with the Google Sheet. It will use a **Service Account JSON key** for authentication (user to provide `google_credentials.json`).
    *   The client will include functions to:
        *   Create and format the initial columns on a new sheet: `video_id`, `segment_start`, `segment_end`, `clip_status`, `version`, `gdrive_link`, `segment_text`, `scheduled_time`, `bottom_text`, `srt_file_link`.
        *   Create a new sheet for each new video, named after the video's title or ID. The application will manage columns and create a new sheet for each new video for normalization.
2.  **Backend Integration**:
    *   In `main.py`, use `sheets_client.py` to query the Google Sheet to prevent processing of existing segments (FR-3).
    *   In `app.py`, after a clip is generated, use `sheets_client.py` to log its metadata to the appropriate sheet (FR-2).
3.  **Frontend Integration**:
    *   Create a new API endpoint in `app.py` to fetch clip data for a video from the Google Sheet.
    *   In `dashboard/src/App.jsx`, use this endpoint to display the status of clips (FR-4).

### Phase 2: Content Intelligence & Layout (FR-5 to FR-7)

1.  **Prompt Enhancement**:
    *   In `prompts.py`, update the Gemini prompt to request self-contained narrative arcs and provide the transcript of already generated clips to ensure uniqueness (FR-5).
2.  **Letterbox Layout & Text Overlay**:
    *   In `editor.py`, modify `process_video_to_vertical` to create a 9:16 aspect ratio with black bars at the top and bottom.
    *   Implement a new function that uses `ffmpeg`'s `drawtext` filter to burn the AI-generated text (which will be the optimized SRT output) at the top and the user-provided text at the bottom. This will be a per-clip setting, managed through the UI (FR-6, FR-7).
3.  **UI for Bottom Text**:
    *   In `dashboard/src/components/ResultCard.jsx`, add an input field (likely in the "Post" modal) for the user to enter the bottom text for each clip. This will be saved to the Google Sheet.

### Phase 3: Captioning and Scheduling (FR-8 to FR-12)

1.  **Optimized SRT Generation**:
    *   In `subtitles.py`, create a new function that calls the Gemini API. This function will take the raw subtitle text and send it with a prompt to rephrase it into shorter, more engaging lines suitable for vertical video, potentially including relevant emojis. This will be a separate Gemini API call made to optimize the generated subtitles for clarity and style (FR-8).
    *   The `generate_srt` function will use this optimized text to create the `.srt` file.
2.  **Scheduling and Status Updates**:
    *   The `ResultCard.jsx` component will be updated to allow setting a `scheduled_time` for each clip, which will be saved to the Google Sheet via an API call to `app.py` (FR-10).
    *   The "Failed" Status Logic will be applied: A clip's status will be set to "Failed" if its `scheduled_time` has passed and its status is still "Pending".
    *   The scheduling automation for status updates (e.g., "Scheduled" to "Uploaded", "Pending" to "Failed") will be handled by a **Google Apps Script** with a time-driven trigger, not a background process in the application.

    ```javascript
    function updateClipStatuses() {
      var spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
      var sheets = spreadsheet.getSheets();
      var now = new Date();

      sheets.forEach(function(sheet) {
        // Skip the main sheet or any non-video sheets
        if (sheet.getName().startsWith("Sheet")) return;

        var dataRange = sheet.getDataRange();
        var data = dataRange.getValues();
        var headers = data[0];
        var statusCol = headers.indexOf("clip_status");
        var scheduledTimeCol = headers.indexOf("scheduled_time");

        if (statusCol === -1 || scheduledTimeCol === -1) return;

        for (var i = 1; i < data.length; i++) {
          var row = data[i];
          var status = row[statusCol];
          var scheduledTime = new Date(row[scheduledTimeCol]);

          if (scheduledTime instanceof Date && !isNaN(scheduledTime)) {
            if (status === "Scheduled" && scheduledTime < now) {
              sheet.getRange(i + 1, statusCol + 1).setValue("Uploaded");
            } else if (status === "Pending" && scheduledTime < now) {
              sheet.getRange(i + 1, statusCol + 1).setValue("Failed");
            }
          }
        }
      });
    }
    ```
    This script will run automatically on a timer (e.g., every hour) and update the statuses, fulfilling the requirement for automated, time-based updates.

I will now proceed with implementing these changes.
