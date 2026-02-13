# Feature Specification: Finalizing the AI-Powered Shorts Automation System

> This specification details the remaining work required to complete the AI-powered shorts generation pipeline. The focus is on adding a database for memory, improving content intelligence, implementing a full captioning and layout system, and adding a manual scheduling tracker.

## 1. User Stories & Scenarios

### 1.1. User Stories

- As a content creator, I want the system to remember all previously generated clips from a video so that I can avoid creating duplicate content and systematically process a whole video over time.
-   As a user, I want to add my social media handle to the bottom of my videos so that I can brand my content.
-   As a social media manager, I want a tool to track my manual posting schedule so I can see which generated clips I have planned to upload and which ones have been posted.

### 1.2. Key Scenarios

-   **Scenario 1: Generating Captions Post-Generation**
    -   A video clip is generated and its Google Drive link is saved to the database.
    -   In the UI, the user clicks a "Generate Subtitles" button on the generated clip card.
    -   The system generates an optimized `.srt` file for the video, saves it (e.g., to Google Drive alongside the video or a dedicated captions storage), and logs the `.srt` file's location in the database.

-   **Scenario 2: Manual Scheduling**
    -   A clip has been generated. Its status is "Pending".
    -   The user clicks a "Schedule" button.
    -   A dialog appears where the user can input a date and time.
    -   The user confirms, and the status of the clip in the database is updated to "Scheduled", with the specified time recorded.
    -   The user then manually uploads the video to their chosen platform at the scheduled time.

-   **Scenario 3: Automatic Status Updates**
    -   A clip has a status of "Scheduled" and a scheduled time that is now in the past.
    -   An automated system process runs, checks the time, and updates the clip's status to "Uploaded".
    -   Another clip has a status of "Pending" and its scheduled time has passed without manual intervention to change its status. The system process updates its status to "Failed".

## 2. Functional Requirements

### 2.1. Database & System Memory
-   **FR-1: Google Sheets Database**: A Google Sheet, acting as the database, MUST be used to log all processing activities. It should accommodate an "almost unlimited" number of records, potentially utilizing multiple sheets for data normalization based on long videos, with a main sheet for videos awaiting live status. The provided Google Sheet link (or a similar one) will be used: "https://docs.google.com/spreadsheets/d/1Ssj97_aKAm4hFLnP7iQudswo6iExAPXgx9tWm3NETKA/edit?usp=sharing".
-   **FR-2: Comprehensive Logging**: The database MUST store the video ID, segments, clip status, and for each generated clip, a version number and its Google Drive link.
-   **FR-3: Idempotent Generation**: The backend MUST consult the database to ensure the same segment is not processed twice.
-   **FR-4: UI State from Database**: The frontend MUST use the database to visually distinguish between generated and non-generated segments.
-   **FR-4.1: Denormalized Upload Log**: For ease of use, the record for a scheduled upload MUST also contain the actual text of the segment.

### 2.2. Content Intelligence
-   **FR-5: Enhanced AI Prompting**: The prompt to the LLM MUST be updated to ask for segments that are self-contained and have a clear narrative structure (hook, payoff). It should be also given only the transcripts of the previously generated clips so that it can generate unique clips everytime.

### 2.3. Captioning and Layout System
-   **FR-6: Letterbox Layout Implementation**: The `editor.py` script MUST be modified to produce a 9:16 video with the main content cropped to ~4:3 and centered (without cropping out the face, basically tracking the face before cropping and then moving the cropped video to the middle), leaving black bars at the top and bottom. If face detection fails, the system will skip cropping and use the full, original frame.
-   **FR-7: User-Provided Bottom Text Overlay**: The system MUST allow a user to input a custom text string to be rendered in the bottom black bar.
-   **FR-8: SRT File Generation**: The system MUST generate an optimized `.srt` file for each video clip. "Optimized" means the captions are intelligently segmented, correctly punctuated (with optional emojis), and display phrases that are grammatically correct, coherent, and avoid clutter. The `.srt` file's location (e.g., Google Drive link) MUST be logged in the database.


### 2.4. Manual Scheduling Tracker
-   **FR-10: Manual Status Toggling**: The UI MUST allow a user to set a scheduled time for a clip and manually toggle its status between "Pending" and "Scheduled".
-   **FR-11: Time-Based Status Automation**: The system MUST have a background process that automatically:
        -   Updates the status from "Scheduled" to "Uploaded" when the scheduled time has passed.
        -   Updates the status from "Pending" to "Failed" if the scheduled time has passed and the clip's status has not been manually changed to 'Scheduled' or 'Uploaded'.
-   **FR-12: Store Drive Link**: The database entry for each generated clip version MUST include the direct Google Drive link to the video file.

## 3. Non-Functional Requirements

-   **NFR-1: Modularity**: The new components (Database, Status Updater) should be modular.
-   **NFR-2: Error Logging**: The status updater process must have robust error logging.

## 4. Success Criteria

-   The system successfully prevents the creation of duplicate clips for the same video with 100% accuracy.
-   A clip's status correctly and automatically transitions from "Scheduled" to "Uploaded" after its scheduled time.

## 5. Assumptions & Dependencies

-   **Assumptions**:
    -   Videos are successfully uploaded to a known location in Google Drive, from which a shareable link can be derived.
    -   The user will manually handle all aspects of uploading the video file to the final social media platform.
-   **Dependencies**:
    -   A time-scheduling library for the background process (e.g., `schedule` or a cron job).

## 6. Out of Scope

-   Any integration with social media APIs for automatic uploading.
-   A UI for managing the Google Drive folder directly.

## 7. Open Questions



## 8. Key Entities & Data Model (Additions)

-   **Clip Table/Sheet**:
    -   `gdrive_link` (string)
    -   `status` (enum: Pending, Scheduled, Uploaded, Failed)
    -   `scheduled_time` (datetime)
    -   `bottom_text` (string)
    -   `srt_file_link` (string)
    -   `segment_text` (string)

## Clarifications

### Session 2026-02-12

- Q: Which approach should the system implement for captioning? → A: Generate an .srt file with optimized captions (no burned-in styles, no style selection UI).
- Q: What specific characteristics define "optimized" captions for the .srt file? → A: The phrases that appear are correct without any clutter, right punctuations (emoji if needed). Basically the phrases that appear altogether should be a part of a sentence (shouldn't clutter when are displayed) or should be good enough toe appearing altogether.
- Q: What is the anticipated maximum number of clips/records the system will store in the file-based database? → A: The system will use Google Sheets as the database and is expected to handle an "almost unlimited" number of records. Data will be normalized based on the long video, with different sheets for various videos, with a main sheet for videos yet to be live. Google Sheet link: "https://docs.google.com/spreadsheets/d/1Ssj97_aKAm4hFLnP7iQudswo6iExAPXgx9tWm3NETKA/edit?usp=sharing"
- Q: What should the time period be for a "Pending" clip to be changed to "Failed" if not scheduled? → A: If the user manually switches a "Pending" clip to "Done" before its scheduled time, it should remain "Done". If the "scheduled time is passed, and I do not switch it to schedule", it should be marked as "Failed".
- Q: How should a user manually mark a "Pending" clip as successfully completed before its scheduled time, if "Done" is not a new status? → A: Manually change the status to "Scheduled" (if a scheduled time is also set).