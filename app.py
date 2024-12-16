import streamlit as st


pages = {
    'Checkin/Checkout': [
        st.Page(
            page='checkin.py',
            title='Check In Students',
            icon=':material/check_circle:',
        ),
        st.Page(
            page='checkout.py',
            title='Check Out Students',
            icon=':material/cancel:',
        ),
    ],
    'Admin': [
        st.Page(
            page='current.py',
            title='Students in the Nest',
            # icon=':material/manage_search:',
            icon=':material/checklist:',
        ),
        st.Page(
            page='month.py',
            title='Month Aggregations',
            icon=':material/calendar_today:',
        )
    ]
}

pg = st.navigation(
    pages=pages,
)

pg.run()