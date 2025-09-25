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
