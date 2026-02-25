import streamlit as st
import pdfplumber
from datetime import datetime, time
import re
from itertools import product

# Page config
st.set_page_config(page_title="Smart Course Scheduler", page_icon="📚", layout="wide")

# Title
st.title("📚 Smart Course Scheduler")
st.write("Select courses and leave days - see all possible schedules!")

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

def find_all_schedules(course_sections_dict, max_results=50):
    """
    Find ALL conflict-free schedules
    Returns list of valid schedules
    """
    course_codes = list(course_sections_dict.keys())
    all_sections = [course_sections_dict[code] for code in course_codes]
    
    valid_schedules = []
    
    # Try all combinations (limit to prevent timeout)
    count = 0
    for combination in product(*all_sections):
        count += 1
        if count > 10000:  # Safety limit
            break
            
        # Check if this combination has conflicts
        has_any_conflict = False
        for i in range(len(combination)):
            for j in range(i + 1, len(combination)):
                if has_conflict(combination[i], combination[j]):
                    has_any_conflict = True
                    break
            if has_any_conflict:
                break
        
        # If no conflicts, add to valid schedules
        if not has_any_conflict:
            valid_schedules.append(list(combination))
            if len(valid_schedules) >= max_results:
                break
    
    return valid_schedules

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
            st.success(f"✅ Selected {len(selected_course_codes)} courses")
            
            # Step 2: Select Leave Days
            st.header("Step 2: Select Leave Days (Optional)")
            st.write("Choose days you want off - we'll find schedules without classes on these days.")
            
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
                st.write("** **")
                if st.checkbox("Friday", key="leave_friday"):
                    leave_days.append("Friday")
                if st.checkbox("Saturday", key="leave_saturday"):
                    leave_days.append("Saturday")
                if st.checkbox("Sunday", key="leave_sunday"):
                    leave_days.append("Sunday")
            
            if leave_days:
                st.info(f"🏖️ Days off: {', '.join(leave_days)}")
            else:
                st.info("✅ No leave days selected - all days available")
            
            # Step 3: Find All Possibilities
            st.header("Step 3: Find All Possible Schedules")
            
            if st.button("🔍 Find All Possibilities", type="primary", use_container_width=True):
                
                with st.spinner("Searching for all possible schedules..."):
                    # Filter sections based on leave days
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
                            if not has_class_on_leave:
                                filtered_sections[code].append(course)
                    
                    # Check if any course has no valid sections
                    no_sections_courses = [code for code, sections in filtered_sections.items() if len(sections) == 0]
                    
                    if no_sections_courses:
                        st.error(f"❌ Cannot find schedules!")
                        st.write(f"**Problem:** These courses have NO sections available on your chosen days:")
                        for code in no_sections_courses:
                            st.write(f"• {code}")
                        st.write("**Solution:** Remove some leave days or remove these courses")
                    else:
                        # Find all valid schedules
                        all_schedules = find_all_schedules(filtered_sections)
                        
                        if all_schedules:
                            st.success(f"✅ **Found {len(all_schedules)} Possible Schedule(s)!**")
                            
                            # Show each possibility
                            for idx, schedule in enumerate(all_schedules, 1):
                                with st.expander(f"📋 **Possibility #{idx}** - Click to view details", expanded=(idx==1)):
                                    
                                    # Show teachers for this possibility
                                    st.subheader("👥 Teachers in this schedule:")
                                    
                                    teacher_list = []
                                    for course in schedule:
                                        teacher_list.append(f"**{course.code}**: {course.instructor}")
                                    
                                    cols = st.columns(2)
                                    for i, teacher_info in enumerate(teacher_list):
                                        with cols[i % 2]:
                                            st.write(teacher_info)
                                    
                                    st.write("---")
                                    
                                    # Show weekly timetable
                                    st.subheader("📅 Weekly Timetable:")
                                    
                                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                                    
                                    for day in days:
                                        day_schedule = []
                                        for course in schedule:
                                            for slot in course.schedule:
                                                if slot['day'] == day:
                                                    day_schedule.append({
                                                        'start': slot['start'],
                                                        'end': slot['end'],
                                                        'course': course
                                                    })
                                        
                                        if day_schedule:
                                            day_schedule.sort(key=lambda x: x['start'])
                                            
                                            st.write(f"**{day}:**")
                                            for item in day_schedule:
                                                st.write(
                                                    f"  🕐 {item['start']}-{item['end']} | "
                                                    f"{item['course'].code} ({item['course'].section}) | "
                                                    f"👤 {item['course'].instructor}"
                                                )
                                        elif day not in leave_days:
                                            st.write(f"**{day}:** Free day")
                                    
                                    st.write("---")
                                    
                                    # Course details
                                    st.subheader("📚 Course Details:")
                                    
                                    for course in schedule:
                                        st.write(f"**{course.code}** - {course.name}")
                                        st.write(f"  Section: {course.section} | Instructor: {course.instructor} | Credits: {course.credits}")
                                    
                                    # Download button for this schedule
                                    schedule_text = f"SCHEDULE POSSIBILITY #{idx}\n" + "="*60 + "\n\n"
                                    schedule_text += "TEACHERS:\n" + "-"*60 + "\n"
                                    for course in schedule:
                                        schedule_text += f"{course.code}: {course.instructor}\n"
                                    schedule_text += "\n"
                                    
                                    schedule_text += "WEEKLY TIMETABLE:\n" + "-"*60 + "\n\n"
                                    for day in days:
                                        day_schedule = []
                                        for course in schedule:
                                            for slot in course.schedule:
                                                if slot['day'] == day:
                                                    day_schedule.append((slot['start'], slot['end'], course))
                                        
                                        if day_schedule:
                                            day_schedule.sort(key=lambda x: x[0])
                                            schedule_text += f"{day}:\n"
                                            for start, end, course in day_schedule:
                                                schedule_text += f"  {start}-{end}: {course.code} ({course.section}) - {course.instructor}\n"
                                        elif day not in leave_days:
                                            schedule_text += f"{day}: Free day\n"
                                    
                                    schedule_text += "\n" + "="*60 + "\n"
                                    
                                    st.download_button(
                                        label=f"📥 Download Possibility #{idx}",
                                        data=schedule_text,
                                        file_name=f"schedule_possibility_{idx}.txt",
                                        mime="text/plain",
                                        key=f"download_{idx}"
                                    )
                        
                        else:
                            st.error("❌ **No Conflict-Free Schedules Found**")
                            st.write("**Possible reasons:**")
                            st.write("• All combinations have time conflicts")
                            st.write("• Your leave days are too restrictive")
                            st.write("• Try removing some leave days")
                            st.write("• Try removing a course")
        
        else:
            st.info("👆 **Select courses in Step 1** to continue")

else:
    st.info("👆 **Upload your course timetable PDF to get started!**")
    
    st.write("---")
    st.write("### How It Works:")
    st.write("1. 📤 Upload your PDF timetable")
    st.write("2. ✅ Select courses you want to take")
    st.write("3. 🏖️ Choose days you want off (optional)")
    st.write("4. 🔍 Click 'Find All Possibilities'")
    st.write("5. 📋 See ALL possible schedules with teacher lists")
    st.write("6. 📥 Download your favorite schedule")

# Sidebar
with st.sidebar:
    st.header("✨ How This Works")
    st.write("""
This tool finds ALL possible conflict-free schedules based on:

✅ Your selected courses
✅ Your leave days
✅ No time conflicts

For each possibility, you'll see:
- Which teachers you'll have
- Complete weekly timetable
- All course details
    """)
    
    st.divider()
    
    st.header("💡 Understanding Results")
    st.write("""
**Possibility #1, #2, #3...**
Each possibility is a different combination of course sections that works.

Different possibilities = different teachers or different time arrangements.
    """)
    
    st.divider()
    
    st.header("🎯 Tips")
    st.write("""
- More leave days = fewer possibilities
- Fewer courses = more possibilities
- If you get too many results, add more leave days to narrow down
- Compare teacher combinations to pick your favorite
    """)
