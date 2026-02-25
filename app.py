import streamlit as st
import pdfplumber
from datetime import datetime, time
import re

# Page config
st.set_page_config(page_title="Course Conflict Checker", page_icon="📚", layout="wide")

# Title
st.title("📚 Course Schedule Conflict Checker")
st.write("Upload your course timetable PDF and select courses without conflicts!")

# Course class
class Course:
    def __init__(self, code, name, section, instructor, dates, schedule, credits):
        self.code = code
        self.name = name
        self.section = section
        self.instructor = instructor
        self.dates = dates
        self.schedule = schedule  # List of {day, start, end}
        self.credits = credits
    
    def __repr__(self):
        return f"{self.code} - {self.section}"

def parse_time(time_str):
    """Convert time string to time object"""
    try:
        time_str = time_str.strip()
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)
    except:
        return None

def extract_courses_from_pdf(pdf_file):
    """Extract course information from your specific PDF format"""
    courses = []
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
    
    # Split by course code pattern
    course_blocks = re.split(r'(\d{2}[A-Z]{2}\d{3})', full_text)
    
    current_code = None
    current_name = None
    current_credits = None
    
    for i, block in enumerate(course_blocks):
        # Check if this is a course code
        if re.match(r'\d{2}[A-Z]{2}\d{3}', block):
            current_code = block
            
            # Get the next block which contains course details
            if i + 1 < len(course_blocks):
                details = course_blocks[i + 1]
                
                # Extract credits
                credit_match = re.search(r'\[(\d+)\s*Credits\]', details)
                if credit_match:
                    current_credits = int(credit_match.group(1))
                
                # Extract course name
                name_match = re.search(r'Course overview\s+(.+?)(?=\n|$)', details)
                if name_match:
                    current_name = name_match.group(1).strip()
                
                # Find all sections for this course
                section_pattern = r'([\w-]+),\s*(\w+)\s*-\s*(.+?)\s+Date:\s*(\d{2}-\d{2}-\d{4})\s*to\s*(\d{2}-\d{2}-\d{4})'
                sections = re.finditer(section_pattern, details)
                
                for section_match in sections:
                    section = section_match.group(1)
                    dept = section_match.group(2)
                    instructor = section_match.group(3)
                    start_date = section_match.group(4)
                    end_date = section_match.group(5)
                    
                    # Extract schedule for this section
                    section_end = details.find('No. of attempts:', section_match.end())
                    if section_end == -1:
                        section_end = len(details)
                    
                    section_text = details[section_match.end():section_end]
                    
                    # Parse schedule lines
                    schedule = []
                    schedule_lines = section_text.strip().split('\n')
                    
                    for line in schedule_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Match day and times: "Monday: 08:00 - 09:00 09:00 - 10:00"
                        day_match = re.match(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday):\s*(.+)', line)
                        if day_match:
                            day = day_match.group(1)
                            times_str = day_match.group(2)
                            
                            # Extract all time ranges
                            time_ranges = re.findall(r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})', times_str)
                            
                            for start, end in time_ranges:
                                schedule.append({
                                    'day': day,
                                    'start': start,
                                    'end': end
                                })
                    
                    if schedule:  # Only add if we found schedule
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
        # Check overlap: slots overlap if start1 < end2 AND start2 < end1
        return start1 < end2 and start2 < end1
    return False

def check_all_conflicts(selected_courses):
    """Check all selected courses for conflicts in real-time"""
    conflicts = []
    
    # Build a time slot map
    time_slots = {}  # {(day, start, end): [courses]}
    
    for course in selected_courses:
        for slot in course.schedule:
            key = (slot['day'], slot['start'], slot['end'])
            if key not in time_slots:
                time_slots[key] = []
            time_slots[key].append(course)
    
    # Check for exact same time slots
    for key, courses_in_slot in time_slots.items():
        if len(courses_in_slot) > 1:
            day, start, end = key
            for i in range(len(courses_in_slot)):
                for j in range(i + 1, len(courses_in_slot)):
                    conflicts.append({
                        'type': 'exact',
                        'course1': courses_in_slot[i],
                        'course2': courses_in_slot[j],
                        'day': day,
                        'time': f"{start} - {end}"
                    })
    
    # Check for overlapping time slots
    for i, course1 in enumerate(selected_courses):
        for j in range(i + 1, len(selected_courses)):
            course2 = selected_courses[j]
            
            for slot1 in course1.schedule:
                for slot2 in course2.schedule:
                    if slot1['day'] == slot2['day']:
                        if check_time_overlap(slot1, slot2):
                            # Check if not already added as exact match
                            is_exact = (slot1['start'] == slot2['start'] and 
                                       slot1['end'] == slot2['end'])
                            
                            if not is_exact:
                                conflicts.append({
                                    'type': 'overlap',
                                    'course1': course1,
                                    'course2': course2,
                                    'day': slot1['day'],
                                    'time1': f"{slot1['start']} - {slot1['end']}",
                                    'time2': f"{slot2['start']} - {slot2['end']}"
                                })
    
    return conflicts

# File uploader
uploaded_file = st.file_uploader("Upload your course timetable (PDF)", type=['pdf'])

if uploaded_file:
    with st.spinner("Extracting courses from PDF..."):
        courses = extract_courses_from_pdf(uploaded_file)
    
    if courses:
        st.success(f"✅ Found {len(courses)} course sections!")
        
        # Create a session state to track selections
        if 'selected_courses' not in st.session_state:
            st.session_state.selected_courses = []
        
        # Display courses in a clean table format
        st.subheader("📋 Available Courses")
        
        # Group courses by code
        courses_by_code = {}
        for course in courses:
            if course.code not in courses_by_code:
                courses_by_code[course.code] = []
            courses_by_code[course.code].append(course)
        
        selected_courses = []
        
        # Display as simple list
        for code in sorted(courses_by_code.keys()):
            course_sections = courses_by_code[code]
            first_course = course_sections[0]
            
            st.write("---")
            st.subheader(f"{code} - {first_course.name}")
            st.caption(f"Credits: {first_course.credits}")
            
            # Show all sections in a table-like format
            for idx, course in enumerate(course_sections):
                checkbox_key = f"{course.code}_{course.section}_{idx}_{course.instructor}"
                
                col1, col2, col3 = st.columns([1, 2, 3])
                
                with col1:
                    is_selected = st.checkbox(
                        f"**{course.section}**",
                        key=checkbox_key
                    )
                
                with col2:
                    st.write(f"👤 **{course.instructor}**")
                
                with col3:
                    # Format schedule nicely
                    schedule_by_day = {}
                    for slot in course.schedule:
                        day = slot['day']
                        time_str = f"{slot['start']}-{slot['end']}"
                        if day not in schedule_by_day:
                            schedule_by_day[day] = []
                        schedule_by_day[day].append(time_str)
                    
                    schedule_text = " | ".join([f"{day}: {', '.join(times)}" 
                                               for day, times in schedule_by_day.items()])
                    st.write(f"🕐 {schedule_text}")
                
                if is_selected:
                    selected_courses.append(course)
        
        # Real-time conflict checking
        st.write("---")
        
        if selected_courses:
            st.subheader(f"✅ You Selected {len(selected_courses)} Course Sections")
            
            # Calculate total credits
            total_credits = sum(c.credits for c in selected_courses)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Courses", len(selected_courses))
            with col2:
                st.metric("Total Credits", total_credits)
            
            # Check for conflicts automatically
            conflicts = check_all_conflicts(selected_courses)
            
            if conflicts:
                st.error(f"⚠️ **ALERT: {len(conflicts)} TIME CONFLICT(S) DETECTED!**")
                
                for idx, conflict in enumerate(conflicts, 1):
                    c1 = conflict['course1']
                    c2 = conflict['course2']
                    
                    if conflict['type'] == 'exact':
                        st.error(
                            f"**Conflict #{idx}: Same Time Slot!**\n\n"
                            f"❌ **{c1.code}** (Section {c1.section}) - {c1.instructor}\n\n"
                            f"❌ **{c2.code}** (Section {c2.section}) - {c2.instructor}\n\n"
                            f"Both classes are on **{conflict['day']} at {conflict['time']}**\n\n"
                            f"👉 Please choose a different section for one of these courses!"
                        )
                    else:
                        st.warning(
                            f"**Conflict #{idx}: Overlapping Times!**\n\n"
                            f"⚠️ **{c1.code}** (Section {c1.section}): {conflict['day']} {conflict['time1']}\n\n"
                            f"⚠️ **{c2.code}** (Section {c2.section}): {conflict['day']} {conflict['time2']}\n\n"
                            f"These classes overlap on **{conflict['day']}**\n\n"
                            f"👉 Choose different sections to avoid this conflict!"
                        )
                
            else:
                st.success("✅ **NO CONFLICTS! Your schedule is perfect!**")
                
                # Show weekly timetable
                st.subheader("📅 Your Weekly Timetable")
                
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                for day in days:
                    day_schedule = []
                    for course in selected_courses:
                        for slot in course.schedule:
                            if slot['day'] == day:
                                day_schedule.append({
                                    'start': slot['start'],
                                    'end': slot['end'],
                                    'course': course
                                })
                    
                    if day_schedule:
                        # Sort by start time
                        day_schedule.sort(key=lambda x: x['start'])
                        
                        st.write(f"### {day}")
                        for item in day_schedule:
                            st.write(
                                f"🕐 **{item['start']} - {item['end']}** | "
                                f"{item['course'].code} ({item['course'].section}) - "
                                f"{item['course'].name} | "
                                f"👤 {item['course'].instructor}"
                            )
                        st.write("")
                
                # Summary list
                st.subheader("📝 Selected Courses Summary")
                
                for course in selected_courses:
                    with st.expander(f"{course.code} - {course.name} (Section {course.section})"):
                        st.write(f"**Instructor:** {course.instructor}")
                        st.write(f"**Credits:** {course.credits}")
                        st.write(f"**Dates:** {course.dates}")
                        st.write("**Schedule:**")
                        for slot in course.schedule:
                            st.write(f"  • {slot['day']}: {slot['start']} - {slot['end']}")
                
                # Download option
                schedule_text = "MY COURSE SCHEDULE\n" + "="*60 + "\n\n"
                schedule_text += f"Total Courses: {len(selected_courses)}\n"
                schedule_text += f"Total Credits: {total_credits}\n\n"
                
                for course in selected_courses:
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
                    file_name="my_course_schedule.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        else:
            st.info("👆 **Select course sections above** by checking the boxes")
            st.write("- Choose ONE section per course")
            st.write("- Conflicts will be detected automatically")
            st.write("- You'll see alerts if there are any time clashes")
            
    else:
        st.warning("⚠️ Couldn't extract courses from PDF.")

else:
    st.info("👆 **Upload your course timetable PDF to get started!**")
    
    st.write("---")
    st.write("### How It Works:")
    st.write("1. 📤 Upload your PDF timetable")
    st.write("2. 📋 Browse courses organized by course code")
    st.write("3. ✅ Select ONE section for each course you want")
    st.write("4. ⚠️ Get instant alerts if there are time conflicts")
    st.write("5. 📥 Download your final schedule when conflict-free!")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About This Tool")
    st.write("""
    This tool helps you build a conflict-free course schedule by:
    
    ✅ Detecting exact time conflicts
    ✅ Detecting overlapping class times
    ✅ Showing clear alerts when conflicts exist
    ✅ Organizing your weekly timetable
    """)
    
    st.divider()
    
    st.header("⚠️ Conflict Types")
    st.write("""
    **Exact Conflict (❌):**
    Two courses at the exact same time
    
    **Overlap Conflict (⚠️):**
    Two courses with overlapping times
    
    Both types mean you cannot take those sections together!
    """)
    
    st.divider()
    
    st.header("💡 Tips")
    st.write("""
    - Select sections carefully
    - Check for conflicts before finalizing
    - Try different sections if conflicts occur
    - Download your schedule when ready
    """)
