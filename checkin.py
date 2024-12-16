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

conn_to_gsheet = helpers.create_connection(
    name='gsheets',
    conn_type=GSheetsConnection,
    cache_ttl_secs=0,
)

df_already_checkedin = helpers.get_checked_in_students(
    date=current_time.strftime('%Y-%m-%d'),
    time_period=time_period,
    conn=conn_to_gsheet,
    cache_ttl_secs=0,
)

############

st.title('Student Check-In')



st.subheader(
    f'Check-in for **{current_time.date()}** *{time_period}*'
)

results_container = st.container()

conn_to_student_roster = helpers.create_connection(
    name='studentinfo',
    conn_type=GSheetsConnection,
    cache_ttl_secs=60,
)

names = conn_to_student_roster.read(
    ttl=60,
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
        submit_time = datetime.datetime.now().time()
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
            df_new_checkins = pd.DataFrame(new_checkins_data)
            # Merge current with old checkins – should never have duplicates
            merged_df = pd.concat(
                [
                    df_already_checkedin,
                    df_new_checkins,
                ],
                ignore_index=True,
            ).sort_values(
                by='SubmitTime',
                ascending=False,
            )

            results_df = helpers.write_to_data_store(
                conn=conn_to_gsheet,
                data=merged_df,
            )

            results_container.write('Updated with new checkins:')
            # Make sure we refresh to reflect changes
            refresh_time_secs = 15
            results_container.write(
                '*Waiting {refresh_time_secs} seconds before refreshing page*'
            )
            results_container.write(results_df)
            time.sleep(refresh_time_secs)
            st.rerun(scope='app')
