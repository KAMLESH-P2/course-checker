import streamlit as st
import pdfplumber
from datetime import datetime, time
import re

# Page config
st.set_page_config(page_title="PDF to Timetable", page_icon="📚", layout="wide")

# Title
st.title("📚 PDF to Timetable Generator")
st.write("Upload your course PDF and instantly get a formatted timetable!")

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

# File uploader
uploaded_file = st.file_uploader("📤 Upload Course PDF", type=['pdf'])

if uploaded_file:
    with st.spinner("📖 Reading PDF and extracting information..."):
        courses = extract_courses_from_pdf(uploaded_file)
    
    if courses:
        st.success(f"✅ Successfully extracted {len(courses)} course sections!")
        
        # Display summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Sections", len(courses))
        
        with col2:
            unique_courses = len(set([c.code for c in courses]))
            st.metric("Unique Courses", unique_courses)
        
        st.write("---")
        
        # Option 1: View as List
        st.header("📋 Course List")
        
        # Group by course code
        courses_by_code = {}
        for course in courses:
            if course.code not in courses_by_code:
                courses_by_code[course.code] = []
            courses_by_code[course.code].append(course)
        
        for code in sorted(courses_by_code.keys()):
            sections = courses_by_code[code]
            first = sections[0]
            
            with st.expander(f"**{code}** - {first.name} ({first.credits} credits) - {len(sections)} sections"):
                for course in sections:
                    st.write(f"**Section {course.section}** - 👤 {course.instructor}")
                    st.caption(f"📅 {course.dates}")
                    
                    # Show schedule
                    schedule_by_day = {}
                    for slot in course.schedule:
                        day = slot['day']
                        time_str = f"{slot['start']}-{slot['end']}"
                        if day not in schedule_by_day:
                            schedule_by_day[day] = []
                        schedule_by_day[day].append(time_str)
                    
                    for day, times in schedule_by_day.items():
                        st.write(f"  • {day}: {', '.join(times)}")
                    
                    st.write("")
        
        st.write("---")
        
        # Option 2: Weekly Timetable View
        st.header("📅 Weekly Timetable View")
        st.write("Shows all classes organized by day and time")
        
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in days:
            # Collect all classes on this day
            day_classes = []
            
            for course in courses:
                for slot in course.schedule:
                    if slot['day'] == day:
                        day_classes.append({
                            'start': slot['start'],
                            'end': slot['end'],
                            'course': course
                        })
            
            if day_classes:
                # Sort by start time
                day_classes.sort(key=lambda x: x['start'])
                
                st.subheader(f"📆 {day}")
                
                for item in day_classes:
                    st.info(
                        f"🕐 **{item['start']} - {item['end']}**\n\n"
                        f"**{item['course'].code}** - {item['course'].name}\n\n"
                        f"Section: {item['course'].section} | "
                        f"👤 {item['course'].instructor} | "
                        f"Credits: {item['course'].credits}"
                    )
        
        st.write("---")
        
        # Option 3: Download Options
        st.header("📥 Download Timetable")
        
        # Generate text format
        timetable_text = "COURSE TIMETABLE\n" + "="*80 + "\n\n"
        
        # By course
        timetable_text += "ORGANIZED BY COURSE:\n" + "-"*80 + "\n\n"
        for code in sorted(courses_by_code.keys()):
            sections = courses_by_code[code]
            first = sections[0]
            
            timetable_text += f"{code} - {first.name} ({first.credits} credits)\n"
            timetable_text += "-" * 80 + "\n"
            
            for course in sections:
                timetable_text += f"\nSection: {course.section}\n"
                timetable_text += f"Instructor: {course.instructor}\n"
                timetable_text += f"Dates: {course.dates}\n"
                timetable_text += "Schedule:\n"
                
                schedule_by_day = {}
                for slot in course.schedule:
                    day = slot['day']
                    time_str = f"{slot['start']}-{slot['end']}"
                    if day not in schedule_by_day:
                        schedule_by_day[day] = []
                    schedule_by_day[day].append(time_str)
                
                for day, times in schedule_by_day.items():
                    timetable_text += f"  {day}: {', '.join(times)}\n"
                
                timetable_text += "\n"
        
        # By day
        timetable_text += "\n" + "="*80 + "\n\n"
        timetable_text += "ORGANIZED BY DAY:\n" + "-"*80 + "\n\n"
        
        for day in days:
            day_classes = []
            
            for course in courses:
                for slot in course.schedule:
                    if slot['day'] == day:
                        day_classes.append({
                            'start': slot['start'],
                            'end': slot['end'],
                            'course': course
                        })
            
            if day_classes:
                day_classes.sort(key=lambda x: x['start'])
                
                timetable_text += f"\n{day.upper()}:\n"
                timetable_text += "-" * 80 + "\n"
                
                for item in day_classes:
                    timetable_text += f"{item['start']}-{item['end']}: "
                    timetable_text += f"{item['course'].code} ({item['course'].section}) - "
                    timetable_text += f"{item['course'].name} | "
                    timetable_text += f"{item['course'].instructor}\n"
                
                timetable_text += "\n"
        
        # Download buttons
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                label="📄 Download as Text File",
                data=timetable_text,
                file_name="course_timetable.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            # CSV format
            csv_text = "Course Code,Course Name,Section,Instructor,Day,Start Time,End Time,Credits\n"
            for course in courses:
                for slot in course.schedule:
                    csv_text += f"{course.code},{course.name},{course.section},{course.instructor},"
                    csv_text += f"{slot['day']},{slot['start']},{slot['end']},{course.credits}\n"
            
            st.download_button(
                label="📊 Download as CSV",
                data=csv_text,
                file_name="course_timetable.csv",
                mime="text/csv",
                use_container_width=True
            )
        
    else:
        st.error("❌ Could not extract course information from PDF")
        st.write("Please make sure your PDF contains course schedule information in the expected format.")

else:
    st.info("👆 **Upload a PDF to get started!**")
    
    st.write("---")
    
    st.write("### What This Tool Does:")
    st.write("1. 📤 Upload your course timetable PDF")
    st.write("2. 🤖 Automatically extracts all course information")
    st.write("3. 📋 Shows courses organized by code")
    st.write("4. 📅 Shows weekly timetable view")
    st.write("5. 📥 Download in text or CSV format")
    
    st.write("---")
    
    st.write("### Example PDF Format:")
    st.code("""
19EE305 [3 Credits]
Course overview
Basic Electrical Engineering

4H4-2, EEE - LOGESH K
Date: 25-08-2025 to 18-10-2025
Monday: 13:00 - 14:00 14:00 - 15:00
Thursday: 15:00 - 16:00 16:00 - 17:00
    """, language="text")

# Sidebar
with st.sidebar:
    st.header("ℹ️ About")
    st.write("""
This tool automatically reads your course timetable PDF and creates organized views of all courses and schedules.
    """)
    
    st.divider()
    
    st.header("📊 Features")
    st.write("""
✅ Extracts all course details
✅ Shows course list view
✅ Shows weekly timetable view
✅ Download as text or CSV
✅ No manual input needed
    """)
    
    st.divider()
    
    st.header("💡 Use Cases")
    st.write("""
- Quick overview of all courses
- Find what's available each day
- Export to Excel for planning
- Share with friends
    """)
