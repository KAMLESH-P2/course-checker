import streamlit as st
import pdfplumber
from datetime import datetime, time
import re

# Page config
st.set_page_config(page_title="Custom Timetable Builder", page_icon="📚", layout="wide")

# Title
st.title("📚 Custom Timetable Builder")
st.write("Select courses and teachers to build your personalized timetable!")

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

# File uploader
uploaded_file = st.file_uploader("📤 Upload Course PDF", type=['pdf'])

if uploaded_file:
    with st.spinner("📖 Reading PDF..."):
        all_courses = extract_courses_from_pdf(uploaded_file)
    
    if all_courses:
        st.success(f"✅ Found {len(all_courses)} course sections!")
        
        # Group courses by code
        courses_by_code = {}
        for course in all_courses:
            if course.code not in courses_by_code:
                courses_by_code[course.code] = []
            courses_by_code[course.code].append(course)
        
        # Group teachers by course
        teachers_by_course = {}
        for code, sections in courses_by_code.items():
            teachers_by_course[code] = {}
            for course in sections:
                if course.instructor not in teachers_by_course[code]:
                    teachers_by_course[code][course.instructor] = []
                teachers_by_course[code][course.instructor].append(course)
        
        st.write("---")
        
        # Step 1: Select Courses
        st.header("Step 1: Select Courses")
        
        selected_courses_dict = {}  # {code: course_name}
        
        cols = st.columns(3)
        for idx, code in enumerate(sorted(courses_by_code.keys())):
            first_course = courses_by_code[code][0]
            with cols[idx % 3]:
                if st.checkbox(
                    f"**{code}**",
                    key=f"course_{code}"
                ):
                    selected_courses_dict[code] = first_course.name
                st.caption(f"{first_course.name}\n({first_course.credits} credits)")
        
        if selected_courses_dict:
            st.success(f"✅ Selected {len(selected_courses_dict)} courses")
            
            # Step 2: Select Teachers
            st.header("Step 2: Select Teachers")
            st.write("Choose one teacher for each selected course:")
            
            selected_sections = {}  # {code: selected_course_object}
            
            for code in selected_courses_dict.keys():
                st.subheader(f"{code} - {selected_courses_dict[code]}")
                
                teachers = list(teachers_by_course[code].keys())
                
                # Create radio buttons for teacher selection
                selected_teacher = st.radio(
                    "Choose teacher:",
                    teachers,
                    key=f"teacher_{code}",
                    horizontal=True
                )
                
                # Get the course section for selected teacher
                course_options = teachers_by_course[code][selected_teacher]
                
                if len(course_options) == 1:
                    selected_sections[code] = course_options[0]
                    st.info(f"Section: {course_options[0].section}")
                else:
                    # Multiple sections with same teacher - show sections
                    section_choice = st.selectbox(
                        "Choose section:",
                        [c.section for c in course_options],
                        key=f"section_{code}"
                    )
                    
                    for course in course_options:
                        if course.section == section_choice:
                            selected_sections[code] = course
                            break
                
                # Show schedule for selected section
                if code in selected_sections:
                    course = selected_sections[code]
                    schedule_text = ""
                    schedule_by_day = {}
                    for slot in course.schedule:
                        day = slot['day']
                        time_str = f"{slot['start']}-{slot['end']}"
                        if day not in schedule_by_day:
                            schedule_by_day[day] = []
                        schedule_by_day[day].append(time_str)
                    
                    for day, times in schedule_by_day.items():
                        schedule_text += f"{day}: {', '.join(times)} | "
                    
                    st.caption(f"🕐 {schedule_text.rstrip(' | ')}")
                
                st.write("")
            
            # Step 3: Generate Timetable
            st.write("---")
            st.header("Step 3: Your Timetable")
            
            if st.button("📅 Generate My Timetable", type="primary", use_container_width=True):
                
                # Check for conflicts
                selected_course_list = list(selected_sections.values())
                conflicts = []
                
                for i in range(len(selected_course_list)):
                    for j in range(i + 1, len(selected_course_list)):
                        if has_conflict(selected_course_list[i], selected_course_list[j]):
                            conflicts.append((selected_course_list[i], selected_course_list[j]))
                
                if conflicts:
                    st.error(f"⚠️ **Time Conflicts Detected! ({len(conflicts)} conflicts)**")
                    
                    for c1, c2 in conflicts:
                        # Find specific conflict times
                        conflict_details = []
                        for slot1 in c1.schedule:
                            for slot2 in c2.schedule:
                                if slot1['day'] == slot2['day'] and check_time_overlap(slot1, slot2):
                                    conflict_details.append(f"{slot1['day']} at {slot1['start']}-{slot1['end']}")
                        
                        st.warning(
                            f"**{c1.code}** ({c1.instructor}) conflicts with **{c2.code}** ({c2.instructor})\n\n"
                            f"Conflict on: {', '.join(set(conflict_details))}\n\n"
                            f"👉 Please select different teachers or sections"
                        )
                
                else:
                    st.success("✅ **No Conflicts! Your Timetable is Ready!**")
                    
                    # Summary
                    total_credits = sum(c.credits for c in selected_course_list)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Total Courses", len(selected_course_list))
                    with col2:
                        st.metric("Total Credits", total_credits)
                    
                    st.write("---")
                    
                    # Weekly Timetable View
                    st.subheader("📅 Your Weekly Schedule")
                    
                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    
                    for day in days:
                        day_schedule = []
                        
                        for course in selected_course_list:
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
                                    f"👤 {item['course'].instructor} | Section: {item['course'].section}"
                                )
                    
                    st.write("---")
                    
                    # Course Summary
                    st.subheader("📚 Course Summary")
                    
                    for course in selected_course_list:
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
                    st.write("---")
                    
                    timetable_text = "MY PERSONALIZED TIMETABLE\n" + "="*70 + "\n\n"
                    timetable_text += f"Total Courses: {len(selected_course_list)}\n"
                    timetable_text += f"Total Credits: {total_credits}\n\n"
                    
                    timetable_text += "WEEKLY SCHEDULE:\n" + "-"*70 + "\n\n"
                    
                    for day in days:
                        day_schedule = []
                        
                        for course in selected_course_list:
                            for slot in course.schedule:
                                if slot['day'] == day:
                                    day_schedule.append((slot['start'], slot['end'], course))
                        
                        if day_schedule:
                            day_schedule.sort(key=lambda x: x[0])
                            timetable_text += f"{day}:\n"
                            
                            for start, end, course in day_schedule:
                                timetable_text += f"  {start}-{end}: {course.code} - {course.name}\n"
                                timetable_text += f"              Teacher: {course.instructor}\n"
                            
                            timetable_text += "\n"
                    
                    timetable_text += "\nCOURSE DETAILS:\n" + "-"*70 + "\n\n"
                    
                    for course in selected_course_list:
                        timetable_text += f"{course.code} - {course.name}\n"
                        timetable_text += f"Section: {course.section} | Instructor: {course.instructor}\n"
                        timetable_text += f"Credits: {course.credits} | Dates: {course.dates}\n"
                        timetable_text += "Schedule:\n"
                        for slot in course.schedule:
                            timetable_text += f"  {slot['day']}: {slot['start']}-{slot['end']}\n"
                        timetable_text += "\n"
                    
                    st.download_button(
                        label="📥 Download My Timetable",
                        data=timetable_text,
                        file_name="my_timetable.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
        
        else:
            st.info("👆 Select courses in Step 1 to continue")

else:
    st.info("👆 **Upload your course PDF to get started!**")
    
    st.write("---")
    
    st.write("### How It Works:")
    st.write("1. 📤 Upload your PDF")
    st.write("2. ✅ Select courses you want")
    st.write("3. 👤 Choose teacher for each course")
    st.write("4. 📅 Generate your personalized timetable")
    st.write("5. ⚠️ Get alerts if there are conflicts")
    st.write("6. 📥 Download your timetable")

# Sidebar
with st.sidebar:
    st.header("✨ Features")
    st.write("""
✅ Select only courses you want
✅ Choose specific teachers
✅ Automatic conflict detection
✅ Weekly timetable view
✅ Download your schedule
    """)
    
    st.divider()
    
    st.header("💡 Tips")
    st.write("""
- Select all courses first
- Then choose teachers carefully
- If conflicts appear, try different teachers
- Download your final timetable
    """)
