import datetime
import helpers
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo

current_time = datetime.datetime.now(tz=ZoneInfo('America/Los_Angeles'))

conn_to_gsheet = helpers.create_connection(
    name='gsheets',
    conn_type=GSheetsConnection,
    cache_ttl_secs=0,
)
df_already_checkedin = helpers.get_checked_in_students(
    date=current_time.strftime('%Y-%m-%d'),
    conn=conn_to_gsheet,
    cache_ttl_secs=0,
)

st.title('Students at Falcon\'s Nest')

st.subheader('Students at the Nest Right Now')
st.dataframe(df_already_checkedin)

st.divider()

st.subheader('Students this morning')
df_checkedin_morning = helpers.get_checked_in_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.MORNING,
    conn=conn_to_gsheet,
    cache_ttl_secs=0,
)
st.dataframe(df_checkedin_morning)

st.subheader('Students this afternoon')

df_checkedin_afternoon = helpers.get_checked_in_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.AFTERNOON,
    conn=conn_to_gsheet,
    cache_ttl_secs=0,
)
st.dataframe(df_checkedin_afternoon)

st.divider()