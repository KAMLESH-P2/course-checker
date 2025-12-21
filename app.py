import streamlit as st
import pdfplumber
from datetime import datetime, time
import re
from itertools import product

# Page config
st.set_page_config(page_title="Auto Course Scheduler", page_icon="📚", layout="wide")

# Title
st.title("📚 Automatic Course Scheduler")
st.write("Select courses and teachers - we'll build a conflict-free schedule for you!")

# Course class
class Course:
    def __init__(self, code, name, section, instructor, dates, schedule, credits):
        self.code = code
        self.name = name
        self.section = section
        self.instructor = instructor
        self.dates = dates
        self.schedule = schedule
        self.credits = credits

def parse_time(time_str):
    """Convert time string to time object"""
    try:
        time_str = time_str.strip()
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    except:
        return None

def extract_courses_from_pdf(pdf_file):
    """Extract course information from PDF"""
    courses = []
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
    
    course_blocks = re.split(r'(\d{2}[A-Z]{2}\d{3})', full_text)
    
    current_code = None
    current_name = None
    current_credits = None
    
    for i, block in enumerate(course_blocks):
        if re.match(r'\d{2}[A-Z]{2}\d{3}', block):
            current_code = block
            
            if i + 1 < len(course_blocks):
                details = course_blocks[i + 1]
                
                credit_match = re.search(r'\[(\d+)\s*Credits\]', details)
                if credit_match:
                    current_credits = int(credit_match.group(1))
                
                name_match = re.search(r'Course overview\s+(.+?)(?=\n|$)', details)
                if name_match:
                    current_name = name_match.group(1).strip()
                
                section_pattern = r'([\w-]+),\s*(\w+)\s*-\s*(.+?)\s+Date:\s*(\d{2}-\d{2}-\d{4})\s*to\s*(\d{2}-\d{2}-\d{4})'
                sections = re.finditer(section_pattern, details)
                
                for section_match in sections:
                    section = section_match.group(1)
                    instructor = section_match.group(3)
                    start_date = section_match.group(4)
                    end_date = section_match.group(5)
                    
                    section_end = details.find('No. of attempts:', section_match.end())
                    if section_end == -1:
                        section_end = len(details)
                    
                    section_text = details[section_match.end():section_end]
                    
                    schedule = []
                    schedule_lines = section_text.strip().split('\n')
                    
                    for line in schedule_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        day_match = re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday):\s*(.+)', line)
                        if day_match:
                            day = day_match.group(1)
                            times_str = day_match.group(2)
                            time_ranges = re.findall(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', times_str)
                            
                            for start, end in time_ranges:
                                schedule.append({
                                    'day': day,
                                    'start': start,
                                    'end': end
                                })
                    
                    if schedule:
                        course = Course(
                            code=current_code,
                            name=current_name or "Unknown",
                            section=section,
                            instructor=instructor,
                            dates=f"{start_date} to {end_date}",
                            schedule=schedule,
                            credits=current_credits or 0
                        )
                        courses.append(course)
    
    return courses

def check_time_overlap(slot1, slot2):
    """Check if two time slots overlap"""
    start1 = parse_time(slot1['start'])
    end1 = parse_time(slot1['end'])
    start2 = parse_time(slot2['start'])
    end2 = parse_time(slot2['end'])
    
    if all([start1, end1, start2, end2]):
        return start1 < end2 and start2 < end1
    return False

def has_conflict(course1, course2):
    """Check if two courses have any time conflict"""
    for slot1 in course1.schedule:
        for slot2 in course2.schedule:
            if slot1['day'] == slot2['day']:
                if check_time_overlap(slot1, slot2):
                    return True
    return False

def find_best_schedule(course_sections_dict):
    """
    Automatically find a conflict-free schedule
    course_sections_dict: {course_code: [list of course objects]}
    """
    # Get all possible combinations
    course_codes = list(course_sections_dict.keys())
    all_sections = [course_sections_dict[code] for code in course_codes]
    
    # Try all combinations
    for combination in product(*all_sections):
        # Check if this combination has conflicts
        has_any_conflict = False
        for i in range(len(combination)):
            for j in range(i + 1, len(combination)):
                if has_conflict(combination[i], combination[j]):
                    has_any_conflict = True
                    break
            if has_any_conflict:
                break
        
        # If no conflicts, return this schedule
        if not has_any_conflict:
            return list(combination)
    
    return None

# File uploader
uploaded_file = st.file_uploader("Upload your course timetable (PDF)", type=['pdf'])

if uploaded_file:
    with st.spinner("Extracting courses from PDF..."):
        all_courses = extract_courses_from_pdf(uploaded_file)
    
    if all_courses:
        st.success(f"✅ Found {len(all_courses)} course sections!")
        
        # Group courses by code
        courses_by_code = {}
        for course in all_courses:
            if course.code not in courses_by_code:
                courses_by_code[course.code] = []
            courses_by_code[course.code].append(course)
        
        # Step 1: Select Courses
        st.header("Step 1: Select Courses")
        st.write("Choose which courses you want to take:")
        
        selected_course_codes = []
        
        cols = st.columns(3)
        for idx, code in enumerate(sorted(courses_by_code.keys())):
            first_course = courses_by_code[code][0]
            with cols[idx % 3]:
                if st.checkbox(
                    f"**{code}**\n{first_course.name}\n({first_course.credits} credits)",
                    key=f"course_{code}"
                ):
                    selected_course_codes.append(code)
        
        if selected_course_codes:
            st.success(f"Selected {len(selected_course_codes)} courses")
            
            # Step 2: Select Leave Days
            st.header("Step 2: Select Leave Days (Optional)")
            st.write("Choose days you want off - no classes will be scheduled on these days.")
            
            leave_days = []
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Select Days Off:**")
                if st.checkbox("Monday", key="leave_monday"):
                    leave_days.append("Monday")
                if st.checkbox("Tuesday", key="leave_tuesday"):
                    leave_days.append("Tuesday")
                if st.checkbox("Wednesday", key="leave_wednesday"):
                    leave_days.append("Wednesday")
                if st.checkbox("Thursday", key="leave_thursday"):
                    leave_days.append("Thursday")
            
            with col2:
                st.write("** **")  # Spacer
                if st.checkbox("Friday", key="leave_friday"):
                    leave_days.append("Friday")
                if st.checkbox("Saturday", key="leave_saturday"):
                    leave_days.append("Saturday")
                if st.checkbox("Sunday", key="leave_sunday"):
                    leave_days.append("Sunday")
            
            if leave_days:
                st.info(f"🏖️ Days off: {', '.join(leave_days)}")
            else:
                st.success("✅ No leave days - all days available for classes")
            
            # Step 3: Select Teachers
            st.header("Step 3: Select Preferred Teachers (Optional)")
            st.write("Choose teachers for each course. Leave blank to consider all teachers.")
            
            teacher_preferences = {}
            
            for code in selected_course_codes:
                sections = courses_by_code[code]
                instructors = list(set([s.instructor for s in sections]))
                
                with st.expander(f"{code} - {sections[0].name}"):
                    st.write(f"Available teachers: **{len(instructors)}**")
                    
                    selected_teachers = []
                    for instructor in instructors:
                        if st.checkbox(
                            f"👤 {instructor}",
                            key=f"teacher_{code}_{instructor}",
                            value=True  # Select all by default
                        ):
                            selected_teachers.append(instructor)
                    
                    if selected_teachers:
                        teacher_preferences[code] = selected_teachers
            
            # Step 4: Generate Schedule
            st.header("Step 4: Generate Your Schedule")
            
            if st.button("🎯 Generate Conflict-Free Schedule", type="primary", use_container_width=True):
                
                with st.spinner("Finding the best schedule for you..."):
                    # Filter sections based on teacher preferences AND leave days
                    filtered_sections = {}
                    for code in selected_course_codes:
                        filtered_sections[code] = []
                        for course in courses_by_code[code]:
                            # Check if course has classes on leave days
                            has_class_on_leave = False
                            if leave_days:
                                for slot in course.schedule:
                                    if slot['day'] in leave_days:
                                        has_class_on_leave = True
                                        break
                            
                            # Skip this section if it has classes on leave days
                            if has_class_on_leave:
                                continue
                            
                            # If teacher preferences exist, filter by them
                            if code in teacher_preferences:
                                if course.instructor in teacher_preferences[code]:
                                    filtered_sections[code].append(course)
                            else:
                                filtered_sections[code].append(course)
                    
                    # Find best schedule
                    best_schedule = find_best_schedule(filtered_sections)
                    
                    if best_schedule:
                        st.success("✅ **Found a Perfect Schedule!**")
                        
                        # Display schedule
                        st.subheader("📅 Your Generated Timetable")
                        
                        # Show selected courses
                        total_credits = sum(c.credits for c in best_schedule)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Courses", len(best_schedule))
                        with col2:
                            st.metric("Total Credits", total_credits)
                        
                        st.write("---")
                        
                        # Weekly view
                        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                        
                        for day in days:
                            day_schedule = []
                            for course in best_schedule:
                                for slot in course.schedule:
                                    if slot['day'] == day:
                                        day_schedule.append({
                                            'start': slot['start'],
                                            'end': slot['end'],
                                            'course': course
                                        })
                            
                            if day_schedule:
                                day_schedule.sort(key=lambda x: x['start'])
                                
                                st.write(f"### {day}")
                                for item in day_schedule:
                                    st.info(
                                        f"🕐 **{item['start']} - {item['end']}**\n\n"
                                        f"**{item['course'].code}** - {item['course'].name}\n\n"
                                        f"Section: {item['course'].section} | 👤 {item['course'].instructor}"
                                    )
                        
                        st.write("---")
                        
                        # Course details
                        st.subheader("📚 Course Details")
                        
                        for course in best_schedule:
                            with st.expander(f"{course.code} - {course.name}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.write(f"**Section:** {course.section}")
                                    st.write(f"**Instructor:** {course.instructor}")
                                with col2:
                                    st.write(f"**Credits:** {course.credits}")
                                    st.write(f"**Dates:** {course.dates}")
                                
                                st.write("**Schedule:**")
                                for slot in course.schedule:
                                    st.write(f"• {slot['day']}: {slot['start']} - {slot['end']}")
                        
                        # Download
                        schedule_text = "MY AUTO-GENERATED COURSE SCHEDULE\n" + "="*60 + "\n\n"
                        schedule_text += f"Total Courses: {len(best_schedule)}\n"
                        schedule_text += f"Total Credits: {total_credits}\n\n"
                        schedule_text += "COURSES:\n" + "-"*60 + "\n\n"
                        
                        for course in best_schedule:
                            schedule_text += f"{course.code} - {course.name}\n"
                            schedule_text += f"Section: {course.section}\n"
                            schedule_text += f"Instructor: {course.instructor}\n"
                            schedule_text += f"Credits: {course.credits}\n"
                            schedule_text += "Schedule:\n"
                            for slot in course.schedule:
                                schedule_text += f"  {slot['day']}: {slot['start']} - {slot['end']}\n"
                            schedule_text += "\n"
                        
                        st.download_button(
                            label="📥 Download Your Schedule",
                            data=schedule_text,
                            file_name="auto_generated_schedule.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                        
                    else:
                        st.error("❌ **Could Not Find a Conflict-Free Schedule**")
                        st.write("**Possible reasons:**")
                        st.write("• Your selected courses/teachers have unavoidable conflicts")
                        st.write("• Your leave days make it impossible to fit all courses")
                        st.write("• Try selecting different teachers")
                        st.write("• Try reducing leave days")
                        st.write("• Try removing some courses")
                        
                        st.write("---")
                        st.write("**Showing all conflicts:**")
                        
                        # Show what conflicts exist
                        for i, code1 in enumerate(selected_course_codes):
                            for code2 in selected_course_codes[i+1:]:
                                sections1 = filtered_sections[code1]
                                sections2 = filtered_sections[code2]
                                
                                all_conflict = True
                                for s1 in sections1:
                                    for s2 in sections2:
                                        if not has_conflict(s1, s2):
                                            all_conflict = False
                                            break
                                    if not all_conflict:
                                        break
                                
                                if all_conflict:
                                    st.warning(f"⚠️ **{code1}** and **{code2}** have conflicts in ALL available sections")
        
        else:
            st.info("👆 **Step 1:** Select the courses you want to take")

else:
    st.info("👆 **Upload your course timetable PDF to get started!**")
    
    st.write("---")
    st.write("### How It Works:")
    st.write("1. 📤 Upload your PDF timetable")
    st.write("2. ✅ Select courses you want to take")
    st.write("3. 🏖️ Choose days you want off (optional)")
    st.write("4. 👤 Choose preferred teachers (optional)")
    st.write("5. 🎯 Click 'Generate' - we'll find a conflict-free schedule automatically!")
    st.write("6. 📥 Download your perfect schedule")

# Sidebar
with st.sidebar:
    st.header("✨ Automatic Scheduling")
    st.write("""
This tool automatically finds a schedule with:

✅ No time conflicts
✅ Your preferred teachers
✅ Respects your leave days
✅ All your selected courses

Just select what you want, and we do the rest!
    """)
    
    st.divider()
    
    st.header("🎯 How It Works")
    st.write("""
The system tries all possible combinations of course sections and finds one where no classes overlap.

If no schedule is possible, you will be told which courses conflict.
    """)
    
    st.divider()
    
    st.header("💡 Tips")
    st.write("""
- Select all teachers initially
- Use leave days to get specific days off
- If no schedule found, try reducing leave days
- You can also deselect some teachers or remove a course
    """)
