import streamlit as st
from supabase import create_client, Client
import hashlib
import pandas as pd
import plotly.express as px
import folium
import streamlit.components.v1 as components

# Supabase Credentials
SUPABASE_URL = "https://nffvzlszgyqokibmcjkt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mZnZ6bHN6Z3lxb2tpYm1jamt0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMwNDcxNTUsImV4cCI6MjA1ODYyMzE1NX0.aganbMyrxhVSONo6rVwFgCBxXSfNf7QuVmNJs3L7BRU"

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to create default Admin & Registrar accounts
def setup_users():
    users = [
        {"name": "Admin", "email": "admin@school.com", "password": hash_password("1234"), "role": "Admin"},
        {"name": "Registrar", "email": "registrar@school.com", "password": hash_password("1234"), "role": "Registrar"}
    ]

    for user in users:
        existing_user = supabase.table("users").select("*").eq("email", user["email"]).execute()
        if not existing_user.data:
            supabase.table("users").insert(user).execute()

setup_users()  # Ensure admin & registrar exist

# Function for user login
def login_user(email, password):
    hashed_pw = hash_password(password)
    response = supabase.table("users").select("*").eq("email", email).eq("password", hashed_pw).execute()
    return response.data[0] if response.data else None

# Function for new user admission (no role selection)
def admit_user(name, email, role="Applicant"):
    response = supabase.table("users").insert({
        "name": name,
        "email": email,
        "password": hash_password("password"),  # placeholder password, user will reset.
        "role": role,
    }).execute()
    return response.data if response.data else None

# Function to update user information
def update_user_info(user_id, name, email, role=None, student_type=None):
    update_data = {"name": name, "email": email}
    if role:
        update_data["role"] = role
    if student_type:
        update_data["student_type"] = student_type
    response = supabase.table("users").update(update_data).eq("id", user_id).execute()
    return response.data if response.data else None

# User Profile Display & Edit
def user_profile():
    st.subheader("User Profile")
    user = st.session_state.user

    new_name = st.text_input("Name", value=user["name"])
    new_email = st.text_input("Email", value=user["email"])

    if st.button("Update Profile", key="update_profile"):
        update_user_info(user["id"], new_name, new_email)
        st.success("Profile updated successfully!")
        st.rerun()

# Admin Dashboard
def admin_dashboard():
    st.title("Admin Dashboard 🛠️")
    st.write("Manage users in the system.")

    users = supabase.table("users").select("id, name, email, role").execute().data
    df = pd.DataFrame(users)

    st.dataframe(df)

    for u in users:
        if st.button(f"Delete {u['name']}", key=f"delete_{u['id']}"):
            supabase.table("users").delete().eq("id", u['id']).execute()
            st.rerun()

# Registrar Dashboard
def registrar_dashboard():
    st.title("Registrar Dashboard 📚")
    st.write("Manage student and professor records.")

    # Applicant List
    st.subheader("Applicant List")

    # Get all applicants
    response = supabase.table("users").select("id, name, email").eq("role", "Applicant").execute()
    applicants = response.data

    if not applicants:
        st.warning("No applicants found.")
        return

    df_all_applicants = pd.DataFrame(applicants)
    st.write("Columns in df_all_applicants:", df_all_applicants.columns)  # Debug

    # Fetch details for Freshmen and Returnee applicants
    try:
        freshmen_details_result = supabase.table("applicant_freshmen_details").select("*").in_("user_email", df_all_applicants["email"].tolist()).execute()
        freshmen_details = freshmen_details_result.data
    except KeyError as e:
        st.error(f"Error fetching freshmen details: {e}. Ensure 'email' column exists in applicant data.")
        return

    try:
        returnee_details = supabase.table("applicant_returnee_details").select("*").in_("user_email", df_all_applicants["email"].tolist()).execute().data
    except KeyError as e:
        st.error(f"Error fetching returnee details: {e}. Ensure 'email' column exists in applicant data.")
        return

    df_freshmen_details = pd.DataFrame(freshmen_details)
    df_returnee_details = pd.DataFrame(returnee_details)

    # Merge dataframes
    if df_freshmen_details.empty:
        st.warning("No freshmen applicant details found.")
        df_freshmen_merged = df_all_applicants  # skip merge
    elif 'user_email' not in df_freshmen_details.columns:
        st.error("Error: 'user_email' column not found in freshmen details.")
        return  # Stop execution if 'user_email' is missing
    else:
        try:
            df_freshmen_merged = pd.merge(df_all_applicants, df_freshmen_details, left_on="email",
                                          right_on="user_email", suffixes=('', '_freshmen'), how='left')
        except KeyError as e:
            st.error(f"Error during merge: {e}")
            return  # Stop execution if merge fails

    df_returnee_merged = pd.merge(df_all_applicants, df_returnee_details, left_on="email",
                                  right_on="user_email", suffixes=('', '_returnee'), how='left')

    # Combine dataframes with indicator for student type
    df_combined = pd.concat([df_freshmen_merged, df_returnee_merged], ignore_index=True)
    df_combined['student_type'] = df_combined['student_type'].fillna(
        df_combined['student_type_freshmen']).fillna(df_combined['student_type_returnee'])
    df_combined = df_combined.drop(['student_type_freshmen', 'student_type_returnee'], axis=1)

    # Search Bar
    search_term = st.text_input("Search Applicants", "")

    # Filter Data
    if search_term:
        df_combined = df_combined[df_combined.apply(
            lambda row: search_term.lower() in ' '.join(row.astype(str).values).lower(), axis=1)]

    # Display Combined Table
    st.dataframe(df_combined)

    df_combined['Admit as Student'] = False
    df_combined['Reject'] = False
    edited_df_combined = st.data_editor(
        df_combined,
        column_config={
            "Admit as Student": st.column_config.CheckboxColumn(
                "Admit as Student", help="Select to admit as student", default=False),
            "Reject": st.column_config.CheckboxColumn("Reject", help="Select to reject", default=False),
        },
        hide_index=True,
    )

    selected_admit_combined = edited_df_combined[edited_df_combined["Admit as Student"]]
    selected_reject_combined = edited_df_combined[edited_df_combined["Reject"]]

    if st.button("Process Applicants"):
        for index, row in selected_admit_combined.iterrows():
            update_user_info(row['id'], row['name'], row['email'], "Student", row['student_type'])
        for index, row in selected_reject_combined.iterrows():
            supabase.table("users").delete().eq("id", row['id']).execute()
        st.success("Applicants processed!")
        st.rerun()

def professor_management():
    st.subheader("Professor Management")
    professors = supabase.table("users").select("id, name, email").eq("role", "Professor").execute().data
    df = pd.DataFrame(professors)
    st.dataframe(df)

    for prof in professors:
        if st.button(f"Delete Professor {prof['name']}", key=f"delete_prof_{prof['id']}"):
            supabase.table("users").delete().eq("id", prof['id']).execute()
            st.rerun()
        if st.button(f"Edit Professor {prof['name']}", key=f"edit_prof_{prof['id']}"):
            edit_professor(prof["id"])

    st.subheader("Add Professor")
    prof_name = st.text_input("Professor Name")
    prof_email = st.text_input("Professor Email")
    prof_password = st.text_input("Professor Password", type="password")
    if st.button("Add Professor", key="add_prof"):
        admit_user(prof_name, prof_email, "Professor")
        st.success("Professor added!")
        st.rerun()

def edit_professor(user_id):
    prof_data = supabase.table("users").select("*").eq("id", user_id).execute().data[0]
    new_name = st.text_input("New Name", value=prof_data["name"])
    new_email = st.text_input("New Email", value=prof_data["email"])
    if st.button("Save Changes", key="save_prof_changes"):
        update_user_info(user_id, new_name, new_email, "Professor")
        st.success("Professor updated!")
        st.rerun()

def student_list():
    st.subheader("Current Student List")
    students = supabase.table("users").select("id, name, email").eq("role", "Student").execute().data
    df = pd.DataFrame(students)
    st.dataframe(df)

def add_subject():
    st.subheader("Add Subject")
    subject_id = st.text_input("Subject ID")
    subject_title = st.text_input("Subject Title")
    subject_description = st.text_input("Subject Description")
    department = st.text_input("Department")

    subjects = supabase.table("subjects").select("id, subject_title").execute().data
    prerequisite_options = {sub["subject_title"]: sub["id"] for sub in subjects}

    has_prerequisites = st.checkbox("Subject has prerequisites")

    selected_prerequisites = []
    if has_prerequisites:
        selected_prerequisites = st.multiselect("Prerequisite Subjects", options=prerequisite_options.keys())

    if st.button("Add Subject", key="add_subject_btn"):
        response = supabase.table("subjects").insert({
            "subject_id": subject_id,
            "subject_title": subject_title,
            "subject_description": subject_description,
            "department": department,
        }).execute()

        if response.data:
            new_subject_id = response.data[0]["id"]

            if has_prerequisites and selected_prerequisites:
                prerequisite_data = []
                for prereq_code in selected_prerequisites:
                    prereq_id = prerequisite_options[prereq_code]
                    prerequisite_data.append({"subject_id": new_subject_id, "prerequisite_id": prereq_id})
                supabase.table("prerequisites").insert(prerequisite_data).execute()

            st.success("Subject added successfully!")
            st.rerun()
        else:
            st.error("Failed to add subject.")

def subject_management():
    st.subheader("Subject Management")
    subjects = supabase.table("subjects").select("*").execute().data

    if subjects:
        df = pd.DataFrame(subjects)

        # Retrieve prerequisite information
        prerequisites = supabase.table("prerequisites").select("*").execute().data
        prereq_map = {}
        for prereq in prerequisites:
            if prereq["subject_id"] not in prereq_map:
                prereq_map[prereq["subject_id"]] = []
            prereq_map[prereq["subject_id"]].append(prereq["prerequisite_id"])

        # Create a dictionary to map subject IDs to titles
        subject_titles = {sub["id"]: sub["subject_title"] for sub in subjects}

        # Create a prerequisite string for each subject
        df["Prerequisites"] = df["id"].apply(
            lambda subject_id: ", ".join(
                [subject_titles[prereq_id] for prereq_id in prereq_map.get(subject_id, [])]
            )
        )

        df['Edit'] = False

        edited_df = st.data_editor(
            df,
            column_config={
                "Edit": st.column_config.CheckboxColumn(
                    "Edit",
                    help="Select to edit",
                    default=False,
                )
            },
            hide_index=True,
        )

        for index, row in edited_df[edited_df["Edit"]].iterrows():
            edit_subject(row["id"])
            break

    else:
        st.write("No subjects found.")

def edit_subject(subject_id):
    st.subheader("Edit Subject")
    response = supabase.table("subjects").select("*").eq("id", subject_id).execute()

    if response.data:
        edit_subject_data = response.data[0]
        print("Retrieved Data:", edit_subject_data)

        # Display the selected subject_id before editing
        st.write(f"Editing Subject ID: {edit_subject_data.get('subject_id', 'N/A')}")

        if "subject_id" in edit_subject_data:
            new_subject_id = st.text_input("New Subject ID", value=edit_subject_data["subject_id"])
        else:
            st.warning("Subject ID not found in database.")
            new_subject_id = st.text_input("New Subject ID", value="")

        if "subject_title" in edit_subject_data:
            new_subject_title = st.text_input("New Subject Title", value=edit_subject_data["subject_title"])
        else:
            st.warning("Subject Title not found in database.")
            new_subject_title = st.text_input("New Subject Title", value="")

        if "subject_description" in edit_subject_data:
            new_subject_description = st.text_input("New Subject Description",
                                                    value=edit_subject_data["subject_description"])
        else:
            st.warning("Subject Description not found in database.")
            new_subject_description = st.text_input("New Subject Description", value="")

        if st.button("Save Changes", key="save_subject_changes"):
            supabase.table("subjects").update({
                "subject_id": new_subject_id,
                "subject_title": new_subject_title,
                "subject_description": new_subject_description,
            }).eq("id", subject_id).execute()
            st.success("Subject updated!")
            st.rerun()

        if st.button("Delete Subject", key="delete_subject_from_edit"):
            # Delete prerequisites that reference this subject first
            supabase.table("prerequisites").delete().eq("subject_id", subject_id).execute()
            # Then delete the subject
            supabase.table("subjects").delete().eq("id", subject_id).execute()
            st.success("Subject and related prerequisites deleted!")
            st.rerun()

    else:
        st.error("Failed to retrieve subject data.")
        print("Supabase Error:", response.error)

# Student Dashboard
def student_dashboard():
    st.title("Student Dashboard 🎓")
    st.write(f"Welcome, {st.session_state.user['name']}!")

    # Example: Display student data using Plotly
    students = supabase.table("users").select("id, name, email").eq("role", "Student").execute().data
    df = pd.DataFrame(students)
    fig = px.bar(df, x="name", y="id", title="Student IDs")
    st.plotly_chart(fig)

    # Example: Display a map using Folium
    m = folium.Map(location=[37.7749, -122.4194], zoom_start=12)  # San Francisco coordinates
    folium.Marker([37.7749, -122.4194], popup="Student Location").add_to(m)
    st.components.v1.html(folium.Figure().add_child(m)._repr_html_(), width=700)

# User Icon & Profile Access (Top-Right)
def user_icon():
    with st.container():
        col1, col2 = st.columns([10, 1])
        with col2:
            if st.button("👤", key="user_icon"):
                st.session_state.show_profile = not st.session_state.show_profile

        if st.session_state.show_profile:
            with st.container():
                user_profile()

# Main Application
def main():
    st.set_page_config(page_title="School Management System", page_icon="🏫")

    # Initialize session state
    if "user" not in st.session_state:
        st.session_state.user = None
    if "show_profile" not in st.session_state:
        st.session_state.show_profile = False
    if "edit_subject_id" not in st.session_state:
        st.session_state.edit_subject_id = None
    if "consent_given" not in st.session_state:
        st.session_state.consent_given = False
    if "show_admission_form" not in st.session_state:
        st.session_state.show_admission_form = False
    if "admission_submitted" not in st.session_state:
        st.session_state.admission_submitted = False  # Track submission
    if "student_type" not in st.session_state:
        st.session_state.student_type = None

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    if st.session_state.user:
        user_icon()  # Display user icon if logged in
        if st.button("Logout", key="logout"):
            st.session_state.user = None
            st.rerun()
    else:
        choice = st.sidebar.radio("Go to", ["Login", "Admission"])

        if choice == "Login":
            st.subheader("User Login")
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            if st.button("Login", key="login"):
                user = login_user(email, password)
                if user:
                    st.session_state.user = user
                    st.success(f"Welcome {user['name']} ({user['role']})")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        elif choice == "Admission":
            consent_page()

        # Redirect to the correct dashboard based on role
    if st.session_state.user:
        role = st.session_state.user["role"]
        if role == "Admin":
            admin_dashboard()
        elif role == "Registrar":
            registrar_choice = st.sidebar.radio("Registrar Actions", ["Applicant List", "Professor Management", "Student List", "Add Subject", "Subject Management"])
            if registrar_choice == "Applicant List":
                registrar_dashboard()
            elif registrar_choice == "Professor Management":
                professor_management()
            elif registrar_choice == "Student List":
                student_list()
            elif registrar_choice == "Add Subject":
                add_subject()
            elif registrar_choice == "Subject Management":
                subject_management()
        elif role == "Student":
            student_dashboard()
        elif role == "Applicant":
            st.warning("Your application is under review.")

def consent_page():
    st.subheader("Data Privacy Policy Consent")
    st.write("DATA PRIVACY POLICY CONSENT")
    st.write("From School")
    st.write("I have read and understood all the provisions of the School Data Privacy Notice School and agree with its full implementation.")
    st.write("I hereby give my consent to School for the collection and processing of my personal data, relating to my Academic record, in accordance with the School Data Privacy Notice forSchool and in compliance with Republic Act 10173 or the Data Privacy Act of 2012 of the Republic of the Philippines, its implementing Rules and Regulations, and other guidelines and issuances by the National Privacy Commission.")
    consent = st.checkbox("I agree to the Data Privacy Policy.")

    if consent:
        st.session_state.consent_given = True
        student_type_selection() #Call student type selection

def student_type_selection():
    st.subheader("Select Student Type")
    student_type = st.radio("Student Type", ["Freshmen Student", "Returnee Student"])
    st.session_state.student_type = student_type
    admission_form() #Call admission form function

def admission_form():
    if st.session_state.student_type == "Freshmen Student":
        freshmen_form()
    elif st.session_state.student_type == "Returnee Student":
        returnee_form()

def freshmen_form():
    st.subheader("New Student Admission (Freshmen)")
    st.subheader("Personal Information")
    first_name = st.text_input("First Name", key="first_name_admission")
    middle_name = st.text_input("Middle Name (Optional)", key="middle_name_admission")
    last_name = st.text_input("Last Name", key="last_name_admission")
    suffix = st.text_input("Suffix (Optional)", key="suffix_admission")
    dob = st.date_input("Date of Birth", key="dob_admission")
    gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="gender_admission")
    citizenship = st.text_input("Citizenship", key="citizenship_admission")
    email = st.text_input("Email", key="email_admission")
    phone = st.text_input("Phone Number", key="phone_admission")
    address = st.text_area("Address", key="address_admission")

    st.subheader("Academic Information")
    last_school = st.text_input("Last School Attended", key="last_school_admission")
    year_graduated = st.number_input("Year Graduated", min_value=1900, max_value=2100, step=1, key="year_graduated_admission")
    academic_achievements = st.text_area("Academic Achievements", key="academic_achievements_admission")

    st.subheader("Guardian Information")
    guardian_name = st.text_input("Parent/Guardian Name", key="guardian_name_admission")
    guardian_phone = st.text_input("Contact Number", key="guardian_phone_admission")
    relationship = st.text_input("Relationship", key="relationship_admission")

    st.subheader("Documents for Upload")
    birth_certificate = st.file_uploader("Birth Certificate", type=["pdf", "png", "jpg", "jpeg"], key="birth_certificate_admission")
    report_card = st.file_uploader("Report Card/Transcript of Records", type=["pdf", "png", "jpg", "jpeg"], key="report_card_admission")
    good_moral = st.file_uploader("Certificate of Good Moral Character", type=["pdf", "png", "jpg", "jpeg"], key="good_moral_admission")

    if st.button("Register", key="admit"):
        # Validation: Check if all required fields are filled
        if not all([first_name, last_name, dob, gender, citizenship, email, phone, address,
                    last_school, year_graduated, academic_achievements,
                    guardian_name, guardian_phone, relationship,
                    birth_certificate, report_card, good_moral]):
            st.error("Please fill in all required fields and upload all documents.")
        else:
            # Construct the full name, handling optional parts correctly
            full_name_parts = [first_name, last_name, middle_name, suffix]
            full_name = " ".join(part for part in full_name_parts if part).strip()

            if admit_user(full_name, email, "Applicant"): #use full_name. change password to a placeholder, as user did not input password
                # Insert applicant details into the "applicant_details" table
                applicant_data = {
                    "user_email": email,  # Link to the user's email
                    "full_name": full_name, #use full_name
                    "date_of_birth": dob.strftime("%Y-%m-%d"),
                    "gender": gender,
                    "citizenship": citizenship,
                    "phone_number": phone,
                    "address": address,
                    "last_school_attended": last_school,
                    "year_graduated": year_graduated,
                    "academic_achievements":academic_achievements,
                    "guardian_name": guardian_name,
                    "guardian_phone": guardian_phone,
                    "relationship": relationship,
                    "student_type": "Freshmen Student",
                }
                supabase.table("applicant_freshmen_details").insert(applicant_data).execute()

                st.success("Registration successful! You can now log in.")
                st.session_state.show_admission_form = False
                st.session_state.admission_submitted = True #set to true after submission
            else:
                st.error("Email already exists. Try another one.")

def returnee_form():
    st.subheader("New Student Admission (Returnee)")
    st.subheader("Personal Information")
    first_name = st.text_input("First Name", key="first_name_returnee")
    middle_name = st.text_input("Middle Name (Optional)", key="middle_name_returnee")
    last_name = st.text_input("Last Name", key="last_name_returnee")
    suffix = st.text_input("Suffix (Optional)", key="suffix_returnee")
    dob = st.date_input("Date of Birth", key="dob_returnee")
    address = st.text_area("Current Address", key="address_returnee")

    st.subheader("Contact Details")
    phone = st.text_input("Phone Number", key="phone_returnee")
    email = st.text_input("Email", key="email_returnee")

    st.subheader("Academic Records (Upload Image)")
    tor = st.file_uploader("Transcript of Records (TOR)", type=["png", "jpg", "jpeg"], key="tor_returnee")
    last_enrollment = st.file_uploader("Certificate of Last Enrollment", type=["png", "jpg", "jpeg"], key="last_enrollment_returnee")
    clearance = st.file_uploader("Returnee Clearance Form", type=["png", "jpg", "jpeg"], key="clearance_returnee")
    good_moral = st.file_uploader("Good Moral Certificate", type=["png", "jpg", "jpeg"], key="good_moral_returnee")

    st.subheader("Old University Details")
    prev_univ_name = st.text_input("Name of Previous University", key="prev_univ_name_returnee")
    prev_univ_address = st.text_area("University Address", key="prev_univ_address_returnee")
    last_year_attended = st.number_input("Last Year Attended", min_value=1900, max_value=2100, step=1, key="last_year_attended_returnee")
    course = st.text_input("Course/Program Enrolled", key="course_returnee")
    semesters_completed = st.number_input("Number of Semesters Completed", min_value=1, step=1, key="semesters_completed_returnee")

    reason_options = ["Academic Break", "Financial Reasons", "Transferring to Another University", "Medical Leave", "Other Personal Reasons"]
    reason_leaving = st.selectbox("Reason for Leaving", reason_options, key="reason_leaving_returnee")

    if st.button("Register", key="admit_returnee"):
        if not all([first_name, last_name, dob, address, phone, email, tor, last_enrollment, clearance, good_moral, prev_univ_name, prev_univ_address, last_year_attended, course, semesters_completed, reason_leaving]):
            st.error("Please fill in all required fields and upload all documents.")
        else:
            full_name_parts = [first_name, last_name, middle_name, suffix]
            full_name = " ".join(part for part in full_name_parts if part).strip()

            if admit_user(full_name, email, "password", role="Applicant"):
                applicant_data = {
                    "user_email": email,
                    "full_name": full_name,
                    "date_of_birth": dob.strftime("%Y-%m-%d"),
                    "phone_number": phone,
                    "address": address,
                    "previous_university_name": prev_univ_name,
                    "previous_university_address": prev_univ_address,
                    "last_year_attended": last_year_attended,
                    "course_program_enrolled": course,
                    "semesters_completed": semesters_completed,
                    "reason_leaving": reason_leaving,
                    "student_type": st.session_state.student_type,
                }
                supabase.table("applicant_details").insert(applicant_data).execute()

                st.success("Registration successful! You can now log in.")
                st.session_state.show_admission_form = False
                st.session_state.admission_submitted = True
            else:
                st.error("Email already exists. Try another one.")

if __name__ == "__main__":
    main()