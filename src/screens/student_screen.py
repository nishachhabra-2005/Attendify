
import streamlit as st

from src.ui.base_layout import style_background_dashboard, style_base_layout

from src.components.header import header_dashboard

from PIL import Image
import numpy as np
from src.pipelines.face_pipeline import predict_attendance, get_face_embeddings, train_classifier
from src.pipelines.voice_pipeline import get_voice_embedding
from src.database.db import get_all_students, create_student, get_student_subjects, get_student_attendance, unenroll_student_to_subject
import time

from src.components.dialog_enroll import enroll_dialog
from src.components.subject_card import subject_card


def student_dashboard():
    student_data = st.session_state.student_data
    student_id = student_data['student_id']

    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')

    with c1:
        header_dashboard()

    with c2:
        st.subheader(f"Welcome, {student_data['name']}")

        if st.button("Logout", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.student_data
            st.rerun()

    st.space()

    # Fetch student subjects and attendance
    with st.spinner('Loading your attendance data...'):
        subjects = get_student_subjects(student_id) or []
        logs = get_student_attendance(student_id) or []

    # --------------------------------------------------
    # Calculate subject-wise attendance
    # --------------------------------------------------

    stats_map = {}

    for log in logs:
        sid = log.get('subject_id')
        status = log.get('is_present')

        # Count only records with an explicit attendance status
        if status is not True and status is not False:
            continue

        if sid not in stats_map:
            stats_map[sid] = {
                "total": 0,
                "attended": 0,
                "absent": 0,
                "logs": []
            }

        stats_map[sid]["total"] += 1

        if status is True:
            stats_map[sid]["attended"] += 1
        else:
            stats_map[sid]["absent"] += 1

        stats_map[sid]["logs"].append(log)

    # --------------------------------------------------
    # Overall attendance
    # --------------------------------------------------

    overall_total = 0
    overall_attended = 0
    overall_absent = 0

    for sub_node in subjects:
        sub = sub_node.get('subjects')

        if isinstance(sub, list):
            sub = sub[0] if sub else None

        if not sub:
            continue

        sid = sub.get('subject_id')
        stats = stats_map.get(
            sid,
            {"total": 0, "attended": 0, "absent": 0, "logs": []}
        )

        overall_total += stats["total"]
        overall_attended += stats["attended"]
        overall_absent += stats["absent"]

    overall_percentage = (
        (overall_attended / overall_total) * 100
        if overall_total > 0 else None
    )

    # --------------------------------------------------
    # Dashboard heading
    # --------------------------------------------------

    st.divider()

    st.header("Your Attendance Overview")
    st.caption("Track your attendance performance across all enrolled subjects.")

    # --------------------------------------------------
    # Overall attendance metrics
    # --------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Overall Attendance",
            f"{overall_percentage:.2f}%" if overall_percentage is not None else "N/A"
        )

    with c2:
        st.metric("Total Classes", overall_total)

    with c3:
        st.metric("Classes Attended", overall_attended)

    with c4:
        st.metric("Classes Missed", overall_absent)

    if overall_percentage is not None:
        st.progress(
            min(overall_percentage / 100, 1.0),
            text=f"Overall Attendance: {overall_percentage:.2f}%"
        )

        if overall_percentage < 75:
            st.warning(
                "Your overall attendance is below 75%. "
                "You should attend upcoming classes regularly."
            )
        else:
            st.success("Your overall attendance is at or above 75%.")

    else:
        st.info("Your attendance will appear here once classes are recorded.")

    # --------------------------------------------------
    # Enrolled subjects
    # --------------------------------------------------

    st.divider()

    c1, c2 = st.columns(2)

    with c1:
        st.header('Your Enrolled Subjects')

    with c2:
        if st.button('Enroll in Subject', type='primary', width='stretch'):
            enroll_dialog()

    st.caption("Your attendance statistics for each enrolled subject.")

    # --------------------------------------------------
    # Subject-wise attendance cards
    # --------------------------------------------------

    if not subjects:
        st.info("You are not enrolled in any subjects yet.")

    cols = st.columns(2)

    for i, sub_node in enumerate(subjects):

        sub = sub_node.get('subjects')

        if isinstance(sub, list):
            sub = sub[0] if sub else None

        if not sub:
            continue

        sid = sub['subject_id']

        stats = stats_map.get(
            sid,
            {"total": 0, "attended": 0, "absent": 0, "logs": []}
        )

        total = stats["total"]
        attended = stats["attended"]
        absent = stats["absent"]

        percentage = (
            (attended / total) * 100
            if total > 0 else None
        )

        # Calculate classes needed to reach 75%
        if percentage is not None and percentage < 75:
            classes_needed = max(0, (3 * total) - (4 * attended))
        else:
            classes_needed = 0

        def unenroll_button(
            student_id=student_id,
            sid=sid,
            subject_name=sub.get('name', 'Subject')
        ):
            if st.button(
                "Unenroll from this course",
                type="tertiary",
                width="stretch",
                icon=":material/delete_forever:",
                key=f"unenroll_{student_id}_{sid}"
            ):
                unenroll_student_to_subject(student_id, sid)
                st.toast(f"Unenrolled from {subject_name} successfully!")
                st.rerun()

        with cols[i % 2]:

            subject_card(
                name=sub.get('name', 'Unknown Subject'),
                code=sub.get('subject_code', 'N/A'),
                section=sub.get('section', 'N/A'),
                stats=[
                    ('📅', 'Total', total),
                    ('✅', 'Attended', attended),
                ],
                footer_callback=unenroll_button
            )

            # Detailed attendance section
            with st.expander(
                f"View {sub.get('name', 'Subject')} Attendance Details"
            ):

                st.subheader("Attendance Performance")

                if percentage is None:
                    st.info("No attendance records available for this subject yet.")

                else:
                    st.metric(
                        "Attendance Percentage",
                        f"{percentage:.2f}%"
                    )

                    st.progress(
                        min(percentage / 100, 1.0),
                        text=f"{percentage:.2f}% attendance"
                    )

                    m1, m2, m3 = st.columns(3)

                    m1.metric("Total Classes", total)
                    m2.metric("Present", attended)
                    m3.metric("Absent", absent)

                    if percentage < 75:
                        st.error(
                            f"Attendance below 75%! "
                            f"You need to attend the next {classes_needed} "
                            f"consecutive classes without absence to reach 75%."
                        )

                    else:
                        st.success("You have maintained the required 75% attendance.")

                    st.divider()

                    st.subheader("Attendance History")

                    history = stats["logs"]

                    if history:
                        for record in reversed(history):

                            timestamp = record.get('timestamp', 'Date unavailable')
                            status = record.get('is_present')

                            if status is True:
                                st.success(f"✅ Present — {timestamp}")

                            elif status is False:
                                st.error(f"❌ Absent — {timestamp}")

                    else:
                        st.info("No attendance history available.")

    st.divider()


def student_screen():

    style_background_dashboard()
    style_base_layout()

    if "student_data" in st.session_state:
        student_dashboard()
        return

    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')

    with c1:
        header_dashboard()

    
    with c2:
     st.subheader(f"Welcome, {student_data['name']}")

     if st.button(
        "← Back to Home",
        type='secondary',
        key='student_home_button',
        shortcut="control+backspace",
        width='stretch'
    ):
        st.session_state['login_type'] = None
        st.session_state['is_logged_in'] = False
        st.session_state['user_role'] = None

        st.session_state.pop('student_data', None)

        st.rerun()


    st.header('Login using FaceID', text_alignment='center')
    st.space()
    st.space()

    show_registration = False

    photo_source = st.camera_input("Position your face in the center")

    if photo_source:

        img = np.array(Image.open(photo_source))

        with st.spinner('AI is scanning..'):

            detected, all_ids, num_faces = predict_attendance(img)

            if num_faces == 0:
                st.warning('Face not found!')

            elif num_faces > 1:
                st.warning('Multiple faces found')

            else:

                if detected:

                    student_id = list(detected.keys())[0]

                    all_students = get_all_students()

                    student = next(
                        (s for s in all_students if s['student_id'] == student_id),
                        None
                    )

                    if student:

                        st.session_state.is_logged_in = True
                        st.session_state.user_role = 'student'
                        st.session_state.student_data = student

                        st.toast(f"Welcome Back {student['name']}")

                        time.sleep(1)
                        st.rerun()

                else:

                    st.info(
                        'Face not recognized! You might be a new student!'
                    )

                    show_registration = True

    if show_registration:

        with st.container(border=True):

            st.header('Register new Profile')

            new_name = st.text_input(
                "Enter your name",
                placeholder='E.g. Hamza Rizvi'
            )

            st.subheader('Optional : Voice Enrollment')

            st.info("Enroll your for voice only attendance")

            audio_data = None

            try:
                audio_data = st.audio_input(
                    'Record a short phrase like I am present, My name is Akash.'
                )

            except Exception:
                st.error('Audio Data failed!')

            if st.button('Create Account', type='primary'):

                if new_name:

                    with st.spinner('Creating profile..'):

                        img = np.array(Image.open(photo_source))

                        encodings = get_face_embeddings(img)

                        if encodings:

                            face_emb = encodings[0].tolist()

                            voice_emb = None

                            if audio_data:
                                voice_emb = get_voice_embedding(audio_data.read())

                            response_data = create_student(
                                new_name,
                                face_embedding=face_emb,
                                voice_embedding=voice_emb
                            )

                            if response_data:

                                train_classifier()

                                st.session_state.is_logged_in = True
                                st.session_state.user_role = 'student'
                                st.session_state.student_data = response_data[0]

                                st.toast(f'Profile Created! Hi {new_name}!')

                                time.sleep(1)
                                st.rerun()

                        else:
                            st.error(
                                'Couldnt capture your facial features for registration'
                            )

                else:
                    st.warning('Please enter your name!')




        
    