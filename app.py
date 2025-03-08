from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import jinja2
import subprocess
import os
import json
import tempfile
import shutil
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Create a Jinja2 environment for LaTeX template rendering
latex_jinja_env = jinja2.Environment(
    block_start_string=r'\BLOCK{',
    block_end_string=r'}',
    variable_start_string=r'\VAR{',
    variable_end_string=r'}',
    comment_start_string=r'\#{',
    comment_end_string=r'}',
    line_statement_prefix=r'%%',
    line_comment_prefix=r'%#',
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader(os.path.abspath('.'))
)

# Function to write template to file
def write_latex_template():
    latex_template = r"""
\documentclass[11pt,letterpaper]{article}

% Essential packages
\usepackage[margin=0.7in]{geometry}
\usepackage{array}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{tabularx}
\usepackage{tikz}
\usepackage{hyperref}
\usepackage{fontawesome}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{multicol}
\usepackage{ragged2e}


% Define colors - Professional tech colors
\definecolor{primary}{RGB}{0, 79, 128}    % Deep blue
\definecolor{secondary}{RGB}{50, 120, 180}  % Medium blue
\definecolor{accent}{RGB}{120, 170, 217}   % Light blue
\definecolor{lightgray}{RGB}{245, 245, 245}
\definecolor{darkgray}{RGB}{80, 80, 80}

% Hyperlink setup
\hypersetup{
    colorlinks=true,
    linkcolor=primary,
    urlcolor=secondary,
    pdftitle={Software Engineer Resume},
    pdfauthor={\VAR{Full_Name}}
}

% Set page style
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[C]{\thepage}

% Section formatting
\titleformat{\section}
  {\Large\bfseries\color{primary}}
  {}{0em}{}
  [{\color{primary}\titlerule[1pt]}]
\titlespacing*{\section}{0pt}{12pt}{6pt}

\titleformat{\subsection}
  {\bfseries\color{secondary}}
  {}{0em}{}
\titlespacing*{\subsection}{0pt}{8pt}{4pt}

% Custom commands
\newcommand{\headerName}[1]{{\fontsize{22pt}{24pt}\selectfont\textbf{\textcolor{primary}{#1}}}}
\newcommand{\headerTitle}[1]{{\fontsize{14pt}{16pt}\selectfont\textcolor{secondary}{#1}}}

\newcommand{\jobTitle}[2]{
  \textbf{\textcolor{primary}{#1}} \hfill \textit{#2}\\
}

\newcommand{\companyInfo}[2]{
  \textit{#1} \hfill #2\\
}

\newcommand{\bulletItem}[1]{
  \item #1
}

\newcommand{\customBullets}[1]{
  \begin{itemize}[leftmargin=*,label=\textcolor{secondary}{\scriptsize\textbullet},itemsep=2pt,parsep=0pt]
    #1
  \end{itemize}
}

\setlength{\parindent}{0pt}


\begin{document}

% Header section
\begin{minipage}[t]{0.6\textwidth}
    \headerName{\VAR{Full_Name}}\\[4pt]
    \headerTitle{\VAR{Designation}}\\[4pt]
    % \textcolor{darkgray}{Backend Systems \& Distributed Computing Specialist}
  \end{minipage}
  \begin{minipage}[t]{0.4\textwidth}
    \begin{flushright}
      \begin{tabular}{rl}
        \textcolor{primary}{\faEnvelope} & \VAR{Email} \\
        \textcolor{primary}{\faPhone} & \VAR{Mobile} \\
        \textcolor{primary}{\faMapMarker} & \VAR{Location}\\
        \textcolor{primary}{\faLinkedin} & \url{\VAR{Linkedin_url}} \\
        \textcolor{primary}{\faGithub} & \url{\VAR{github_url}}
      \end{tabular}
    \end{flushright}
  \end{minipage}

  \vspace{10pt}
  \begin{center}
  \begin{tikzpicture}
  \draw[primary, fill=primary] (0,0) rectangle (\textwidth,1.5pt);
  \end{tikzpicture}
  \end{center}
  \vspace{4pt}


% Professional summary
\section{PROFESSIONAL SUMMARY}
\VAR{summary}

% Skills section
\section{TECHNICAL SKILLS}

\begin{multicols}{2}

%%for category, skills in skills_data.items()
    %%if loop.index0 % 2 == 0 and not loop.first
    \columnbreak
    %%endif
   
    \subsection{\VAR{category}}
    \customBullets{
      %%for skill in skills
      \bulletItem{\VAR{skill}}
      %%endfor
    }
%%endfor

\end{multicols}

\section{PROFESSIONAL EXPERIENCE}

%%for job in experience
\jobTitle{\VAR{job.title}}{\VAR{job.duration}}
\companyInfo{\VAR{job.company}}{\VAR{job.location}}
\customBullets{
  %%for point in job.responsibilities
  \bulletItem{\VAR{point}}
  %%endfor
}

\vspace{8pt}
%%endfor

% Projects section
\section{NOTABLE PROJECTS}

%%for project in projects
\jobTitle{\VAR{project.title}}{\VAR{project.duration}}
\companyInfo{\VAR{project.link}}{\VAR{project.type}}
\customBullets{
  %%for point in project.details
  \bulletItem{\VAR{point}}
  %%endfor
}
\vspace{8pt}
%%endfor

% Education section
\section{EDUCATION}

%%for degree in education
\jobTitle{\VAR{degree.title}}{\VAR{degree.duration}}
\companyInfo{\VAR{degree.university}}{\VAR{degree.gpa}}
\customBullets{
  %%for point in degree.details
  \bulletItem{\VAR{point}}
  %%endfor
}
\vspace{4pt}
%%endfor

% Certifications section
\section{CERTIFICATIONS \& ACHIEVEMENTS}
\begin{multicols}{2}
\customBullets{
  %%for cert in certifications
  \bulletItem{\VAR{cert}}
  %%endfor
}

\columnbreak

\customBullets{
  %%for achievement in achievements
  \bulletItem{\VAR{achievement}}
  %%endfor
}
\end{multicols}


\vspace{-0.3cm}
\begin{center}
\textit{\textcolor{secondary}{References available upon request}}
\end{center}

\end{document}
"""
    with open('resume_template.tex', 'w') as f:
        f.write(latex_template)

# Function to thoroughly sanitize LaTeX input
def sanitize_latex(text):
    if not isinstance(text, str):
        return text
    
    # Replace backslashes first
    text = text.replace('\\', '\\textbackslash{}')
    
    # Replace special LaTeX characters
    replacements = {
        '$': '\\$',
        '%': '\\%',
        '&': '\\&',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
        '<': '\\textless{}',
        '>': '\\textgreater{}',
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    # Fix common issues with LaTeX
    # Replace consecutive spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    return text

# Process all data recursively
def process_data(obj):
    if isinstance(obj, dict):
        return {k: process_data(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_data(item) for item in obj]
    else:
        return sanitize_latex(obj)

@app.route('/generate_resume', methods=['POST'])
def generate_resume():
    try:
        # Get form data from request
        data = request.json
        
        # Create a copy of the data for debugging
        with open('debug_input.json', 'w') as f:
            json.dump(data, f, indent=2)
        
        # Process and sanitize all data
        processed_data = process_data(data)
        
        # Save the processed data for debugging
        with open('debug_processed.json', 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        # Create a temporary directory for the resume generation
        temp_dir = tempfile.mkdtemp()
        
        # Create the resume template file
        write_latex_template()
        shutil.copy('resume_template.tex', os.path.join(temp_dir, 'resume_template.tex'))
        
        # Change to the temporary directory
        original_dir = os.getcwd()
        os.chdir(temp_dir)
        
        # Render the LaTeX template with the provided data
        template = latex_jinja_env.get_template('resume_template.tex')
        rendered_tex = template.render(**processed_data)
        
        # Write the rendered LaTeX to a file
        with open('resume.tex', 'w') as f:
            f.write(rendered_tex)
            
        # Copy the tex file for debugging
        shutil.copy('resume.tex', os.path.join(original_dir, 'debug_resume.tex'))
        
        # Compile the LaTeX file to PDF using pdflatex with nonstopmode
        process = subprocess.run(
            ['pdflatex', '-interaction=nonstopmode', 'resume.tex'], 
            capture_output=True, 
            text=True,
            check=False  # Don't raise an exception on non-zero return
        )
        
        # Save the log for debugging regardless of success
        with open(os.path.join(original_dir, 'latex_compile.log'), 'w') as f:
            f.write(process.stdout)
            f.write(process.stderr)
        
        # Try a second compilation to resolve references (if first one succeeded)
        if process.returncode == 0:
            subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', 'resume.tex'],
                check=False
            )
        
        # Check if PDF was generated
        if not os.path.exists('resume.pdf'):
            os.chdir(original_dir)
            shutil.rmtree(temp_dir)
            return jsonify({
                'error': 'Failed to generate PDF', 
                'details': 'Check latex_compile.log for details'
            }), 500
        
        # Copy the PDF to a known location in the original directory
        shutil.copy('resume.pdf', os.path.join(original_dir, 'resume.pdf'))
        
        # Change back to the original directory and clean up
        os.chdir(original_dir)
        shutil.rmtree(temp_dir)
        
        # Return the PDF file
        return send_file('resume.pdf', as_attachment=True)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # Write error details to a log file
        with open('error.log', 'w') as f:
            f.write(str(e) + '\n')
            f.write(error_details)
            
        return jsonify({
            'error': str(e),
            'details': 'Check error.log for more information'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)