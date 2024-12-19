import datetime
import helpers
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
from zoneinfo import ZoneInfo


current_time = datetime.datetime.now(tz=ZoneInfo('America/Los_Angeles'))
time_period = (
    helpers.TimePeriod.MORNING
    if current_time.hour < 9
    else helpers.TimePeriod.AFTERNOON
)

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


df_already_checkedin = helpers.get_checked_in_students(
    last_check_in_time=st.session_state['last_check_in_time'],
    date=current_time.strftime('%Y-%m-%d'),
    time_period=time_period,
)


df_already_checkedout = helpers.get_checked_out_students(
    last_check_out_time=st.session_state['last_check_out_time'],
    date=current_time.strftime('%Y-%m-%d'),
    time_period=time_period,
)

############


st.title('Check Out Students ')
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
                student_data['OverrideTime'] = None
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
            # Update that a check out occurred
            st.session_state['last_check_out_time'] = submit_time

            refresh_time_secs = 5
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
