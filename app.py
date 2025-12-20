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
    def __init__(self, name, code, days, start_time, end_time, prereqs=None):
        self.name = name
        self.code = code
        self.days = days  # List like ["Monday", "Wednesday"]
        self.start_time = start_time
        self.end_time = end_time
        self.prereqs = prereqs or []

def parse_time(time_str):
    """Convert time string like '09:00' or '9:00 AM' to time object"""
    time_str = time_str.strip().upper()
    
    # Try different formats
    formats = ['%H:%M', '%I:%M %p', '%I:%M%p', '%H.%M']
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except:
            continue
    return None

def extract_courses_from_pdf(pdf_file):
    """Extract course information from PDF"""
    courses = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            
            # Example parsing - adjust based on your PDF format
            lines = text.split('\n')
            
            for line in lines:
                # Skip empty lines
                if not line.strip():
                    continue
                
                # Simple pattern matching - adjust to your PDF format
                # Example: "CS101 Programming Mon/Wed 9:00-10:30"
                
                # Try to find course code (letters + numbers)
                code_match = re.search(r'\b([A-Z]{2,4}\s*\d{3,4})\b', line)
                
                # Try to find time pattern
                time_match = re.search(r'(\d{1,2}[:.]\d{2})\s*[-–]\s*(\d{1,2}[:.]\d{2})', line)
                
                # Try to find days
                day_match = re.findall(r'\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b', line, re.IGNORECASE)
                
                if code_match and time_match and day_match:
                    code = code_match.group(1)
                    start = time_match.group(1).replace('.', ':')
                    end = time_match.group(2).replace('.', ':')
                    days = [d.capitalize() for d in day_match]
                    
                    # Extract course name (text before the code)
                    name = line.split(code)[0].strip() or code
                    
                    course = Course(name, code, days, start, end)
                    courses.append(course)
    
    return courses

def check_time_overlap(course1, course2):
    """Check if two courses have time conflicts"""
    conflicts = []
    
    for day1 in course1.days:
        for day2 in course2.days:
            # Check if same day
            if day1.lower()[:3] == day2.lower()[:3]:  # Compare first 3 letters
                # Parse times
                start1 = parse_time(course1.start_time)
                end1 = parse_time(course1.end_time)
                start2 = parse_time(course2.start_time)
                end2 = parse_time(course2.end_time)
                
                if all([start1, end1, start2, end2]):
                    # Check overlap
                    if start1 < end2 and start2 < end1:
                        conflicts.append({
                            'day': day1,
                            'course1': course1,
                            'course2': course2
                        })
    
    return conflicts

def check_all_conflicts(selected_courses):
    """Check all selected courses for conflicts"""
    time_conflicts = []
    
    for i, course1 in enumerate(selected_courses):
        for course2 in selected_courses[i+1:]:
            conflicts = check_time_overlap(course1, course2)
            if conflicts:
                time_conflicts.extend(conflicts)
    
    return time_conflicts

# File uploader
uploaded_file = st.file_uploader("Upload your course timetable (PDF)", type=['pdf'])

if uploaded_file:
    with st.spinner("Extracting courses from PDF..."):
        courses = extract_courses_from_pdf(uploaded_file)
    
    if courses:
        st.success(f"✅ Found {len(courses)} courses!")
        
        # Display courses with checkboxes
        st.subheader("📋 Select Your Courses")
        
        selected_courses = []
        
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])
        
        for course in courses:
            with col1:
                checkbox = st.checkbox(
                    f"**{course.code}** - {course.name}",
                    key=course.code
                )
                
                # Show course details
                days_str = ", ".join(course.days)
                st.write(f"   🕐 {days_str} | {course.start_time} - {course.end_time}")
                st.write("")
                
                if checkbox:
                    selected_courses.append(course)
        
        # Check for conflicts button
        if selected_courses:
            st.divider()
            st.subheader(f"Selected: {len(selected_courses)} courses")
            
            if st.button("🔍 Check for Conflicts", type="primary"):
                conflicts = check_all_conflicts(selected_courses)
                
                if conflicts:
                    st.error(f"⚠️ Found {len(conflicts)} time conflict(s)!")
                    
                    for conflict in conflicts:
                        c1 = conflict['course1']
                        c2 = conflict['course2']
                        st.warning(
                            f"**TIME CONFLICT on {conflict['day']}:**\n\n"
                            f"• {c1.code} ({c1.start_time} - {c1.end_time})\n\n"
                            f"• {c2.code} ({c2.start_time} - {c2.end_time})"
                        )
                else:
                    st.success("✅ No conflicts found! Your schedule looks good!")
                    
                    # Show summary
                    st.subheader("📅 Your Schedule Summary")
                    for course in selected_courses:
                        days_str = ", ".join(course.days)
                        st.write(f"**{course.code}**: {days_str} | {course.start_time}-{course.end_time}")
        else:
            st.info("👆 Select courses above to check for conflicts")
            
    else:
        st.warning("⚠️ Couldn't extract courses from PDF. Make sure your PDF contains course schedules with times.")
        st.info("💡 **Tip:** Your PDF should have courses in format like:\n\n`CS101 Programming Mon/Wed 9:00-10:30`")

else:
    st.info("👆 Upload a PDF to get started!")
    
    # Show example
    with st.expander("📄 Example PDF Format"):
        st.write("Your PDF should contain course information like:")
        st.code("""
CS101 Introduction to Programming
Monday/Wednesday 09:00-10:30

MATH201 Calculus II  
Tuesday/Thursday 11:00-12:30

CS102 Data Structures
Monday/Wednesday 09:00-10:30
        """)

# Sidebar with instructions
with st.sidebar:
    st.header("ℹ️ How to Use")
    st.write("""
    1. **Upload** your course timetable PDF
    2. **Select** the courses you want to take
    3. **Click** "Check for Conflicts"
    4. Review any time conflicts!
    """)
    
    st.divider()
    
    st.header("📝 Requirements")
    st.write("""
    Your PDF should include:
    - Course codes (e.g., CS101)
    - Course names
    - Days (Mon, Tue, etc.)
    - Times (e.g., 9:00-10:30)
    """)
