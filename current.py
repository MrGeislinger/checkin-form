import datetime
import helpers
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo

current_time = datetime.datetime.now(tz=ZoneInfo('America/Los_Angeles'))

conn_to_gsheet_checkin = helpers.create_connection(
    name='checkin',
    conn_type=GSheetsConnection,
    cache_ttl_secs=10,
)

df_already_checkedin_morning = helpers.get_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.MORNING,
    conn=conn_to_gsheet_checkin,
    cache_ttl_secs=10,
)

df_already_checkedin_afternoon = helpers.get_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.AFTERNOON,
    conn=conn_to_gsheet_checkin,
    cache_ttl_secs=10,
)

conn_to_gsheet_checkout = helpers.create_connection(
    name='checkout',
    conn_type=GSheetsConnection,
    cache_ttl_secs=10,
)

df_already_checkedout_morning = helpers.get_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.MORNING,
    conn=conn_to_gsheet_checkout,
    cache_ttl_secs=10,
    worksheet='checkouts',
)

df_already_checkedout_afternoon = helpers.get_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.AFTERNOON,
    conn=conn_to_gsheet_checkout,
    cache_ttl_secs=10,
    worksheet='checkouts',
)

######

st.title('Students at Falcon\'s Nest')

st.subheader('Students at the Nest Right Now')

current_timetime_period = (
    helpers.TimePeriod.MORNING
    if current_time.hour < 9
    else helpers.TimePeriod.AFTERNOON
)

if current_timetime_period == helpers.TimePeriod.MORNING:
    df_checkedin = df_already_checkedin_morning
    df_checkedout = df_already_checkedout_morning

else:
    df_checkedin = df_already_checkedin_afternoon
    df_checkedout = df_already_checkedout_afternoon



# Only students currently checked-in for the time period but not yet checked out
df_current = df_checkedin[
    ~(
        df_checkedin['FullName']
        .isin(
            df_checkedout['FullName']
        )
    )
]
st.dataframe(df_current)

st.divider()

st.subheader('Students this morning')

st.dataframe(df_already_checkedin_morning)


st.subheader('Students this afternoon')

st.dataframe(df_already_checkedin_afternoon)

st.divider()