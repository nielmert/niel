import streamlit as st

class User:
    def __init__(self, username, role):
        self.username = username
        self.role = role

class Student(User):
    def __init__(self, username):
        super().__init__(username, "student")
        self.assignments = {}

    def view_assignments(self):
        return self.assignments

    def submit_assignment(self, assignment_name, submission):
        if assignment_name in self.assignments and self.assignments[assignment_name]["status"] == "pending":
            self.assignments[assignment_name]["status"] = "submitted"
            self.assignments[assignment_name]["submission"] = submission
            return True
        else:
            return False

    def view_grades(self):
        grades = {}
        for assignment, details in self.assignments.items():
            if "grade" in details:
                grades[assignment] = details["grade"]
        return grades

class Professor(User):
    def __init__(self, username):
        super().__init__(username, "professor")

    def create_assignment(self, assignment_name, students, student_list):
        for student_username in students:
            found = False
            for student in student_list:
                if student.username == student_username:
                    student.assignments[assignment_name] = {"status": "pending", "submission": None}
                    found = True
                    break
            if not found:
                st.error(f"Student '{student_username}' not found.")
                return False
        return True

    def add_grade(self, student_username, assignment_name, grade, student_list):
        for student in student_list:
            if student.username == student_username:
                if assignment_name in student.assignments:
                    student.assignments[assignment_name]["grade"] = grade
                    return True
                else:
                    return False
        return False

    def add_comment(self, student_username, assignment_name, comment, student_list):
        for student in student_list:
            if student.username == student_username:
                if assignment_name in student.assignments:
                    student.assignments[assignment_name]["comment"] = comment
                    return True
                else:
                    return False
        return False

class Principal(User):
    def __init__(self, username):
        super().__init__(username, "principal")
        self.school_report = ""

    def set_school_report(self, report):
        self.school_report = report

    def get_school_report(self):
        return self.school_report

def main():
    if 'users' not in st.session_state:
        st.session_state.users = {}
    if 'student_list' not in st.session_state:
        st.session_state.student_list = []
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'principal_mode' not in st.session_state:
        st.session_state.principal_mode = False

    st.set_page_config(page_title="University Portal", page_icon="🎓")
    st.title("🎓 University Portal")

    if not st.session_state.logged_in and not st.session_state.principal_mode:
        login_ui()
    else:
        app_ui()

def login_ui():
    st.header("Login / Create Account")
    username = st.text_input("Username:")
    role = st.selectbox("Role:", ["student", "professor"])
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Login"):
            if username in st.session_state.users and st.session_state.users[username].role == role:
                st.session_state.logged_in = True
                st.session_state.current_user = st.session_state.users[username]
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Invalid username or role.")
    with col2:
        if st.button("Create Account"):
            if username and role:
                if username not in st.session_state.users:
                    if role == "student":
                        new_student = Student(username)
                        st.session_state.users[username] = new_student
                        st.session_state.student_list.append(new_student)
                    else:
                        st.session_state.users[username] = Professor(username)
                    st.success("Account created successfully. Please log in.")
                else:
                    st.error("Username already exists.")
            else:
                st.error("Please enter username and select role.")
    with col3:
        if st.button("Enter Principal Mode"):
            st.session_state.principal_mode = True
            st.session_state.current_user = Principal("Principal")
            st.rerun()

def app_ui():
    with st.sidebar:
        if st.session_state.principal_mode:
            principal_actions = ["View All", "Set School Report", "View School Report", "Edit/Delete User"]
            principal_action = st.selectbox("Principal Actions:", principal_actions)
            st.session_state.principal_action = principal_action
        elif st.session_state.current_user.role == "student":
            student_actions = ["View Assignments", "Submit Assignment", "View Grades"]
            student_action = st.selectbox("Student Actions:", student_actions)
            st.session_state.student_action = student_action
        elif st.session_state.current_user.role == "professor":
            professor_actions = ["Add Assignment", "Add Grades", "Add Comments"]
            professor_action = st.selectbox("Professor Actions:", professor_actions)
            st.session_state.professor_action = professor_action

        if not st.session_state.principal_mode and st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        if st.session_state.principal_mode and st.button("Exit Principal Mode"):
            st.session_state.principal_mode = False
            st.rerun()

    if st.session_state.principal_mode:
        principal_ui()
    elif st.session_state.current_user.role == "student":
        student_ui()
    elif st.session_state.current_user.role == "professor":
        professor_ui()

def student_ui():
    student = st.session_state.current_user

    st.header("Student Dashboard")
    if st.session_state.student_action == "View Assignments":
        st.subheader("View Assignments")
        assignments = student.view_assignments()
        if assignments:
            for assignment, details in assignments.items():
                st.write(f"**{assignment}**: {details['status']}")
        else:
            st.info("No assignments found.")

    elif st.session_state.student_action == "Submit Assignment":
        st.subheader("Submit Assignment")
        assignments = student.view_assignments()
        if assignments:
            assignment_name = st.selectbox("Select Assignment:", list(assignments.keys()))
            submission = st.text_area("Submission:")
            if st.button("Submit"):
                if student.submit_assignment(assignment_name, submission):
                    st.success(f"Assignment '{assignment_name}' submitted.")
                else:
                    st.error("Error submitting assignment.")
        else:
            st.info("No assignments found.")

    elif st.session_state.student_action == "View Grades":
        st.subheader("View Grades")
        grades = student.view_grades()
        if grades:
            for assignment, grade in grades.items():
                st.write(f"**{assignment}**: {grade}")
        else:
            st.info("No grades available.")

def professor_ui():
    professor = st.session_state.current_user
    st.header("Professor Dashboard")

    if st.session_state.professor_action == "Add Assignment":
        st.subheader("Add Assignment")
        assignment_name = st.text_input("Assignment Name:")
        student_usernames = st.text_area("Student Usernames (comma-separated):")
        student_usernames = [name.strip() for name in student_usernames.split(",")]
        if st.button("Add Assignment"):
            if professor.create_assignment(assignment_name, student_usernames, st.session_state.student_list):
                st.success(f"Assignment '{assignment_name}' created.")

    elif st.session_state.professor_action == "Add Grades":
        st.subheader("Add Grades")
        student_username = st.text_input("Student Username:")
        assignments = []
        for student in st.session_state.student_list:
            if student.username == student_username:
                assignments = list(student.assignments.keys())
                break

        if assignments:
            assignment_name = st.selectbox("Select Assignment:", assignments)
            grade = st.number_input("Grade:", min_value=0, max_value=100)
            if st.button("Add Grade"):
                if professor.add_grade(student_username, assignment_name, grade, st.session_state.student_list):
                    st.success(f"Grade added for {student_username} - {assignment_name}.")
                else:
                    st.error("Error adding grade.")
        else:
            st.info("Student or assignments not found.")

    elif st.session_state.professor_action == "Add Comments":
        st.subheader("Add Comments")
        student_username = st.text_input("Student Username:")
        assignments = []
        for student in st.session_state.student_list:
            if student.username == student_username:
                assignments = list(student.assignments.keys())
                break
        if assignments:
            assignment_name = st.selectbox("Select Assignment:", assignments)
            comment = st.text_area("Comment:")
            if st.button("Add Comment"):
                if professor.add_comment(student_username, assignment_name, comment, st.session_state.student_list):
                    st.success(f"Comment added for {student_username} - {assignment_name}.")
                else:
                    st.error("Error adding comment.")
        else:
            st.info("Student or assignments not found.")

def principal_ui():
    principal = st.session_state.current_user
    st.header("Principal Dashboard")

    if st.session_state.principal_action == "View All":
        st.subheader("View All Users and Assignments")
        st.write("**All Users:**")
        for username, user in st.session_state.users.items():
            st.write(f"- {username} ({user.role})")
        st.write("**All Students Assignments and Comments:**")
        for student in st.session_state.student_list:
            st.write(f"**{student.username}:**")
            for assignment, details in student.assignments.items():
                st.write(f"- {assignment}: {details}")
                if "comment" in details:
                    st.write(f"  - Comment: {details['comment']}")

    elif st.session_state.principal_action == "Set School Report":
        st.subheader("Set School Report")
        report = st.text_area("School Report:")
        if st.button("Set Report"):
            principal.set_school_report(report)
            st.success("School report set.")

    elif st.session_state.principal_action == "View School Report":
        st.subheader("View School Report")
        report = principal.get_school_report()
        if report:
            st.write("**School Report:**")
            st.write(report)
        else:
            st.info("No school report set.")

    elif st.session_state.principal_action == "Edit/Delete User":
        st.subheader("Edit/Delete User")
        username_to_edit = st.selectbox("Select User to Edit/Delete:", list(st.session_state.users.keys()))
        if username_to_edit:
            user_to_edit = st.session_state.users[username_to_edit]
            st.write(f"**Username:** {user_to_edit.username}")
            st.write(f"**Role:** {user_to_edit.role}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Delete User"):
                    del st.session_state.users[username_to_edit]
                    if user_to_edit.role == "student":
                        st.session_state.student_list = [s for s in st.session_state.student_list if s.username != username_to_edit]
                    st.success(f"User '{username_to_edit}' deleted.")
                    st.rerun()
            with col2:
                new_role = st.selectbox("Change Role:", ["student", "professor"], index=["student", "professor"].index(user_to_edit.role))
                if st.button("Change Role"):
                    if user_to_edit.role != new_role:
                        if new_role == "student" and user_to_edit.role == "professor":
                            st.session_state.users[username_to_edit] = Student(username_to_edit)
                            st.session_state.student_list.append(st.session_state.users[username_to_edit])
                        elif new_role == "professor" and user_to_edit.role == "student":
                            st.session_state.users[username_to_edit] = Professor(username_to_edit)
                            st.session_state.student_list = [s for s in st.session_state.student_list if s.username != username_to_edit]

                        st.session_state.users[username_to_edit].role = new_role
                        st.success(f"Role of '{username_to_edit}' changed to {new_role}.")
                        st.rerun()

if __name__ == "__main__":
    main()