import datetime
from enum import Enum
import gspread
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from typing import Iterable


class TimePeriod(Enum):
    MORNING = 'morning'
    AFTERNOON = 'afternoon'
    
    def __str__(self):
        return self.value



def create_connection(
    name: str = 'gsheets',
    conn_type = GSheetsConnection,
    cache_ttl_secs: float = 30,
):
    """Creates a connection to a data source.

    Args:        
        name: The name of the connection.
        conn_type: The type of connection to be used.
        cache_ttl_secs: How long to cache the data for.
    Returns:
        conn: Connection object to data source.
    """
    # Create a connection object for the data base
    conn = st.connection(
        name=name,
        type=conn_type,
        ttl=cache_ttl_secs,
    )
    return conn

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


def write_to_data_store(
    conn,
    data: list[dict[str, str]] | pd.DataFrame,
):
    # pass
    result_data = conn.update(
        # worksheet='checkin',
        data=data,
    )
    return result_data


def get_students(
    conn,
    worksheet: str | int | None = None,
    time_period: TimePeriod = TimePeriod.MORNING,
    date: datetime.datetime = None,
    cache_ttl_secs: float = 30,
) -> pd.DataFrame:
    """Gets the students already checked in via a data source

    Args:        
        conn: Connection to be used.
        date: Date to filter by.
        cache_ttl_secs: How long to cache the data for.
    Returns:
        pd.DataFrame: The students already checked in.
    """
    # Create a connection object for the data base
    df = conn.read(
        worksheet=worksheet,
        ttl=cache_ttl_secs,
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


    return df

