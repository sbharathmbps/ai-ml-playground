from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load model
model = SentenceTransformer(
    "perplexity-ai/pplx-embed-v1-0.6B",
    trust_remote_code=True
)

def embedding(resume, jobs):
    # Generate embeddings
    resume_embedding = model.encode(resume)

    job_embeddings = model.encode(jobs)

    # Compute similarity
    scores = cosine_similarity(
        [resume_embedding],
        job_embeddings
    )[0]

    # Rank jobs
    ranked_jobs = sorted(
        zip(jobs, scores),
        key=lambda x: x[1],
        reverse=True
    )

    # Print results
    for job, score in ranked_jobs[:3]:
        print("Similarity:", round(score,3))
        print(job[:200], "...\n")


if __name__=="__main__": 

    job_description = ["""JOB DESCRIPTION 1 – MACHINE LEARNING ENGINEER 

Role Overview
We are looking for an experienced Machine Learning Engineer to design and deploy machine learning models for large-scale production systems. The candidate will work closely with data scientists and engineering teams to build intelligent applications focused on computer vision and predictive analytics.

Responsibilities

• Design and implement machine learning models for image recognition and object detection.
• Build scalable ML pipelines for data preprocessing, feature engineering, and model training.
• Optimize deep learning models using frameworks such as TensorFlow or PyTorch.
• Deploy trained models into production environments using containerization tools.
• Collaborate with data engineers to process large datasets efficiently.

Required Skills

• Strong programming skills in Python
• Experience with Machine Learning and Deep Learning algorithms
• Hands-on experience with TensorFlow or PyTorch
• Knowledge of Computer Vision techniques
• Experience working with SQL databases

Preferred Skills

• Experience with Docker and ML deployment pipelines
• Familiarity with cloud platforms such as AWS or GCP
• Knowledge of model monitoring and optimization techniques

Experience Required

3–6 years of experience in machine learning or AI development""",

"""JOB DESCRIPTION 2 – DATA SCIENTIST 

Role Overview
We are seeking a Data Scientist who will analyze complex datasets and develop predictive models that support business decision-making. The candidate will apply machine learning techniques to extract insights and build scalable analytics solutions.

Responsibilities

• Analyze structured and unstructured datasets to identify patterns and insights.
• Develop predictive models using machine learning algorithms.
• Perform feature engineering and data preprocessing tasks.
• Communicate findings to stakeholders through reports and dashboards.
• Work with cross-functional teams to implement data-driven solutions.

Required Skills

• Proficiency in Python and data science libraries such as pandas and scikit-learn
• Strong understanding of machine learning algorithms
• Experience with SQL and data querying
• Statistical analysis and data visualization skills

Preferred Skills

• Experience with deep learning frameworks
• Familiarity with big data technologies such as Spark
• Experience with cloud-based analytics platforms

Experience Required

2–5 years of experience in data science or analytics""",

"""JOB DESCRIPTION 3 – AI ENGINEER 

Role Overview
We are hiring an AI Engineer responsible for designing and implementing intelligent systems using machine learning and AI techniques.

Responsibilities

• Develop AI models for automation and decision-making systems.
• Design algorithms that process and analyze large datasets.
• Implement machine learning models and integrate them into applications.
• Collaborate with engineering teams to deploy AI features.

Required Skills

• Strong programming skills in Python or similar languages
• Knowledge of machine learning algorithms and neural networks
• Experience with AI frameworks and libraries

Preferred Skills

• Experience with natural language processing or computer vision
• Understanding of model optimization techniques

Experience Required

2–4 years of experience in AI or software engineering""",

"""JOB DESCRIPTION 4 – SENIOR DATA ANALYST 

Role Overview
We are seeking a Senior Data Analyst to transform complex datasets into meaningful insights that support strategic decision-making.

Responsibilities

• Analyze large datasets using SQL and Python.
• Build dashboards using Tableau or Power BI.
• Perform data cleaning and transformation tasks.
• Generate analytical reports for business stakeholders.

Required Skills

• Strong SQL querying skills
• Experience with Python for data analysis
• Expertise in Tableau or Power BI
• Strong statistical analysis skills

Preferred Skills

• Experience with data warehousing systems
• Knowledge of predictive analytics techniques""",

"""JOB DESCRIPTION 5 – BUSINESS INTELLIGENCE ANALYST 

Role Overview
The Business Intelligence Analyst will design reporting solutions and dashboards that help organizations monitor performance and identify business opportunities.

Responsibilities

• Develop BI dashboards and reports.
• Work with business teams to understand analytics requirements.
• Extract data using SQL queries.
• Deliver insights that support operational improvements.

Required Skills

• SQL and database knowledge
• Experience with BI tools such as Power BI or Tableau
• Strong analytical and problem-solving skills""",

"""JOB DESCRIPTION 6 – JUNIOR DATA SCIENTIST 

Role Overview
We are hiring a Junior Data Scientist to support machine learning and data analytics projects.

Responsibilities

• Perform statistical analysis on datasets.
• Build simple machine learning models.
• Assist in data preprocessing and feature engineering.

Required Skills

• Python programming
• Knowledge of statistics and machine learning concepts
• Experience with data visualization tools""",

"""JOB DESCRIPTION 7 – BACKEND ENGINEER 
Role Overview
We are looking for a Backend Engineer responsible for building scalable backend systems and APIs for high-performance applications.

Responsibilities

• Design and develop RESTful APIs using Java and Spring Boot.
• Implement microservices architecture for distributed applications.
• Work with relational databases such as MySQL or PostgreSQL.
• Deploy applications using Docker and Kubernetes.

Required Skills

• Strong programming skills in Java
• Experience with Spring Boot and microservices architecture
• Knowledge of REST APIs and database systems
• Familiarity with Docker containerization""",

"""JOB DESCRIPTION 8 – SOFTWARE ENGINEER 

Role Overview
The Software Engineer will develop backend services and maintain scalable web applications.

Responsibilities

• Build backend services using Java or Python.
• Maintain APIs and backend systems for web applications.
• Work with databases and ensure application performance.

Required Skills

• Programming experience in Java or Python
• Database management knowledge""",

"""JOB DESCRIPTION 9 – FULL STACK DEVELOPER 

Role Overview
Seeking a Full Stack Developer to build and maintain web applications.

Responsibilities

• Develop backend APIs and services.
• Work with frontend frameworks and databases.
• Collaborate with cross-functional teams.

Required Skills

• Experience in web development technologies
• Knowledge of backend programming and databases""",

"""JOB DESCRIPTION 10 – DEVOPS ENGINEER 

Role Overview
We are looking for a DevOps Engineer responsible for managing cloud infrastructure and automating deployment pipelines.

Responsibilities

• Build CI/CD pipelines for application deployment.
• Manage containerized applications using Docker and Kubernetes.
• Automate infrastructure using Terraform.

Required Skills

• AWS cloud infrastructure
• Docker and Kubernetes
• CI/CD tools such as Jenkins""",

"""JOB DESCRIPTION 11 – CLOUD ENGINEER 

Role Overview
The Cloud Engineer will manage cloud infrastructure and deployment automation.

Responsibilities

• Configure AWS cloud resources.
• Implement containerization strategies.
• Monitor cloud services.""",

"""JOB DESCRIPTION 12 – SITE RELIABILITY ENGINEER 

Role Overview
Seeking an SRE responsible for improving system reliability and monitoring infrastructure.

Responsibilities

• Monitor system performance.
• Automate infrastructure tasks.
• Ensure system uptime."""]




#     resume = """RESUME 1 – MACHINE LEARNING ENGINEER

# Name: Rahul Sharma
# Location: Bangalore, India
# Email: [rahul.sharma@email.com](mailto:rahul.sharma@email.com)

# Professional Summary
# Machine Learning Engineer with 5 years of experience designing and deploying scalable AI solutions. Experienced in building end-to-end machine learning pipelines including data preprocessing, feature engineering, model training, evaluation, and deployment. Strong experience in computer vision and deep learning frameworks.

# Skills
# Python, Machine Learning, Deep Learning, Computer Vision, TensorFlow, PyTorch, OpenCV, SQL, Data Processing, Feature Engineering, Model Deployment, Docker, Git

# Experience

# Machine Learning Engineer – TechVision AI (2020–Present)

# • Built computer vision models for object detection and image classification.
# • Developed scalable machine learning pipelines using Python and PyTorch.
# • Optimized deep learning models for performance and production deployment.

# Data Analyst – Insight Analytics (2018–2020)

# • Conducted exploratory data analysis and built predictive models using Python.
# • Worked with SQL databases to extract and transform datasets.

# Education

# M.Tech in Artificial Intelligence – IIT Hyderabad

# """

#     resume = """RESUME 2 – DATA ANALYST

# Name: Priya Nair
# Location: Chennai, India

# Professional Summary
# Data Analyst with 4 years of experience analyzing large datasets and creating dashboards to support business decisions. Strong expertise in SQL, Python, Tableau, and Power BI for business intelligence reporting.

# Skills
# Python, SQL, Tableau, Power BI, Excel, Data Visualization, Data Cleaning, Statistics, Business Intelligence

# Experience

# Data Analyst – Business Insight Solutions (2021–Present)

# • Built dashboards using Tableau and Power BI to visualize business metrics.
# • Analyzed datasets using SQL queries and Python.
# • Generated business reports and insights for management teams.

# Education

# MBA in Business Analytics – Anna University"""

    resume = """RESUME 3 – BACKEND SOFTWARE ENGINEER

Name: Arjun Patel
Location: Hyderabad, India
Email: [arjun.patel@email.com](mailto:arjun.patel@email.com)
Phone: +91 9876543210

Professional Summary
Backend Software Engineer with over 6 years of experience designing, developing, and maintaining scalable backend systems and microservices-based architectures. Skilled in building high-performance APIs, optimizing database queries, and deploying containerized applications in cloud environments.

Technical Skills
Java, Python, Spring Boot, Microservices Architecture, REST APIs, MySQL, PostgreSQL, Docker, Kubernetes, Git, Jenkins, System Design

Professional Experience

Senior Backend Engineer – CloudTech Systems (2021–Present)

• Designed and implemented scalable microservices using Spring Boot and Java.
• Developed RESTful APIs for web and mobile applications.
• Optimized SQL queries and improved database performance.
• Containerized applications using Docker and deployed services on Kubernetes clusters.

Backend Developer – TechWave Solutions (2018–2021)

• Developed backend services for enterprise web applications.
• Built API endpoints for authentication and transaction processing.
• Implemented caching and load balancing to improve system performance.

Education

Bachelor of Technology – Computer Science
National Institute of Technology, Surat | 2018"""


#     resume = """RESUME 4 – DEVOPS ENGINEER

# Name: Sneha Kapoor
# Location: Pune, India
# Email: [sneha.kapoor@email.com](mailto:sneha.kapoor@email.com)

# Professional Summary
# DevOps Engineer with 5 years of experience automating infrastructure, managing cloud environments, and implementing CI/CD pipelines for enterprise applications.

# Technical Skills
# AWS, Docker, Kubernetes, Terraform, Jenkins, Linux, Python, Bash, Prometheus, Grafana

# Professional Experience

# DevOps Engineer – CloudOps Technologies (2021–Present)

# • Implemented CI/CD pipelines for automated application deployment.
# • Managed Kubernetes clusters and containerized environments.
# • Automated infrastructure provisioning using Terraform.

# System Engineer – NetCloud Services (2019–2021)

# • Maintained Linux servers and monitored system performance.
# • Assisted in migrating applications to AWS infrastructure.

# Education

# Bachelor of Technology – Information Technology
# Pune University | 2019
# """

    embedding(resume, job_description)