import streamlit as st
import requests
import json
import base64
import os
import tempfile
from datetime import datetime
from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv
import io
import fitz  # PyMuPDF

# Load environment variables
load_dotenv()

# Set up the page configuration
st.set_page_config(
    page_title="Resume Optimizer & Generator",
    page_icon="📄",
    layout="wide"
)

# Initialize the agent
def get_agent():
    return Agent(
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[],
        description="You are an expert resume optimizer with deep knowledge of various industries and job requirements.",
        instructions="""
        # Resume Enhancement Process
        
        ## Analysis Phase
        1. Analyze the provided job description thoroughly
           - Extract key requirements, skills, and qualifications
           - Identify industry-specific terminology and buzzwords
           - Note preferred experience levels and education requirements
           
        2. Evaluate the current resume (payload) against job requirements
           - Identify strengths that already align with the job description
           - Spot gaps and improvement opportunities
           - Determine which sections need enhancement
        
        ## Enhancement Phase  
        3. Modify the resume content to improve job alignment while preserving core facts:
           - Rephrase experience descriptions using industry-relevant terminology
           - Highlight transferable skills that match job requirements
           - Restructure accomplishments to demonstrate relevant outcomes
           - Ensure all modifications maintain factual accuracy of:
             * Educational background and institutions
             * Certification names and credentials
             * Employment history timeline and company names
             * Core technical skills and technologies
        
        4. DO NOT fabricate or add:
           - New jobs or positions not in original payload
           - Skills or technologies not listed in original payload
           - Educational degrees or certifications not listed in original payload
           - Projects that don't exist in the original payload
        
        ## Scoring and Reporting
        5. Score the original resume against the job description
        6. Score the enhanced resume against the job description
        7. Provide a detailed comparison showing improvements
        
        ## Important Guidelines
        - Focus on professional enhancement through better wording, not factual changes
        - Maintain the person's actual career trajectory and capabilities
        - Use industry-standard terminology appropriate for the target position
        - Eliminate irrelevant content that doesn't support the job application
        - Fix grammatical errors and improve overall professional tone
        """,
        expected_output="""
        # Resume Enhancement Report
        
        ## Job Description Analysis
        {Summary of key requirements and skills from the job description}
        
        ## Original Resume Assessment
        {Brief evaluation of original resume's alignment with job requirements}
        
        ## Enhanced Resume Payload
        ```json
        {Complete enhanced JSON payload with all optimized fields}
        ```
        
        ## Improvement Summary
        - Experience Descriptions: {Specific improvements made}
        - Skills Presentation: {How skills were better aligned}
        - Project Descriptions: {How projects were reframed to match requirements}
        - Overall Language Enhancement: {Terminology improvements}
        
        ## Scoring Comparison
        | Category | Original Score | Enhanced Score | Improvement |
        |----------|---------------|----------------|-------------|
        | Relevant Experience | {score}/100 | {score}/100 | +{points} |
        | Skills Match | {score}/100 | {score}/100 | +{points} |
        | Education & Certs | {score}/100 | {score}/100 | +{points} |
        | Overall Fit | {score}/100 | {score}/100 | +{points} |
        
        ## Overall Match Percentage: {Original score}% → {Enhanced score}%
        
        ## Key Improvements Made
        1. {First major improvement}
        2. {Second major improvement}
        3. {Third major improvement}
        
        ## Unchanged Elements (Core Facts Preserved)
        - All employment history dates and company names
        - Educational credentials and institutions
        - Certification titles
        - Core technical skills
        """,
        add_datetime_to_instructions=True,
        show_tool_calls=True,
        markdown=True,
    )

# Define the Flask API endpoint
API_URL = "http://localhost:5000/generate_resume"

# Function to extract text from PDF
def extract_text_from_pdf(uploaded_file):
    """Extracts text from PDF using PyMuPDF (fitz)"""
    extracted_text = ""
    
    # Read file as a BytesIO stream
    pdf_stream = io.BytesIO(uploaded_file.read())  
    doc = fitz.open("pdf", pdf_stream)  # Open PDF from memory

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        extracted_text += text + "\n"

    return extracted_text

# Helper functions
def download_pdf(pdf_content):
    """Generate a download link for the PDF"""
    b64_pdf = base64.b64encode(pdf_content).decode('utf-8')
    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="resume.pdf">Download Resume PDF</a>'
    return href

def add_dynamic_list(section_name, item_name, key_prefix, default_items=None):
    """Create a dynamic list of input fields"""
    if section_name not in st.session_state:
        st.session_state[section_name] = default_items or [""]
    
    # Display all current items
    for i, item in enumerate(st.session_state[section_name]):
        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.session_state[section_name][i] = st.text_input(
                f"{item_name} {i+1}",
                value=item,
                key=f"{key_prefix}_{i}"
            )
        with col2:
            if i > 0 or (i == 0 and len(st.session_state[section_name]) > 1):
                if st.button("✂️", key=f"del_{key_prefix}_{i}"):
                    st.session_state[section_name].pop(i)
                    st.rerun()
    
    # Button to add new item
    if st.button(f"Add {item_name}", key=f"add_{key_prefix}"):
        st.session_state[section_name].append("")
        st.rerun()

def create_date_duration_input(label, value, key):
    """Create a standardized date duration input with proper formatting"""
    st.write(label)
    
    # Split existing value if it exists
    start_date = ""
    end_date = ""
    
    if value and " - " in value:
        parts = value.split(" - ")
        if len(parts) == 2:
            start_date = parts[0]
            end_date = parts[1]
    
    col1, col2 = st.columns(2)
    with col1:
        month_options = ["", "January", "February", "March", "April", "May", "June", 
                       "July", "August", "September", "October", "November", "December"]
        
        # Start date
        st.write("Start Date")
        start_col1, start_col2 = st.columns(2)
        
        with start_col1:
            # Extract month from start_date if exists
            start_month = ""
            for month in month_options[1:]:  # Skip empty option
                if start_date.startswith(month):
                    start_month = month
                    break
            
            start_month_selected = st.selectbox(
                "Month",
                options=month_options,
                index=month_options.index(start_month) if start_month in month_options else 0,
                key=f"{key}_start_month"
            )
        
        with start_col2:
            # Extract year from start_date if exists
            start_year = ""
            if start_date:
                # Try to extract a 4-digit year
                parts = start_date.replace(",", "").split()
                for part in parts:
                    if part.isdigit() and len(part) == 4:
                        start_year = part
                        break
            
            current_year = datetime.now().year
            years = [""] + [str(year) for year in range(current_year, current_year - 50, -1)]
            
            start_year_selected = st.selectbox(
                "Year",
                options=years,
                index=years.index(start_year) if start_year in years else 0,
                key=f"{key}_start_year"
            )
    
    with col2:
        # End date with multiple current position options
        st.write("End Date")
        
        # Current position options
        current_position_options = ["Present", "Till Date", "Current", "Ongoing"]
        
        # Check if end_date matches any current position indicators
        is_current = False
        current_option = "Present"  # Default if we detect it's current
        
        for option in current_position_options:
            if end_date and end_date.lower() == option.lower():
                is_current = True
                current_option = option
                break
        
        # Option to select if this is a current position
        is_current_position = st.checkbox(
            "Current Position", 
            value=is_current,
            key=f"{key}_is_current"
        )
        
        if is_current_position:
            # If it's a current position, provide options for how to display it
            current_text = st.selectbox(
                "Display As",
                options=current_position_options,
                index=current_position_options.index(current_option) if current_option in current_position_options else 0,
                key=f"{key}_current_text"
            )
            end_month_selected = None
            end_year_selected = None
        else:
            # If not current, show normal date selectors
            end_col1, end_col2 = st.columns(2)
            
            with end_col1:
                # Extract month from end_date if exists and not a current position
                end_month = ""
                if end_date and not is_current:
                    for month in month_options[1:]:  # Skip empty option
                        if end_date.startswith(month):
                            end_month = month
                            break
                
                end_month_selected = st.selectbox(
                    "Month",
                    options=month_options,
                    index=month_options.index(end_month) if end_month in month_options else 0,
                    key=f"{key}_end_month"
                )
            
            with end_col2:
                # Extract year from end_date if exists and not a current position
                end_year = ""
                if end_date and not is_current:
                    # Try to extract a 4-digit year
                    parts = end_date.replace(",", "").split()
                    for part in parts:
                        if part.isdigit() and len(part) == 4:
                            end_year = part
                            break
                
                end_year_selected = st.selectbox(
                    "Year",
                    options=years,
                    index=years.index(end_year) if end_year in years else 0,
                    key=f"{key}_end_year"
                )
    
    # Combine into a properly formatted duration string
    if start_month_selected and start_year_selected:
        formatted_start = f"{start_month_selected} {start_year_selected}"
    else:
        formatted_start = ""
    
    if is_current_position:
        formatted_end = current_text
    elif end_month_selected and end_year_selected:
        formatted_end = f"{end_month_selected} {end_year_selected}"
    else:
        formatted_end = ""
    
    # Construct final duration string
    if formatted_start and formatted_end:
        return f"{formatted_start} - {formatted_end}"
    elif formatted_start:
        return formatted_start
    elif formatted_end:
        return formatted_end
    else:
        return ""

def add_nested_section(section_title, fields, session_key):
    """Create a section with nested fields"""
    st.subheader(section_title)
    
    if session_key not in st.session_state:
        st.session_state[session_key] = [{}]
    
    for i, item in enumerate(st.session_state[session_key]):
        with st.expander(f"{section_title} {i+1}", expanded=i==0):
            for field in fields:
                field_id = field.get('id')
                field_label = field.get('label')
                field_type = field.get('type', 'text')
                
                if field_id not in item:
                    item[field_id] = field.get('default', '')
                
                if field_type == 'text':
                    item[field_id] = st.text_input(
                        field_label, 
                        value=item[field_id],
                        key=f"{session_key}_{i}_{field_id}"
                    )
                elif field_type == 'textarea':
                    item[field_id] = st.text_area(
                        field_label, 
                        value=item[field_id],
                        key=f"{session_key}_{i}_{field_id}"
                    )
                elif field_type == 'duration':
                    # Use the custom date duration input
                    item[field_id] = create_date_duration_input(
                        field_label,
                        item[field_id],
                        f"{session_key}_{i}_{field_id}"
                    )
                elif field_type == 'list':
                    # Initialize as list if it doesn't exist or is not a list
                    list_key = f"{session_key}_{i}_{field_id}"
                    
                    # Ensure the item has a list for this field
                    if field_id not in item or not isinstance(item[field_id], list):
                        item[field_id] = [""]
                    
                    # Initialize the session state for this list
                    if list_key not in st.session_state:
                        st.session_state[list_key] = item[field_id]
                    
                    st.write(field_label)
                    for j, point in enumerate(st.session_state[list_key]):
                        col1, col2 = st.columns([0.9, 0.1])
                        with col1:
                            st.session_state[list_key][j] = st.text_area(
                                f"Point {j+1}",
                                value=point,
                                key=f"{list_key}_{j}",
                                height=100
                            )
                        with col2:
                            if j > 0 or (j == 0 and len(st.session_state[list_key]) > 1):
                                if st.button("✂️", key=f"del_{list_key}_{j}"):
                                    st.session_state[list_key].pop(j)
                                    st.rerun()
                    
                    if st.button(f"Add Point", key=f"add_{list_key}"):
                        st.session_state[list_key].append("")
                        st.rerun()
                    
                    # Update the item with the current list state
                    item[field_id] = st.session_state[list_key]
        
        col1, col2 = st.columns([0.9, 0.1])
        with col2:
            if i > 0 or (i == 0 and len(st.session_state[session_key]) > 1):
                if st.button("Delete", key=f"del_section_{session_key}_{i}"):
                    st.session_state[session_key].pop(i)
                    st.rerun()
    
    if st.button(f"Add {section_title}", key=f"add_section_{session_key}"):
        st.session_state[session_key].append({})
        st.rerun()

def add_skills_section():
    """Add skills section with categories"""
    st.subheader("Technical Skills")
    
    if "skills_categories" not in st.session_state:
        st.session_state.skills_categories = ["Languages", "Frameworks"]
    
    if "skills_data" not in st.session_state:
        st.session_state.skills_data = {
            "Languages": ["Python", "JavaScript"],
            "Frameworks": ["Flask", "React"]
        }
    
    # Display and manage categories
    st.write("Skill Categories")
    cols = st.columns([0.45, 0.45, 0.1])
    with cols[0]:
        new_category = st.text_input("Add New Category")
    with cols[1]:
        if st.button("Add Category") and new_category:
            if new_category not in st.session_state.skills_categories:
                st.session_state.skills_categories.append(new_category)
                st.session_state.skills_data[new_category] = [""]
                st.rerun()
    
    # Display each category and its skills
    for category in list(st.session_state.skills_categories):  # Use list to avoid modification during iteration
        with st.expander(category, expanded=True):
            # Add delete category button
            if st.button("Delete Category", key=f"del_cat_{category}"):
                st.session_state.skills_categories.remove(category)
                if category in st.session_state.skills_data:
                    del st.session_state.skills_data[category]
                st.rerun()
            
            # Skills for this category
            if category not in st.session_state.skills_data:
                st.session_state.skills_data[category] = [""]
            
            for i, skill in enumerate(st.session_state.skills_data[category]):
                cols = st.columns([0.9, 0.1])
                with cols[0]:
                    st.session_state.skills_data[category][i] = st.text_input(
                        f"Skill {i+1}",
                        value=skill,
                        key=f"skill_{category}_{i}"
                    )
                with cols[1]:
                    if i > 0 or (i == 0 and len(st.session_state.skills_data[category]) > 1):
                        if st.button("✂️", key=f"del_skill_{category}_{i}"):
                            st.session_state.skills_data[category].pop(i)
                            st.rerun()
            
            if st.button(f"Add Skill to {category}", key=f"add_skill_{category}"):
                st.session_state.skills_data[category].append("")
                st.rerun()

def extract_json_payload(response_text):
    """Extract the JSON payload from the agent response"""
    # Find the start and end of the JSON payload in the markdown content
    start_index = response_text.find("```json")
    if start_index == -1:
        return None
    
    start_index += 7  # Skip over the ```json
    end_index = response_text.find("```", start_index)
    
    if end_index == -1:
        return None
    
    json_string = response_text[start_index:end_index].strip()
    
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return None

def extract_overall_score(response_text):
    """Extract the overall match percentage from the agent response"""
    # Using regex to find the overall match percentage pattern
    import re
    match = re.search(r"Overall Match Percentage: (\d+)% → (\d+)%", response_text)
    
    if match:
        original_score = int(match.group(1))
        enhanced_score = int(match.group(2))
        return original_score, enhanced_score
    
    return None, None

def get_ats_agent():
    """Create an ATS scoring agent"""
    return Agent(
        model=Gemini(id="gemini-2.0-flash-exp"),
        tools=[],
        description="You are an expert resume scorer with deep knowledge of various industries and job requirements.",
        instructions="""
        - Analyze the provided job description
        - Evaluate the resume against the job requirements
        - Provide a detailed scoring breakdown
        - Calculate an overall match percentage
        """,
        expected_output="""
        # Resume Scoring Report

        ## Job Description Analysis
        {Key requirements and skills from the job description}

        ## Resume Evaluation
        {Detailed analysis of how the resume matches the job requirements}

        ## Scoring Breakdown
        - Relevant Experience: {score}/100
        - Skills Match: {score}/100
        - Education: {score}/100
        - Overall Fit: {score}/100

        ## Overall Match Percentage: {total_score}%
        """,
        add_datetime_to_instructions=True,
        show_tool_calls=True,
        markdown=True,
    )

# Initialize session state for file upload
if 'uploaded_resume' not in st.session_state:
    st.session_state.uploaded_resume = None

def initialize_session_variables():
    """Initialize all session state variables if they don't exist"""
    # Personal info
    if 'full_name' not in st.session_state:
        st.session_state.full_name = ''
    if 'designation' not in st.session_state:
        st.session_state.designation = ''
    if 'email' not in st.session_state:
        st.session_state.email = ''
    if 'mobile' not in st.session_state:
        st.session_state.mobile = ''
    if 'location' not in st.session_state:
        st.session_state.location = ''
    if 'linkedin_url' not in st.session_state:
        st.session_state.linkedin_url = ''
    if 'github_url' not in st.session_state:
        st.session_state.github_url = ''
    if 'summary' not in st.session_state:
        st.session_state.summary = ''
    
    # Other sections
    if 'certifications' not in st.session_state:
        st.session_state.certifications = ['']
    if 'achievements' not in st.session_state:
        st.session_state.achievements = ['']

# Main application
def main():
    # Initialize session variables
    initialize_session_variables()
    
    st.title("Resume Optimizer & Generator")
    st.write("Create a tailored resume for your target job with AI-powered optimization.")
    
    # Create a sidebar for job description and target score
    with st.sidebar:
        st.header("Job Description & Target")
        
        # Option to upload resume PDF
        uploaded_file = st.file_uploader("Upload Existing Resume (PDF)", type=["pdf"])
        if uploaded_file is not None and uploaded_file != st.session_state.uploaded_resume:
            st.session_state.uploaded_resume = uploaded_file
            with st.spinner("Extracting resume content..."):
                try:
                    resume_text = extract_text_from_pdf(uploaded_file)
                    st.success("Resume extracted successfully! Use the content to fill in the form.")
                    st.text_area("Extracted Content", resume_text, height=200)
                except Exception as e:
                    st.error(f"Error extracting PDF: {str(e)}")
        
        job_description = st.text_area(
            "Enter Job Description",
            placeholder="Paste the job description here...",
            height=300
        )
        
        expected_score = st.slider(
            "Target Match Score (%)",
            min_value=50,
            max_value=95,
            value=85,
            step=5,
            help="Set your target matching score against the job description"
        )
    
    # Tabs for different resume sections
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Personal Info", 
        "Skills", 
        "Experience", 
        "Projects", 
        "Education", 
        "Optimize & Generate"
    ])
    
    with tab1:
        st.subheader("Personal Information")
        
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=st.session_state.full_name)
            designation = st.text_input("Job Title/Designation", value=st.session_state.designation)
            email = st.text_input("Email", value=st.session_state.email)
            mobile = st.text_input("Phone Number", value=st.session_state.mobile)
        
        with col2:
            location = st.text_input("Location", value=st.session_state.location)
            linkedin_url = st.text_input("LinkedIn URL", value=st.session_state.linkedin_url)
            github_url = st.text_input("GitHub URL", value=st.session_state.github_url)
        
        st.subheader("Professional Summary")
        summary = st.text_area("Summary", value=st.session_state.summary, height=150)
        
        # Save to session state
        st.session_state.full_name = full_name
        st.session_state.designation = designation
        st.session_state.email = email
        st.session_state.mobile = mobile
        st.session_state.location = location
        st.session_state.linkedin_url = linkedin_url
        st.session_state.github_url = github_url
        st.session_state.summary = summary
    
    with tab2:
        add_skills_section()
    
    with tab3:
        experience_fields = [
            {'id': 'title', 'label': 'Job Title', 'type': 'text'},
            {'id': 'company', 'label': 'Company Name', 'type': 'text'},
            {'id': 'location', 'label': 'Location', 'type': 'text'},
            {'id': 'duration', 'label': 'Duration', 'type': 'duration'},
            {'id': 'responsibilities', 'label': 'Responsibilities & Achievements', 'type': 'list'}
        ]
        add_nested_section("Work Experience", experience_fields, "experience")
    
    with tab4:
        project_fields = [
            {'id': 'title', 'label': 'Project Name', 'type': 'text'},
            {'id': 'link', 'label': 'Project Link', 'type': 'text'},
            {'id': 'type', 'label': 'Project Type', 'type': 'text'},
            {'id': 'duration', 'label': 'Duration', 'type': 'duration'},
            {'id': 'details', 'label': 'Project Details', 'type': 'list'}
        ]
        add_nested_section("Projects", project_fields, "projects")
    
    with tab5:
        education_fields = [
            {'id': 'title', 'label': 'Degree/Qualification', 'type': 'text'},
            {'id': 'university', 'label': 'University/Institution', 'type': 'text'},
            {'id': 'gpa', 'label': 'GPA/Grade', 'type': 'text'},
            {'id': 'duration', 'label': 'Duration', 'type': 'duration'},
            {'id': 'details', 'label': 'Additional Details', 'type': 'list'}
        ]
        add_nested_section("Education", education_fields, "education")
    
    # In your tab6 section, replace the current optimization button and tabs code with this:

    with tab6:
        st.subheader("Certifications & Achievements")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("Certifications")
            add_dynamic_list("certifications", "Certification", "cert")
        
        with col2:
            st.write("Achievements")
            add_dynamic_list("achievements", "Achievement", "achieve")
        
        st.markdown("---")
        st.subheader("Optimize & Generate Resume")
        
        # Initialize session state variables for optimization
        if "show_optimization_tabs" not in st.session_state:
            st.session_state.show_optimization_tabs = False
        if "optimization_report" not in st.session_state:
            st.session_state.optimization_report = None
        if "optimized_payload" not in st.session_state:
            st.session_state.optimized_payload = None
        if "original_score" not in st.session_state:
            st.session_state.original_score = None
        if "enhanced_score" not in st.session_state:
            st.session_state.enhanced_score = None
        
        # Define the optimize function to avoid code repetition
        def optimize_resume():
            if not job_description:
                st.error("Please provide a job description to optimize your resume.")
                return
            
            # Prepare the original data payload
            original_payload = {
                "Full_Name": st.session_state.full_name,
                "Designation": st.session_state.designation,
                "Email": st.session_state.email,
                "Mobile": st.session_state.mobile,
                "Location": st.session_state.location,
                "Linkedin_url": st.session_state.linkedin_url,
                "github_url": st.session_state.github_url,
                "summary": st.session_state.summary,
                "skills_data": st.session_state.skills_data,
                "experience": st.session_state.experience,
                "projects": st.session_state.projects,
                "education": st.session_state.education,
                "certifications": st.session_state.certifications,
                "achievements": st.session_state.achievements
            }
            
            # Display a spinner while optimizing
            with st.spinner("Optimizing your resume to match the job description..."):
                # Run the agent to optimize the resume
                prompt = f"""
                Job Description: {job_description}

                Resume Payload: {json.dumps(original_payload)}

                Expected Score: {expected_score}%

                Please enhance this resume to better match the job description while preserving the core facts. 
                I'm aiming for a match score of at least {expected_score}%.
                """
                
                # Run the agent
                agent = get_agent()
                response = agent.run(prompt)
                
                # Store the response in session state for reference
                st.session_state.optimization_report = response.content
                
                # Extract the optimized JSON payload from the response
                optimized_payload = extract_json_payload(response.content)
                
                # Extract the scores
                original_score, enhanced_score = extract_overall_score(response.content)
                
                if optimized_payload:
                    st.session_state.optimized_payload = optimized_payload
                    st.session_state.original_score = original_score
                    st.session_state.enhanced_score = enhanced_score
                    st.session_state.show_optimization_tabs = True
                    st.rerun()  # Rerun to show the tabs
        
        # Generate payload for optimization button
        if st.button("Optimize Resume for Job", type="primary"):
            optimize_resume()
        
        # Only show tabs if optimization has been done
        if st.session_state.show_optimization_tabs:
            # Display success message with scores
            if st.session_state.original_score is not None and st.session_state.enhanced_score is not None:
                st.success(f"Resume optimized! Original match: {st.session_state.original_score}% → Enhanced match: {st.session_state.enhanced_score}%")
            else:
                st.success("Resume optimized successfully!")
            
            # Create tabs outside the button click logic
            report_tab, generate_tab = st.tabs(["Optimization Report", "Generate PDF"])
            
            with report_tab:
                st.markdown(st.session_state.optimization_report)
            
            with generate_tab:
                # Display the optimized payload for debugging
                if st.checkbox("Show JSON Payload (Debug)"):
                    st.json(st.session_state.optimized_payload)
                
                # Save as JSON option
                if st.button("Save Optimized Resume Data (JSON)"):
                    json_str = json.dumps(st.session_state.optimized_payload, indent=2)
                    st.download_button(
                        label="Download JSON Data",
                        data=json_str,
                        file_name=f"{st.session_state.full_name.replace(' ', '_')}_resume_data.json",
                        mime="application/json"
                    )
                
                # Improved PDF generation
                if st.button("Generate Optimized PDF Resume"):
                    with st.spinner("Generating your optimized resume PDF..."):
                        try:
                            # Get the API endpoint from sidebar
                            api_url = API_URL
                            
                            # First check if the API is available with better error handling
                            try:
                                # Simple connection test with timeout
                                base_url = "/".join(api_url.split("/")[:-1]) or api_url  # Get base URL
                                test_response = requests.get(f"{base_url}/", timeout=3)
                            except requests.exceptions.ConnectionError:
                                st.error(f"Cannot connect to the API server at {base_url}/")
                                st.info("Please make sure the resume generation service is running at the specified URL.")
                                
                                # Provide alternative options
                                st.warning("Alternative options:")
                                st.markdown("""
                                1. Try using a different API endpoint in the sidebar
                                2. Save the JSON data and use it with a different resume generator
                                3. Use the optimized content to manually update your resume
                                """)
                                return
                            except Exception as e:
                                st.error(f"Error connecting to API: {str(e)}")
                                return
                            
                            # Ensure the payload is properly formatted
                            if not isinstance(st.session_state.optimized_payload, dict):
                                st.error("Invalid payload format. Please optimize your resume again.")
                                return
                            
                            # Send the request with improved error handling
                            try:
                                st.info(f"Connecting to API at: {api_url}")
                                
                                api_response = requests.post(
                                    api_url, 
                                    json=st.session_state.optimized_payload, 
                                    timeout=30,  # Allow up to 30 seconds for PDF generation
                                    headers={"Content-Type": "application/json"}
                                )
                                
                                # Check if the request was successful
                                if api_response.status_code == 200:
                                    # Get the PDF content
                                    pdf_content = api_response.content
                                    
                                    # Store PDF content in session state
                                    st.session_state.generated_pdf_content = pdf_content
                                    
                                    # Display success message
                                    st.success("Resume PDF generated successfully!")
                                    
                                    # Create download button
                                    st.download_button(
                                        label="Download Optimized Resume",
                                        data=pdf_content,
                                        file_name=f"{st.session_state.full_name.replace(' ', '_')}_resume.pdf",
                                        mime="application/pdf"
                                    )
                                    
                                    # Add button for checking ATS score (outside the generate PDF button scope)
                                    st.session_state.show_ats_score_button = True
                                else:
                                    st.error(f"Error generating PDF: Status code {api_response.status_code}")
                                    st.write("Response from server:")
                                    st.code(api_response.text[:500], language="text")
                                    
                                    # Fallback options
                                    st.info("You can still use the JSON data to generate your resume with another tool.")
                            except requests.exceptions.Timeout:
                                st.error("Request timed out. The PDF generation is taking too long.")
                                st.info("Try again later or use the JSON data option.")
                            except requests.exceptions.RequestException as e:
                                st.error(f"Request failed: {str(e)}")
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc(), language="python")
                            
                            # Provide helpful message
                            st.info("You can still use the optimized content to manually update your resume.")

                # Add this outside the "Generate Optimized PDF Resume" button to persist across reruns
                if st.session_state.get("show_ats_score_button", False):
                    if st.button("Check ATS Score of Generated PDF"):
                        with st.spinner("Calculating ATS score of the generated PDF..."):
                            try:
                                # Get PDF content from session state
                                pdf_content = st.session_state.get("generated_pdf_content")
                                
                                if pdf_content is None:
                                    st.error("PDF content not found. Please generate the PDF again.")
                                    return
                                
                                # Extract text from the PDF
                                pdf_text = extract_text_from_pdf(pdf_content)
                                
                                # Store in session state to show we're checking ATS score
                                st.session_state.checking_ats_score = True
                                
                                # Run the ATS scoring agent with the extracted text
                                ats_agent = get_ats_agent()
                                job_description = st.session_state.get('job_description', '')
                                
                                if not job_description:
                                    st.error("Please provide a job description to check ATS score.")
                                else:
                                    prompt = f"""
                                    Job Description: {job_description}

                                    Resume Text: {pdf_text}

                                    Please score this resume against the job description.
                                    """
                                    
                                    response = ats_agent.run(prompt)
                                    
                                    # Store response in session state
                                    st.session_state.pdf_ats_score_response = response.content
                                    
                                    # Extract overall score using regex
                                    import re
                                    match = re.search(r"Overall Match Percentage: (\d+)%", response.content)
                                    if match:
                                        score = int(match.group(1))
                                        expected_score = st.session_state.get('expected_score', 85)
                                        
                                        # Store score in session state
                                        st.session_state.pdf_ats_score = score
                                    
                                    # Force a rerun to display results
                                    st.rerun()
                            
                            except Exception as e:
                                st.error(f"Error calculating PDF ATS score: {str(e)}")
                                import traceback
                                st.code(traceback.format_exc(), language="python")

                # Display ATS score results if available
                if st.session_state.get("checking_ats_score", False) and st.session_state.get("pdf_ats_score_response"):
                    score = st.session_state.get("pdf_ats_score")
                    expected_score = st.session_state.get('expected_score', 85)
                    
                    if score is not None:
                        # Create progress bar to visualize score
                        st.metric("PDF ATS Match Score", f"{score}%")
                        st.progress(score/100)
                        
                        if score < expected_score:
                            st.warning(f"Your PDF resume scores {score}%, which is below your target of {expected_score}%.")
                        else:
                            st.success(f"Your PDF resume scores {score}%, which meets your target of {expected_score}%!")
                    
                    # Display the full scoring report
                    with st.expander("View Full PDF ATS Scoring Report", expanded=True):
                        st.markdown(st.session_state.pdf_ats_score_response)
                            
# Initialize ATS scoring tab
if "ats_score" not in st.session_state:
    st.session_state.ats_score = None

# Fix for tab7 ATS Score tab
def add_ats_scoring_tab():
    tab7 = st.sidebar.expander("ATS Score Check")

    with tab7:
        st.write("Check your resume's ATS score against the job description")
        
        # Add information about what ATS scoring is - NEW
        with st.expander("What is ATS scoring?"):
            st.write("""
            **Applicant Tracking System (ATS)** scoring measures how well your resume matches the job description. 
            A higher score means your resume is more likely to pass through automated filters used by employers.
            """)
        
        # Ensure there's a job description
        job_description = st.session_state.get('job_description', '')
        expected_score = st.session_state.get('expected_score', 85)
        
        if not job_description:
            st.warning("Please enter a job description in the sidebar first.")
        
        if st.button("Calculate ATS Score"):
            if not job_description:
                st.error("Please provide a job description to check ATS score.")
            else:
                with st.spinner("Calculating ATS score..."):
                    try:
                        # Prepare the current resume data
                        current_payload = {
                            "Full_Name": st.session_state.full_name,
                            "Designation": st.session_state.designation,
                            "Email": st.session_state.email,
                            "Mobile": st.session_state.mobile,
                            "Location": st.session_state.location,
                            "Linkedin_url": st.session_state.linkedin_url,
                            "github_url": st.session_state.github_url,
                            "summary": st.session_state.summary,
                            "skills_data": st.session_state.skills_data,
                            "experience": st.session_state.experience,
                            "projects": st.session_state.projects,
                            "education": st.session_state.education,
                            "certifications": st.session_state.certifications,
                            "achievements": st.session_state.achievements
                        }
                        
                        # Run the ATS scoring agent
                        ats_agent = get_ats_agent()
                        prompt = f"""
                        Job Description: {job_description}

                        Resume Payload: {json.dumps(current_payload)}

                        Please score this resume against the job description.
                        """
                        
                        response = ats_agent.run(prompt)
                        st.session_state.ats_score = response.content
                        
                        # Extract overall score using regex
                        import re
                        match = re.search(r"Overall Match Percentage: (\d+)%", response.content)
                        if match:
                            score = int(match.group(1))
                            
                            # Create progress bar to visualize score - NEW
                            st.metric("ATS Match Score", f"{score}%")
                            progress_color = "green" if score >= expected_score else "orange" if score >= 70 else "red"
                            st.progress(score/100)
                            
                            if score < expected_score:
                                st.warning(f"Your current resume scores {score}%, which is below your target of {expected_score}%. Consider optimizing it.")
                            else:
                                st.success(f"Your current resume scores {score}%, which meets your target of {expected_score}%!")
                            
                            # Add recommendations based on score - NEW
                            if score < 70:
                                st.error("Your resume needs significant improvement to match this job.")
                            elif score < expected_score:
                                st.warning("Click 'Optimize Resume for Job' in the main section to improve your match.")
                        else:
                            st.warning("Could not extract score from response. See full report below.")
                        
                        # Display the full scoring report
                        with st.expander("View Full ATS Scoring Report", expanded=True):
                            st.markdown(response.content)
                    
                    except Exception as e:
                        st.error(f"Error calculating ATS score: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc(), language="python")

# Run the main application
if __name__ == "__main__":
    main()  