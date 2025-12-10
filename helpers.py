import datetime
from enum import Enum
import gspread
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from typing import Iterable

SECS_IN_DAY: int = 60 * 60 * 24
SECS_IN_HOUR: int = 60 * 60


class TimePeriod(Enum):
    MORNING = 'morning'
    AFTERNOON = 'afternoon'
    
    def __str__(self):
        return self.value

@st.cache_resource(
    max_entries=1,
    show_spinner='Fetching Student Roster'
)
def get_student_roster(
    name: str = 'studentinfo',
    cache_ttl_secs: float = SECS_IN_DAY,
) -> pd.DataFrame:
    conn_to_student_roster = create_connection(
        name=name,
        cache_ttl_secs=cache_ttl_secs,
    )

    names = conn_to_student_roster.read(
        ttl=cache_ttl_secs,
    )

    return names


@st.cache_resource
def create_connection(
    name: str = 'gsheets',
    cache_ttl_secs: float = SECS_IN_DAY,
) -> GSheetsConnection:
    """Creates a connection to a data source.

    Args:        
        name: The name of the connection.
        cache_ttl_secs: How long to cache the data for.

    Returns:
        conn: Connection object to data source.
    """
    # Create a connection object for the data base
    conn = st.connection(
        name=name,
        type=GSheetsConnection,
        ttl=cache_ttl_secs,
    )
    return conn

@st.cache_data
def dataframe_to_list(
    df: pd.DataFrame
) -> list[list[str]]:
    """Converts DataFrame to a list of list where each element is a string.

    Args:
        df: DataFrame to convert.

    Returns:
        list[list[str]]: List of list of strings.
    """
    data = df.values.tolist()
    # Make sure any None values go to blank strings
    data_clean = [
        [
            '' if value is None 
            else str(value)
            for value in row
        ]
        for row in data
    ]
    return data_clean

def append_data_to_sheet(
    conn: GSheetsConnection,
    data: Iterable[list[str]],
    spreadsheet_url: str,
    worksheet: str,
) -> None:
    """Appends a list of data to specified Google Sheet

    Args:
        conn: Connection object to Google Sheet
        data: Data to append at the end of spreadsheet
        spreadsheet: Name of spreadsheet
        worksheet: Name of worksheet
    """
    # Hack to use gspread using streamlit's version
    gc = conn._instance._client
    # Open specific spreadsheet and tab
    sh = gc.open_by_url(
        url=spreadsheet_url
    )
    sh = sh.worksheet(worksheet)  
    # Append all rows of data
    sh.append_rows(values=data)

def get_checked_in_students(
    date: str,
    time_period: TimePeriod,
    spreadsheet: str = 'checkin',
    worksheet: str = 'checkins',
):
    print('Getting checked in students')
    conn_to_gsheet = create_connection(
        name=spreadsheet,
    )
    df = get_students(
        conn=conn_to_gsheet,
        worksheet=worksheet,
        time_period=time_period,
        date=date,
    )
    # DEBUG
    print(df.shape)
    print(df.FullName)
    return df

def get_checked_out_students(
    date: str,
    time_period: TimePeriod,
    spreadsheet: str = 'checkout',
    worksheet: str = 'checkouts',
):
    print('Getting checked out students')
    conn_to_gsheet = create_connection(
        name=spreadsheet,
    )
    df = get_students(
        conn=conn_to_gsheet,
        worksheet=worksheet,
        time_period=time_period,
        date=date,
        # cache_ttl_secs=cache_ttl_secs,
    )
    return df

def get_students(
    conn: GSheetsConnection,
    worksheet: str | int | None = None,
    time_period: TimePeriod = TimePeriod.MORNING,
    date: datetime.datetime = None,
) -> pd.DataFrame:
    """Gets the students already checked in via a data source

    Args:        
        conn: Connection to be used.
        worksheet: Spreadsheet tab. Otherwise uses first tab.
        time_period: TimePeriod.MORNING or TimePeriod.AFTERNOON.
        date: Date to filter by.
        cache_ttl_secs: How long to cache the data for.

    Returns:
        pd.DataFrame: The students already checked in.
    """
    # Create a connection object for the data base
    df = conn.read(
        worksheet=worksheet,
        ttl=0,  # Always reset cache
    )
    # Filter only the date specified
    if date:
        df = df[df['SubmitDate'] == date]
    
    # Filter by time period
    # TODO: Determine if SubmitTime or OverrideTime should be used
    if time_period == TimePeriod.MORNING:
        df = df[pd.to_datetime(df['SubmitTime']).dt.hour < 9]
    elif time_period == TimePeriod.AFTERNOON:
        df = df[pd.to_datetime(df['SubmitTime']).dt.hour >= 9]

    # Remove duplicate names (keeping the time first entered)
    df = df.sort_values(by='SubmitTime')
    df = df.drop_duplicates(
        subset=[
            'FullName',
            'SubmitDate',
        ],
        keep='first',
    )
    
    return df

def get_attendance(
    students: Iterable[str] = None,
    date_start: datetime.datetime | None = None,
    date_end: datetime.datetime | None = None,
    drop_duplicates: bool = False,
) -> pd.DataFrame:
    """Get attendance for a date range and name of students.

    Args:
        students: List of students to get attendance for. If None, get all.
        date_start: Start date to get attendance for. Default to today
        date_end: End date to get attendance for. Default to next day.
        drop_duplicates: Whether to drop duplicate students. Default to False.
    Returns:
        DataFrame of attendance.
    """
    # Default dates available
    if date_start is None:
        date_start = datetime.datetime.today()
    if date_end is None:
        date_end = date_start + datetime.timedelta(days=1)

    # Check that date_end is later than start
    if date_end < date_start:
        raise ValueError('date_end must be later than date_start')

    # Data sources: checkin & checkout
    print('Getting checked in students')
    conn_to_gsheet_checkin = create_connection(
        name='checkin',
    )
    df_checkins = conn_to_gsheet_checkin.read(
        worksheet='checkins',
        ttl=0,  # Always reset cache
    )
    df_checkins['Action'] = 'checkin'

    print('Getting checked out students')
    conn_to_gsheet_checkout = create_connection(
        name='checkout',
    )
    df_checkouts = conn_to_gsheet_checkout.read(
        worksheet='checkouts',
        ttl=0,  # Always reset cache
    )
    df_checkouts['Action'] = 'checkout'

    # Combine data from checkins & checkouts, making action into its own column
    df = pd.concat([df_checkins, df_checkouts])

    # Filter only the date specified (convert to string first)
    df = df[
        (df['SubmitDate'] >= date_start.strftime('%Y-%m-%d')) &
        (df['SubmitDate'] <= date_end.strftime('%Y-%m-%d'))
    ]

    # Filter only students (using all if not given)
    if students:
        df = df[df['FullName'].isin(students)]

    # Make it easier to find dates
    df = df.sort_values(
        by=[
            'LastName',
            'FirstName',
            'SubmitDate',
            'SubmitTime',
        ],
        ascending=True,
    )
    order_of_columns = [
        'LastName',
        'FirstName',
        'Action',
        'SubmitDate',
        'SubmitTime',
        'OverrideTime',
        'Grade',
    ]
    df = df[order_of_columns]

    # Default to displaying all values by students
    if drop_duplicates:
        print('Dropping duplicate entries before displaying')
        df = df.drop_duplicates(
            subset=[
                'LastName',
                'FirstName',
                'SubmitDate',
                'Action',
            ],
            keep='last',  # Assume the last one submitted is the override
        )

    return df

def format_student_name(
        full_name: str,
        names: pd.DataFrame,
    ) -> str:
    '''Use name as search to get "FullName (Grade)".

    Args:
        full_name: Full name of student to format.
        names: DataFrame of student information.
    
    Returns:
        str: Formatted name.
    '''
    value = (
        names[names['FullName'] == full_name][
            ['FullName', 'Grade']
        ].values[0]
    )
    return f'{value[0]} ({value[1]})'

def get_corrections(
    students: Iterable[str] = None,
    date_start: datetime.datetime | None = None,
    date_end: datetime.datetime | None = None,
) -> pd.DataFrame:
    """Get corrections for a date range and name of students.

    Args:
        students: List of students to get corrections for. If None, get all.
        date_start: Start date to get corrections for. Default to today
        date_end: End date to get corrections for. Default to next day.

    Returns:
        DataFrame of corrections.
    """
    # Default dates available
    if date_start is None:
        date_start = datetime.datetime.today()
    if date_end is None:
        date_end = date_start + datetime.timedelta(days=1)

    # Check that date_end is later than start
    if date_end < date_start:
        raise ValueError('date_end must be later than date_start')

    # Data source
    conn_to_gsheet_checkin = create_connection(
        name='corrections',
    )
    df_corrections = conn_to_gsheet_checkin.read(
        worksheet='Form Responses 1',
        ttl=0,  # Always reset cache
    )

    # Rename Columns (defined from original source)
    column_renames = {
        'Choose Grade of Student': 'Grade',
        'Email Address': 'SubmittedBy',
        'Checkin, Checkout, or Remove?': 'Action',
        'StudentName': 'FullName',
        'Additional Notes': 'Notes',
    }
    df_corrections = df_corrections.rename(
        columns=column_renames,
    )

    # Convert to datetime (makes it possible to query against)
    df_corrections['Date'] = pd.to_datetime(
        df_corrections['Date'],
    )
    df_corrections['Time'] = pd.to_datetime(
        df_corrections['Time'],
    )

    # Filter only the date specified (convert to string first)
    df_corrections_filtered = df_corrections[
        (df_corrections['Date'] >= date_start.strftime('%Y-%m-%d')) &
        (df_corrections['Date'] <= date_end.strftime('%Y-%m-%d'))
    ]

    # Identify the columns to keep
    id_cols = [
        'Timestamp',
        'SubmittedBy',
        'Grade',
        'Session',
        'Action',
        'Date',
        'Time',
        'Notes',
    ]

    # Identify the columns to melt
    student_cols = [
        col for col in df_corrections_filtered.columns
        if 'Choose Student (Grade' in col
    ]

    # Melt/transform the DataFrame
    df_corrections_melted = pd.melt(
        df_corrections_filtered,
        id_vars=id_cols,
        value_vars=student_cols,
        value_name='FullName'  # The new column for the student names
    )

    # Remove rows where 'FullName' is empty (created by melt), just in case
    df_corrections_melted = df_corrections_melted.dropna(subset=['FullName'])

    # Filter only students (using all if not given)
    # This can only be done after melting to 'FullName'
    if students:
        df_corrections_melted = df_corrections_melted[
            df_corrections_melted['FullName'].isin(students)
        ]

    # Select and reorder the columns for the final DataFrame
    final_colums = [
        'SubmittedBy',
        'Timestamp',
        'FullName',
        'Date',
        'Session',
        'Time',
        'Action',
        'Grade',
        'Notes',
    ]
    df_corrections_final = df_corrections_melted[final_colums]
    df_corrections_final = df_corrections_final.sort_values(
        by=[
            'Date',
            'FullName',
            'Session',
            'Time',
        ],
        ascending=True,
    )

    # Make the date simply display as MM/DD/YYY
    df_corrections_final['Date'] = pd.to_datetime(
        df_corrections_final['Date']
    ).dt.strftime('%m/%d/%Y')
    # Make the time simply display as HH:MM
    df_corrections_final['Time'] = pd.to_datetime(
        df_corrections_final['Time']
    ).dt.strftime('%H:%M')

    return df_corrections_final

def sync_main_state(main_key, widget_key):
    """Updates the main state from the widget that was just clicked.

    Args:
       main_key: Key to the main value to be used.
       widget_key: Key to the widget value (changed in UI).
    """
    new_value = st.session_state[widget_key]
    st.session_state[main_key] = new_value

    # We need to ensure that the other widget (on the other tab) also gets updated
    # implicitly by updating its key in session_state.
    # The structure of the keys is known to be:
    # - status-{name}  (main_key)
    # - check_by_grades_{name}
    # - check_by_lastname_{name}

    if main_key.startswith('status-'):
        name = main_key.replace('status-', '', 1)

        grades_key = f'check_by_grades_{name}'
        lastname_key = f'check_by_lastname_{name}'

        # Update if they exist in session_state, or even if they don't,
        # it is safer to set them so when the widget renders it picks up the true value.
        st.session_state[grades_key] = new_value
        st.session_state[lastname_key] = new_value

    print(f'Synced {main_key} to {widget_key} with value {new_value}')
    st.rerun()
