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

# Session state to track the last time a check in was done
if 'last_check_in_time' not in st.session_state:
    st.session_state['last_check_in_time'] = None
if 'last_check_out_time' not in st.session_state:
    st.session_state['last_check_out_time'] = current_time.timestamp()
if 'checkin_conn' not in st.session_state:
    st.session_state['checkin_conn'] = helpers.create_connection(
        name='checkin',
    )
print(f'{st.session_state.last_check_in_time=}')
print(f'{st.session_state.last_check_out_time=}')

df_already_checkedin = helpers.get_checked_in_students(
    last_check_in_time=st.session_state['last_check_in_time'],
    date=current_time.strftime('%Y-%m-%d'),
    time_period=time_period,
)

############

st.title('Student Check-In')



st.subheader(
    f'Check-in for **{current_time.date()}** *{time_period}*'
)

results_container = st.container()

names = helpers.get_student_roster(
    name='studentinfo',
    cache_ttl_secs=helpers.SECS_IN_DAY,
)

last_name_letters = sorted(names['LastName'].str[0].unique())



# Override time option they were checked in. Defaults to current time
is_override = st.checkbox('Override Time')
override_checkin_time = None

with st.form(key='my_form'):
    submitted = st.form_submit_button('Check In')

    
    if is_override:
        now = datetime.datetime.now(
            tz=ZoneInfo('America/Los_Angeles')
        )
        print(f'Datetime: {now=}')
        time_inc_minute = 10
        override_checkin_time = st.time_input(
            label='Check-in Time',
            value=datetime.time(
                hour=now.hour,
                minute=(now.minute // time_inc_minute)*time_inc_minute,
                tzinfo=ZoneInfo('America/Los_Angeles')
            ),
            step=datetime.timedelta(minutes=time_inc_minute),
        )
        print(f'Override: {override_checkin_time=}')


    # selected_names = st.multiselect('Names', names['FullName'])
    all_names = {}

    # Display each name grouped by last name so a section appears for each last name letter
    for letter in last_name_letters:
        st.subheader(letter)
        filtered_names = names[names['LastName'].str.startswith(letter)]
        filtered_names = filtered_names.sort_values(by='FullName')
        # Split names into three columns to be displayed
        cols = st.columns(3)
        for index, name in enumerate(filtered_names['FullName']):
            col_index = index % 3
            col = cols[col_index]
            # Checked in students are not selectable or to be written to DB
            is_already_checked_in = (
                name in df_already_checkedin['FullName'].values
            )
            if is_already_checked_in:
                label_info = f'~~{name}~~'
                # Time checked in is DF's either override or if empty, submittime
                time_checkedin = (
                    df_already_checkedin
                    [df_already_checkedin['FullName'] == name]
                    ['OverrideTime']
                    .values[0]
                )
                
                # Check if time_checkedin is nan
                if pd.isna(time_checkedin):
                    time_checkedin = (
                        df_already_checkedin
                        [df_already_checkedin['FullName'] == name]
                        ['SubmitTime']
                        .values[0]
                    )

                
                label_info += f' [{time_checkedin}]'
            else:
                label_info = f'{name}'
            is_student_checked = col.checkbox(
                label=label_info,
                key=name,
                value=is_already_checked_in,
                disabled=is_already_checked_in,
            )
            # Only need to track students already checked in
            if not is_already_checked_in:
                all_names[name] = {
                    'is_checked_in': is_student_checked,
                }
        st.divider()
    
    if submitted:
        # Track time of actual submission
        submit_time = (
            datetime.datetime.now(
                tz=ZoneInfo('America/Los_Angeles'),
            )
            .time()
        )
        st.write(f'Submitted on {submit_time} ')
        st.write(f'{override_checkin_time}')
        
        new_checkins_data: list[dict[str, str]] = []
        for full_name, student_info in all_names.items():   
            checkedin = student_info['is_checked_in']
            if not checkedin:
                continue
            info = names[names['FullName'] == full_name]
            
            student_data = {}
            student_data['FullName'] = full_name
            student_data['FirstName'] = info['FirstName'].values[0]
            student_data['LastName'] = info['LastName'].values[0]
            student_data['Grade'] = str(info['Grade'].values[0])
            student_data['SubmitTime'] = (
                submit_time.strftime('%H:%M:%S')
            )
            student_data['SubmitDate'] = (
                current_time.strftime('%Y-%m-%d')
            )
            student_data['OverrideTime'] = (
                None if not is_override else override_checkin_time
            )
            new_checkins_data.append(student_data)

            
        if new_checkins_data:
            df_new_checkins = (
                pd.DataFrame(
                    new_checkins_data,
                )
                .astype(
                    {'Grade': str},
                )
                .sort_values(
                    by='SubmitTime',
                    ascending=False,
                )
            )
            # Sort the columns in specified order
            columns = [
                'SubmitTime',
                'SubmitDate',
                'OverrideTime',
                'FullName',
                'LastName',
                'FirstName',
                'Grade',
            ]
            df_new_checkins = df_new_checkins[columns]


            # Convert DF to a list of list (we can ignore the header)
            helpers.append_data_to_sheet(
                conn=st.session_state['checkin_conn'],
                data=helpers.dataframe_to_list(df_new_checkins),
                spreadsheet_url=(
                    st.secrets.connections.checkin.spreadsheet
                ),
                worksheet='checkins',
            )

            # Update that a check in occurred
            st.session_state['last_check_in_time'] = submit_time
    
            results_container.success('Students checked in successfully!')
            results_container.write('Updated with new check-ins:')
            # Make sure we refresh to reflect changes
            refresh_time_secs = 5
            results_container.write(
                f'*Waiting {refresh_time_secs} seconds before refreshing page*'
            )
            results_container.write(df_new_checkins)
            time.sleep(refresh_time_secs)
            st.rerun(scope='app')
