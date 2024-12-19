import datetime
import helpers
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo

current_time = datetime.datetime.now(tz=ZoneInfo('America/Los_Angeles'))

# Session state default if first time opening up app
if 'last_check_in_time' not in st.session_state:
    st.session_state['last_check_in_time'] = None
if 'last_check_out_time' not in st.session_state:
    st.session_state['last_check_out_time'] = current_time.timestamp()
if 'checkout_conn' not in st.session_state:
    st.session_state['checkout_conn'] = helpers.create_connection(
        name='checkout',
    )
print(f'{st.session_state.last_check_in_time=}')
print(f'{st.session_state.last_check_out_time=}')

df_already_checkedin_morning = helpers.get_checked_in_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.MORNING,
    last_check_in_time=st.session_state['last_check_in_time'],
)

df_already_checkedin_afternoon = helpers.get_checked_in_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.AFTERNOON,
    last_check_in_time=st.session_state['last_check_in_time'],
)


df_already_checkedout_morning = helpers.get_checked_out_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.MORNING,
    last_check_out_time=st.session_state['last_check_out_time'],
)

df_already_checkedout_afternoon = helpers.get_checked_out_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=helpers.TimePeriod.AFTERNOON,
    last_check_out_time=st.session_state['last_check_out_time'],
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