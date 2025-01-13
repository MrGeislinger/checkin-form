import datetime
import helpers
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from zoneinfo import ZoneInfo

refresh_cache: bool = False
current_time = datetime.datetime.now(tz=ZoneInfo('America/Los_Angeles'))

# If new date, refresh cache
if st.session_state.get('last_date', None) != current_time.strftime('%Y-%m-%d'):
    st.session_state['last_period'] = current_time.strftime('%Y-%m-%d')
    print(f'Cache: New date {current_time.strftime("%Y-%m-%d")}')
    refresh_cache = True

for data_type in ('checkedin', 'checkedout'):
    for time_period in (helpers.TimePeriod.MORNING, helpers.TimePeriod.AFTERNOON):
        cache_name = f'{data_type}_df_{time_period}'
        if refresh_cache or (cache_name not in st.session_state):
            st.session_state[cache_name] = helpers.get_checked_in_students(
                date=current_time.strftime('%Y-%m-%d'),
                time_period=time_period,
            )

df_already_checkedin_morning = st.session_state['checkedin_df_morning']
df_already_checkedin_afternoon = st.session_state['checkedin_df_afternoon']
df_already_checkedout_morning = st.session_state['checkedout_df_morning']
df_already_checkedout_afternoon = st.session_state['checkedout_df_afternoon']

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