import datetime
import helpers
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
from zoneinfo import ZoneInfo

refresh_cache: bool = False
current_time = datetime.datetime.now(tz=ZoneInfo('America/Los_Angeles'))
time_period = (
    helpers.TimePeriod.MORNING
    if current_time.hour < 9
    else helpers.TimePeriod.AFTERNOON
)

if 'checkout_conn' not in st.session_state:
    # Ensure the cache doesn't live too long & cause issues from time period
    st.session_state['checkout_conn'] = helpers.create_connection(
        name='checkout',
        cache_ttl_secs=(3 * helpers.SECS_IN_HOUR),
    )

if st.session_state.get('time_period', None) != time_period:
    st.session_state['time_period'] = time_period
    print(f'Cache: New time period {time_period}')

# If new date, refresh cache
if st.session_state.get('last_date', None) != current_time.strftime('%Y-%m-%d'):
    st.session_state['last_date'] = current_time.strftime('%Y-%m-%d')
    print(f'Cache: New date {current_time.strftime("%Y-%m-%d")}')
    refresh_cache = True


cache_name_checkin = f'checkedin_df_{st.session_state["time_period"]}'
cache_name_checkout = f'checkedout_df_{st.session_state["time_period"]}'

if refresh_cache or (cache_name_checkin not in st.session_state):
    df_already_checkedin = helpers.get_checked_in_students(
        date=current_time.strftime('%Y-%m-%d'),
        time_period=time_period,
    )
    st.session_state[cache_name_checkin] = df_already_checkedin
else:
    df_already_checkedin = st.session_state[cache_name_checkin]

if refresh_cache or (cache_name_checkout not in st.session_state):
    df_already_checkedout = helpers.get_checked_out_students(
        date=current_time.strftime('%Y-%m-%d'),
        time_period=time_period,
    )
    st.session_state[cache_name_checkout] = df_already_checkedout
else:
    df_already_checkedout = st.session_state[cache_name_checkout]


############


st.title('Check Out Students ')

n_current_students = len(df_already_checkedin) - len(df_already_checkedout)
st.subheader(f'# of kids currently in the nest: {n_current_students}')
st.write(f'{len(df_already_checkedin)} checked in today')
st.write(f'{len(df_already_checkedout)} checked out today')

st.subheader(
    f'Check-out for **{current_time.date()}** *{time_period}*'
)

# Only students currently checked-in for the time period but not yet checked out
df_to_checkout = df_already_checkedin[
    ~(
        df_already_checkedin['FullName']
        .isin(
            df_already_checkedout['FullName']
        )
    )
]

results_container = st.container()

# Override time option they were checked out. Defaults to current time
is_override = st.checkbox('Override Time')
override_checkout_time = None

if is_override:
    now = datetime.datetime.now(
        tz=ZoneInfo('America/Los_Angeles')
    )
    print(f'Datetime: {now=}')
    time_inc_minute = 10
    override_checkout_time = st.time_input(
        label='Check-out Time',
        value=datetime.time(
            hour=now.hour,
            minute=(now.minute // time_inc_minute)*time_inc_minute,
            tzinfo=ZoneInfo('America/Los_Angeles')
        ),
        step=datetime.timedelta(minutes=time_inc_minute),
    )
    print(f'Override: {override_checkout_time=}')

with st.form(key='checkout_form'):
    selected_names = st.multiselect(
        'Select students to check out',
        df_to_checkout['FullName'],
    )
    checkout_submitted = st.form_submit_button('Check Out')

    if checkout_submitted:
        if selected_names:
            # Add checkout time
            submit_time = datetime.datetime.now(
                tz=ZoneInfo('America/Los_Angeles')
            ).time()
            checkout_data = []
            for name in selected_names:
                info = df_to_checkout[df_to_checkout['FullName'] == name]
                student_data = {}
                student_data['FullName'] = name
                student_data['FirstName'] = info['FirstName'].values[0]
                student_data['LastName'] = info['LastName'].values[0]
                student_data['Grade'] = str(info['Grade'].values[0])
                student_data['SubmitTime'] = submit_time.strftime('%H:%M:%S')
                student_data['SubmitDate'] = current_time.strftime('%Y-%m-%d')
                student_data['OverrideTime'] = (
                    None if not is_override else override_checkout_time
                )
                checkout_data.append(student_data)

            df_checkout = pd.DataFrame(checkout_data).astype({'Grade': str})
            columns = [
                'SubmitTime',
                'SubmitDate',
                'OverrideTime',
                'FullName',
                'LastName',
                'FirstName',
                'Grade',
            ]
            df_checkout = df_checkout[columns]

            # Convert DF to a list of list (we can ignore the header)
            helpers.append_data_to_sheet(
                conn=st.session_state['checkout_conn'],
                data=helpers.dataframe_to_list(df_checkout),
                spreadsheet_url=st.secrets.connections.checkout.spreadsheet,
                worksheet='checkouts',
            )

            # Mutate already checked-in for cache
            st.session_state[cache_name_checkout] = pd.concat(
                [
                    df_already_checkedout,
                    df_checkout,
                ]
            )

            refresh_time_secs = 2
            results_container.success('Students checked out successfully!')
            results_container.write(
                f'*Waiting {refresh_time_secs} seconds before refreshing page*'
            )
            results_container.write(df_checkout)
            time.sleep(refresh_time_secs)
            st.rerun()
        else:
            st.warning('Please select at least one student to check out.')

st.divider()

st.subheader('Students still present')
st.dataframe(df_to_checkout)

st.subheader('Students already checked in')
st.write(df_already_checkedin)

st.subheader('Students already checked out')
st.write(df_already_checkedout)
