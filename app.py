import datetime
import streamlit as st
import pandas as pd
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection
import time



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
    cache_ttl_secs: float = 30,
) -> pd.DataFrame:
    """Gets the students already checked in via a data source

    Args:        
        cache_ttl_secs: How long to cache the data for.
        name: The name of the connection.
        conn: Connection to be used.
    Returns:
        pd.DataFrame: The students already checked in.
    """
    # Create a connection object for the data base

    df = conn.read(
        ttl=cache_ttl_secs,
    )
    return df

conn_to_gsheet = create_connection(
    name='gsheets',
    conn_type=GSheetsConnection,
    cache_ttl_secs=0,
)
df_already_checkedin = get_already_checked_in_students(
    conn=conn_to_gsheet,
    cache_ttl_secs=0,
)

############

st.title('Sign In Form')

# Collapsible section to display students already checked in
with st.expander('Students already checked in'):
    search_term = st.text_input('Filter by name:')
    if search_term:
        filtered_names = df_already_checkedin[
            df_already_checkedin['LastName'].str.contains(search_term, case=False)
            | df_already_checkedin['FirstName'].str.contains(search_term, case=False)
        ]
        st.dataframe(filtered_names)
    # Print results.
    st.dataframe(df_already_checkedin)

st.subheader('Check in Students')
st.write(
    'Select student names to be checked in'
)

names = pd.read_csv('names.csv').sort_values(by='LastName')

last_name_letters = sorted(names['LastName'].str[0].unique())
options = last_name_letters
filter_selection = st.pills(
    'Display',
    options,
    default=options,
    selection_mode='multi',
)

results_container = st.container()


# Override time option they were checked in. Defaults to current time
is_override = st.checkbox('Override Time')
override_checkin_time = None

with st.form(key='my_form'):
    submitted = st.form_submit_button('Check In')

    
    if is_override:
        now = datetime.datetime.now()
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
        if letter not in filter_selection:
            continue
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
                # Include when checked in
                time_checkedin = (
                    df_already_checkedin
                    [df_already_checkedin['FullName'] == name]
                    ["SubmitTime"]
                    .values[0]
                    # .loc[0]
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
            # Convert submitTime to a string (HH:MM:SS)
            student_data['SubmitTime'] = (
                submit_time.strftime('%H:%M:%S')
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

            results_df = write_to_data_store(
                conn=conn_to_gsheet,
                data=merged_df,
            )

            results_container.write('Updated with new checkins:')
            # Make sure we refresh to reflect changes
            refresh_time_secs = 15
            results_container.write(
                f'*Waiting {refresh_time_secs} seconds before refreshing page*'
            )
            results_container.write(results_df)
            time.sleep(refresh_time_secs)
            st.rerun(scope='app')
