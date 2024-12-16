import streamlit as st
import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection



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


def get_already_checked_in_students(
    conn,
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
        ttl=cache_ttl_secs,
    )
    # Filter only the date specified
    if date:
        df = df[df['SubmitDate'] == date]

    return df

