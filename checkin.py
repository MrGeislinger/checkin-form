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

# Session state to track the last time a check in was done
if 'checkin_conn' not in st.session_state:
    # Ensure the cache doesn't live too long & cause issues from time period
    st.session_state['checkin_conn'] = helpers.create_connection(
        name='checkin',
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

# Checkin data
if refresh_cache or (cache_name_checkin not in st.session_state):
    df_already_checkedin = helpers.get_checked_in_students(
        date=current_time.strftime('%Y-%m-%d'),
        time_period=time_period,
    )
    st.session_state[cache_name_checkin] = df_already_checkedin
    print(f'Updated cache for {cache_name_checkin}')
else:
    df_already_checkedin = st.session_state[cache_name_checkin]
    print(f'Using data from cache {cache_name_checkin}')

# Checkout data
if refresh_cache or (cache_name_checkout not in st.session_state):
    df_already_checkedout = helpers.get_checked_out_students(
        date=current_time.strftime('%Y-%m-%d'),
        time_period=time_period,
    )
    st.session_state[cache_name_checkout] = df_already_checkedout
else:
    df_already_checkedout = st.session_state[cache_name_checkout]

############

st.title('Student Check-In')

n_current_students = len(df_already_checkedin) - len(df_already_checkedout)
st.subheader(f'# of kids currently in the nest: {n_current_students}')
st.write(f'{len(df_already_checkedin)} checked in today')
st.write(f'{len(df_already_checkedout)} checked out today')

st.subheader(
    f'Check-in for **{current_time.date()}** *{time_period}*'
)

#####
names = helpers.get_student_roster(
    name='studentinfo',
    cache_ttl_secs=helpers.SECS_IN_DAY,
)

last_name_letters = sorted(names['LastName'].str[0].unique())
# Note this is probably a mixed type
grades = [grade for grade in names['Grade'].unique()]

######
st.html('<a href="#check-in-the-following">Go To Bottom</a>')


results_container = st.container()

# Holds all names in roster
all_names = {}

st.divider()

tab1, tab2 = st.tabs(['🏫 GRADE', '👤 LAST NAME'])
# Display each name grouped by grade (each its own section)
with tab1:
    for grade in grades:
        st.subheader(f'Grade {grade}')
        filtered_names = names[names['Grade'] == grade]
        filtered_names = filtered_names.sort_values(
            by=['LastName', 'FirstName'],
        )
        # Split names into three columns to be displayed
        n_cols = 3
        cols = st.columns(n_cols)
        # Calculate the total number of names in grouping
        n_names_in_group = len(filtered_names)
        # Calculate the number of names per column (rounding up)
        names_per_col = (n_names_in_group + n_cols - 1) // n_cols
        col_index = -1
        for index, name in enumerate(filtered_names['FullName']):
            if index % names_per_col == 0:
                col_index += 1
                
            col = cols[col_index]
            # Checked in students are not selectable or to be written to DB
            is_already_checked_in = (
                name in df_already_checkedin['FullName'].values
            )
            if is_already_checked_in:
                label_info = f'~~{name}~~'
                # Time checked in DF's either override or if empty, submit time
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
                value=st.session_state.get(f'status-{name}'),
                key=f'check_by_grades_{name}',
                on_change=helpers.sync_main_state,
                args=(
                    f"status-{name}",  # main value for status
                    f'check_by_grades_{name}',  # value for this UI widget
                ),
                disabled=is_already_checked_in,
            )

            # Only need to track students already checked in
            if not is_already_checked_in:
                all_names[name] = {
                    'is_checked_in': is_student_checked,
                }
        st.divider()
# Display each name grouped by last name (each its own section)        
with tab2:
    for letter in last_name_letters:
        st.subheader(letter)
        filtered_names = names[names['LastName'].str.startswith(letter)]
        filtered_names = filtered_names.sort_values(
            by=['LastName', 'FirstName'],
        )
        # Split names into three columns to be displayed
        n_cols = 3
        cols = st.columns(n_cols)
        # Calculate the total number of names in grouping
        n_names_in_group = len(filtered_names)
        # Calculate the number of names per column (rounding up)
        names_per_col = (n_names_in_group + n_cols - 1) // n_cols
        col_index = -1
        for index, name in enumerate(filtered_names['FullName']):
            if index % names_per_col == 0:
                col_index += 1
                
            col = cols[col_index]
            # Checked in students are not selectable or to be written to DB
            is_already_checked_in = (
                name in df_already_checkedin['FullName'].values
            )
            if is_already_checked_in:
                label_info = f'~~{name}~~'
                # Time checked in DF's either override or if empty, submit time
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
                value=st.session_state.get(f'status-{name}'),
                key=f'check_by_lastname_{name}',
                on_change=helpers.sync_main_state,
                args=(
                    f"status-{name}",  # main value for status
                    f'check_by_lastname_{name}',  # value for this UI widget
                ),
                disabled=is_already_checked_in,
            )
            # Only need to track students already checked in
            if not is_already_checked_in:
                all_names[name] = {
                    'is_checked_in': is_student_checked,
                }
        st.divider()



################ SUBMISSION FORM ################

st.html('<a href="#student-check-in">Go To Top</a>')

# Override time option they were checked in. Defaults to current time
is_override = st.checkbox('Override Time')
override_checkin_time = None

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


with st.form(key='my_form'):

    st.write('## Check in the following')
    # Get full names of checked students to filter on the roster
    full_names = [
        state.split('-', maxsplit=1)[1]
        for state in st.session_state
        if state.startswith('status-') and st.session_state[state]
    ]
    # Only display checked students if they are checked
    if full_names:
        st.write(
            names[
                names['FullName'].isin(full_names)
            ]
            .sort_values(
                by=[
                    'LastName',
                    'FirstName',
                ],
            )[
                [
                    'FullName',
                    'Grade',
                    'LastName',
                    'FirstName',
                ]
            ]
        )

    submitted = st.form_submit_button('Check In')

    if submitted:
        # Remove the session state of submitted from full_names
        for name in full_names:
            session_state_status = st.session_state.get(f'status-{name}')
            if session_state_status is not None:
                st.session_state[f'status-{name}'] = False
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
            print('New Checkin data')
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

            # Mutate already checked-in for cache
            st.session_state[cache_name_checkin] = pd.concat(
                [
                    df_already_checkedin,
                    df_new_checkins,
                ]
            )
    
            results_container.success('Students checked in successfully!')
            results_container.write('Updated with new check-ins:')
            
        # Make sure we refresh to reflect changes
        refresh_time_secs = 2
        results_container.write(
            f'*Waiting {refresh_time_secs} seconds before refreshing page*'
        )
        # results_container.write(df_new_checkins)
        # Reset the what is displayed to be 'checked in'
        full_names = []
        time.sleep(refresh_time_secs)
        st.rerun()
        print('Never refreshed')