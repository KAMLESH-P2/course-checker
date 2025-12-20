import streamlit as st
import pdfplumber
from datetime import datetime, time
import re

# Page config
st.set_page_config(page_title="Course Conflict Checker", page_icon="📚", layout="wide")

# Title
st.title("📚 Course Schedule Conflict Checker")
st.write("Upload your course timetable PDF to check for conflicts!")

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

def check_time_overlap(course1, course2):
    """Check if two courses have time conflicts"""
    conflicts = []
    
    for slot1 in course1.schedule:
        for slot2 in course2.schedule:
            if slot1['day'] == slot2['day']:
                start1 = parse_time(slot1['start'])
                end1 = parse_time(slot1['end'])
                start2 = parse_time(slot2['start'])
                end2 = parse_time(slot2['end'])
                
                if all([start1, end1, start2, end2]):
                    # Check overlap
                    if start1 < end2 and start2 < end1:
                        conflicts.append({
                            'day': slot1['day'],
                            'time1': f"{slot1['start']}-{slot1['end']}",
                            'time2': f"{slot2['start']}-{slot2['end']}"
                        })
    
    return conflicts

def check_all_conflicts(selected_courses):
    """Check all selected courses for conflicts"""
    conflicts = []
    
    for i, course1 in enumerate(selected_courses):
        for course2 in selected_courses[i+1:]:
            course_conflicts = check_time_overlap(course1, course2)
            if course_conflicts:
                for conflict in course_conflicts:
                    conflicts.append({
                        'course1': course1,
                        'course2': course2,
                        'day': conflict['day'],
                        'time1': conflict['time1'],
                        'time2': conflict['time2']
                    })
    
    return conflicts

# File uploader
uploaded_file = st.file_uploader("Upload your course timetable (PDF)", type=['pdf'])

if uploaded_file:
    with st.spinner("Extracting courses from PDF..."):
        courses = extract_courses_from_pdf(uploaded_file)
    
    if courses:
        st.success(f"✅ Found {len(courses)} course sections!")
        
        # Group courses by code for better display
        courses_by_code = {}
        for course in courses:
            if course.code not in courses_by_code:
                courses_by_code[course.code] = []
            courses_by_code[course.code].append(course)
        
        # Display courses with checkboxes
        st.subheader("📋 Select Your Course Sections")
        st.info("💡 Each course may have multiple sections with different times. Select ONE section per course.")
        
        selected_courses = []
        
        for code in sorted(courses_by_code.keys()):
            course_sections = courses_by_code[code]
            
            with st.expander(f"**{code}** - {course_sections[0].name} ({course_sections[0].credits} credits) - {len(course_sections)} sections"):
                for course in course_sections:
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        checkbox_key = f"{course.code}_{course.section}"
                        selected = st.checkbox(
                            f"**Section {course.section}** - {course.instructor}",
                            key=checkbox_key
                        )
                        
                        # Show schedule
                        schedule_text = ""
                        for slot in course.schedule:
                            schedule_text += f"  • {slot['day']}: {slot['start']}-{slot['end']}\n"
                        
                        st.text(schedule_text)
                        st.caption(f"📅 {course.dates}")
                        
                        if selected:
                            selected_courses.append(course)
                
                st.divider()
        
        # Check for conflicts
        if selected_courses:
            st.divider()
            st.subheader(f"✅ Selected: {len(selected_courses)} course sections")
            
            # Show selected courses
            total_credits = sum(c.credits for c in selected_courses)
            st.metric("Total Credits", total_credits)
            
            if st.button("🔍 Check for Conflicts", type="primary", use_container_width=True):
                conflicts = check_all_conflicts(selected_courses)
                
                if conflicts:
                    st.error(f"⚠️ Found {len(conflicts)} time conflict(s)!")
                    
                    for conflict in conflicts:
                        c1 = conflict['course1']
                        c2 = conflict['course2']
                        
                        st.warning(
                            f"**⚠️ TIME CONFLICT on {conflict['day']}:**\n\n"
                            f"**{c1.code}** (Section {c1.section}) - {conflict['time1']}\n\n"
                            f"**{c2.code}** (Section {c2.section}) - {conflict['time2']}\n\n"
                            f"These two sections overlap!"
                        )
                else:
                    st.success("✅ No conflicts found! Your schedule looks good!")
                    
                    # Show weekly schedule summary
                    st.subheader("📅 Your Weekly Schedule")
                    
                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    
                    for day in days:
                        day_schedule = []
                        for course in selected_courses:
                            for slot in course.schedule:
                                if slot['day'] == day:
                                    day_schedule.append((slot['start'], slot['end'], course))
                        
                        if day_schedule:
                            day_schedule.sort(key=lambda x: x[0])
                            st.write(f"**{day}:**")
                            for start, end, course in day_schedule:
                                st.write(f"  • {start}-{end}: {course.code} ({course.section}) - {course.name}")
                    
                    # Download schedule option
                    schedule_text = "MY COURSE SCHEDULE\n" + "="*50 + "\n\n"
                    for course in selected_courses:
                        schedule_text += f"{course.code} - {course.name}\n"
                        schedule_text += f"Section: {course.section} | Instructor: {course.instructor}\n"
                        schedule_text += f"Credits: {course.credits}\n"
                        for slot in course.schedule:
                            schedule_text += f"  {slot['day']}: {slot['start']}-{slot['end']}\n"
                        schedule_text += "\n"
                    
                    st.download_button(
                        label="📥 Download Schedule",
                        data=schedule_text,
                        file_name="my_schedule.txt",
                        mime="text/plain"
                    )
        else:
            st.info("👆 Select course sections above to check for conflicts")
            
    else:
        st.warning("⚠️ Couldn't extract courses from PDF. Please make sure it's the correct format.")

else:
    st.info("👆 Upload your course timetable PDF to get started!")
    
    st.write("---")
    st.write("**How it works:**")
    st.write("1. Upload your PDF timetable")
    st.write("2. Expand each course to see available sections")
    st.write("3. Select ONE section per course")
    st.write("4. Click 'Check for Conflicts' to see if your selections overlap")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.write("""
    This tool helps you:
    - View all available course sections
    - Select your preferred sections
    - Detect time conflicts automatically
    - Download your final schedule
    """)
    
    st.divider()
    
    st.header("💡 Tips")
    st.write("""
    - Each course may have multiple sections
    - Select only ONE section per course
    - Check for conflicts before finalizing
    - Download your schedule when ready
    """)
