import datetime
import streamlit as st
import pandas as pd
from zoneinfo import ZoneInfo
from streamlit_gsheets import GSheetsConnection



st.title('Sign In Form')

def get_already_checked_in_students(
    cache_ttl_secs: float = 30,
    name: str = 'gsheets',
    conn_type = GSheetsConnection,
) -> pd.DataFrame:
    """Gets the students already checked in via a data source

    Args:        
        cache_ttl_secs: How long to cache the data for.
        name: The name of the connection.
        conn_type: The type of connection to be used.
    Returns:
        pd.DataFrame: The students already checked in.
    """
    # Create a connection object for the data base
    conn = st.connection(
        name=name,
        type=conn_type,
        ttl=cache_ttl_secs,
    )

    df = conn.read(
        ttl=cache_ttl_secs,
    )
    return df

df_already_checkedin = get_already_checked_in_students()


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
st.markdown(f'Your selected options: {filter_selection}.')

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
            student_checked = col.checkbox(
                label=label_info,
                key=name,
                value=is_already_checked_in,
                disabled=is_already_checked_in,
            )
            # Only need to track students already checked in
            if not is_already_checked_in:
                all_names[name] = student_checked
        st.divider()
    
    if submitted:
        # Track time of actual submission
        submit_time = datetime.datetime.now().time()
        st.write(f'Submitted on {submit_time} ')
        st.write(f'{override_checkin_time}')
        for name, checkedin in all_names.items():
            if checkedin:
                info = names[names['FullName'] == name]
                st.write(f'{name} checked in (grade {info["Grade"].values[0]})')



