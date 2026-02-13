import gspread
import os
from google.oauth2.service_account import Credentials

# Get the directory of the current script
script_dir = os.path.dirname(os.path.realpath(__file__))

# Construct the path to the service account file
SERVICE_ACCOUNT_FILE = os.path.join(script_dir, '..', 'service_account.json')

# Define the necessary scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_gspread_client():
    """
    Authenticates with the Google Sheets API using a service account
    and returns a gspread client.
    """
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(
            f"Service account key file not found at {SERVICE_ACCOUNT_FILE}. "
            "Please make sure to place it in the root of the project."
        )

    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    client = gspread.authorize(credentials)
    return client

def create_sheet_with_columns(client, spreadsheet_title, sheet_title, columns):
    """
    Creates a new spreadsheet with a worksheet and specified columns.
    If the spreadsheet already exists, it creates a new worksheet in it.
    If the worksheet already exists, it clears it and adds the columns.
    """
    try:
        spreadsheet = client.open(spreadsheet_title)
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(spreadsheet_title)
        print(f"Spreadsheet '{spreadsheet_title}' created. Please share it with the service account email.")

    try:
        worksheet = spreadsheet.worksheet(sheet_title)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_title, rows="100", cols="20")

    worksheet.append_row(columns)
    print(f"Successfully created or updated sheet '{sheet_title}' in spreadsheet '{spreadsheet_title}'")
    return worksheet

def initialize_main_sheet(client, spreadsheet_title, sheet_title="Clips"):
    """
    Initializes the main sheet by checking if it has the required columns and creates them if missing.
    """
    required_columns = ["Clip ID", "Status", "Generation Time", "AI Title", "Bottom Text", "Scheduled Time"]
    try:
        spreadsheet = client.open(spreadsheet_title)
    except gspread.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_title}' not found. Creating it now.")
        spreadsheet = client.create(spreadsheet_title)
        print(f"Spreadsheet '{spreadsheet_title}' created. Please share it with the service account email.")

    try:
        worksheet = spreadsheet.worksheet(sheet_title)
        current_columns = worksheet.row_values(1)
        if current_columns != required_columns:
            worksheet.clear()
            worksheet.append_row(required_columns)
            print(f"Main sheet '{sheet_title}' in '{spreadsheet_title}' updated with required columns.")
        else:
            print(f"Main sheet '{sheet_title}' in '{spreadsheet_title}' already has the required columns.")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_title, rows="100", cols="20")
        worksheet.append_row(required_columns)
        print(f"Main sheet '{sheet_title}' created with required columns in '{spreadsheet_title}'.")
    return spreadsheet

def read_sheet_data(client, spreadsheet_title, sheet_title):
    """
    Reads all data from a specified worksheet and returns it as a list of dictionaries.
    Each dictionary represents a row, with keys being column headers.
    """
    try:
        spreadsheet = client.open(spreadsheet_title)
        worksheet = spreadsheet.worksheet(sheet_title)
        data = worksheet.get_all_records()  # Returns a list of dictionaries
        print(f"Successfully read data from sheet '{sheet_title}' in spreadsheet '{spreadsheet_title}'.")
        return data
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_title}' not found.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet '{sheet_title}' not found in spreadsheet '{spreadsheet_title}'.")
        return None
    except Exception as e:
        print(f"An error occurred while reading sheet data: {e}")
        return None

def write_sheet_data(client, spreadsheet_title, sheet_title, data):
    """
    Writes a list of lists (rows) to a specified worksheet, starting from the first row.
    This will overwrite existing data.
    """
    try:
        spreadsheet = client.open(spreadsheet_title)
        worksheet = spreadsheet.worksheet(sheet_title)
        worksheet.clear()  # Clear existing data
        worksheet.append_rows(data)
        print(f"Successfully wrote data to sheet '{sheet_title}' in spreadsheet '{spreadsheet_title}'.")
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_title}' not found.")
        return False
    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet '{sheet_title}' not found in spreadsheet '{spreadsheet_title}'.")
        return False
    except Exception as e:
        print(f"An error occurred while writing sheet data: {e}")
        return False

def update_clip_data(client, spreadsheet_title, sheet_title, clip_id, data_to_update):
    """
    Updates specific cells for a given clip_id.
    data_to_update is a dict where keys are column headers.
    """
    try:
        spreadsheet = client.open(spreadsheet_title)
        worksheet = spreadsheet.worksheet(sheet_title)
        
        headers = worksheet.row_values(1)
        
        try:
            cell = worksheet.find(clip_id, in_column=1)
        except gspread.exceptions.CellNotFound:
            print(f"Clip ID '{clip_id}' not found.")
            return False
            
        row_index = cell.row
        
        for header, value in data_to_update.items():
            if header in headers:
                col_index = headers.index(header) + 1
                worksheet.update_cell(row_index, col_index, value)
        
        print(f"Successfully updated data for clip '{clip_id}'.")
        return True

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Spreadsheet '{spreadsheet_title}' not found.")
        return False
    except gspread.exceptions.WorksheetNotFound:
        print(f"Worksheet '{sheet_title}' not found in spreadsheet '{spreadsheet_title}'.")
        return False
    except Exception as e:
        print(f"An error occurred while updating clip data: {e}")
        return False


if __name__ == '__main__':
    try:
        client = get_gspread_client()
        print("Successfully authenticated with Google Sheets API.")
        
        spreadsheet_title = "OpenShorts Clips"
        main_sheet_name = "Clips"
        
        # Initialize the main sheet
        spreadsheet = initialize_main_sheet(client, spreadsheet_title, main_sheet_name)

        # Example of writing data
        sample_data = [
            ["Clip ID", "Status", "Generation Time", "AI Title", "Bottom Text", "Scheduled Time"],
            ["clip_001", "processing", "2023-10-26 10:00:00", "The first clip", "This is bottom text 1", ""],
            ["clip_002", "completed", "2023-10-26 10:05:00", "The second clip", "Another bottom text", ""]
        ]
        write_sheet_data(client, spreadsheet_title, main_sheet_name, sample_data)

        # Example of reading data
        read_data = read_sheet_data(client, spreadsheet_title, main_sheet_name)
        if read_data:
            print("\nData read from sheet:")
            for row in read_data:
                print(row)
        
        # Example: List all spreadsheets
        spreadsheets = client.list_spreadsheet_files()
        print("\nAvailable spreadsheets:")
        for spreadsheet in spreadsheets:
            print(f"- {spreadsheet['name']}")

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An error occurred: {e}")