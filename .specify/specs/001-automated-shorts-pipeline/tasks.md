# Tasks for AI-Powered Shorts Automation System Finalization

## Feature Name: AI-Powered Shorts Automation System Finalization

## Implementation Strategy

This feature will be implemented in phases, with each user story representing a deliverable increment. We will prioritize foundational setup, then proceed with Google Sheets integration, followed by AI content and video layout enhancements, and finally, optimized subtitles and automated scheduling. This approach allows for incremental delivery and testing.

## Dependencies

- **US1** (Google Sheets Integration) is foundational and should be completed first.
- **US2** (Enhanced AI Content & Video Layout) depends on the basic clip generation process and Google Sheets for storing bottom text. It can proceed once US1 is nearing completion.
- **US3** (Optimized Subtitles & Automated Scheduling) depends on the core subtitle generation (US2 provides the base text) and Google Sheets for scheduling metadata (US1).

## Parallel Execution Opportunities

- Within each user story phase, tasks marked with `[P]` can be executed in parallel.
- US2 and US3 have some independent tasks that could potentially overlap in development once their preceding dependencies are met.

---

### Phase 1: Setup

- [X] T001 Add `gspread` and `oauth2client` to `requirements.txt`
- [ ] T002 Verify Python dependencies installation with `pip install -r requirements.txt` (This is a manual verification step for the user)

### Phase 2: Foundational Tasks

*   **Story Goal**: Establish the core Google Sheets client for all subsequent data operations.
*   **Independent Test Criteria**: The `sheets_client.py` module can successfully authenticate and perform basic sheet operations (create, read columns, and initialize the main sheet if blank).

- [X] T003 Create `sheets_client.py` with authentication logic using a Service Account JSON key
- [X] T004 Implement `create_sheet_with_columns` function in `sheets_client.py` to create new sheets with predefined columns
- [X] T005 Implement an `initialize_main_sheet` function in `sheets_client.py` that checks if the main sheet has the required columns and creates them if they are missing.
- [X] T006 Implement basic `read_sheet_data` and `write_sheet_data` functions in `sheets_client.py`

### Phase 3: US1 - Google Sheets Integration for Clip Metadata Management

*   **Story Goal**: As a user, I want video metadata to be stored in and retrieved from Google Sheets so I can track clip processing and status.
*   **Independent Test Criteria**: Clip metadata is accurately logged to Google Sheets post-generation. The system prevents re-processing of existing segments. The frontend dashboard accurately displays clip statuses fetched from the backend.

- [X] T007 [P] [US1] Modify `main.py` to use `sheets_client.py` to query Google Sheet for existing segments to prevent re-processing
- [X] T008 [P] [US1] Modify `app.py` to use `sheets_client.py` to log clip metadata to Google Sheet after generation
- [X] T009 [P] [US1] Create new API endpoint in `app.py` to fetch clip data for a video from the Google Sheet
- [X] T010 [P] [US1] Modify `dashboard/src/App.jsx` to use the new API endpoint to display the status of clips

### Phase 4: US2 - Enhanced AI Content & Letterboxed Video Overlay

*   **Story Goal**: As a user, I want AI-generated titles and user-provided text to be burned onto letterboxed videos, and the AI content generation to be enhanced for narrative quality.
*   **Independent Test Criteria**: AI prompts generate improved narratives. Videos are generated with a 9:16 aspect ratio, black bars, and correct text overlays (AI-generated at top, user-provided at bottom). The UI allows inputting and saving bottom text.

- [X] T011 [P] [US2] Update Gemini prompt in `prompts.py` to request self-contained narrative arcs and use transcript of already generated clips
- [X] T012 [P] [US2] Modify `editor.py`'s `process_video_to_vertical` to create a 9:16 aspect ratio with black bars
- [X] T013 [P] [US2] Implement new function in `editor.py` to burn AI-generated text at the top using `ffmpeg drawtext`
- [X] T014 [P] [US2] Implement new function in `editor.py` to burn user-provided text at the bottom using `ffmpeg drawtext`
- [X] T015 [P] [US2] Modify `dashboard/src/components/ResultCard.jsx` to add an input field for bottom text and save it to the Google Sheet

### Phase 5: US3 - Optimized Subtitles & Automated Scheduling

*   **Story Goal**: As a user, I want optimized SRT subtitles for my clips and automated status updates for scheduled clips in Google Sheets.
*   **Independent Test Criteria**: `subtitles.py` generates optimized SRTs via a Gemini API call. The UI allows setting and saving scheduled times. The Google Apps Script successfully updates clip statuses based on time and status.

- [X] T016 [P] [US3] Create new function in `subtitles.py` to call Gemini API for optimizing raw subtitle text into shorter, engaging lines
- [X] T017 [P] [US3] Modify `subtitles.py`'s `generate_srt` to use the optimized text from the Gemini API call
- [X] T018 [P] [US3] Modify `dashboard/src/components/ResultCard.jsx` to allow setting a `scheduled_time` for each clip and save to Google Sheet
- [ ] T019 [US3] Update backend (`app.py`) to handle saving `scheduled_time` and `bottom_text` to Google Sheet
- [ ] T020 [US3] Instruct user to install provided Google Apps Script in their Google Sheet for automated status updates (User Action)

### Final Phase: Polish & Cross-Cutting Concerns

- [ ] T021 Review all modified files for code quality, formatting, and adherence to project conventions
- [ ] T022 Document API endpoints added to `app.py` (if not already done via FastAPI's auto-generation)


