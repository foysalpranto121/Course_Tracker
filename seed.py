import os
import sys
import argparse
import random
import datetime
import pandas as pd
from faker import Faker

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "todo_project.settings")

import django
django.setup()

from courses.models import Course, Task

fake = Faker()

CATEGORIES = [
    "Web Development", "Data Science", "Mobile Apps", 
    "UI/UX Design", "Cloud Computing", "Cyber Security", 
    "DevOps", "Artificial Intelligence", "Database Systems"
]

STATUS_CHOICES = ["not_started", "in_progress", "completed"]

COURSE_TOPICS = [
    "Full-Stack Django 5 & React Masterclass",
    "Python Data Structures & Algorithms",
    "Modern Frontend with Vue.js & Tailwind",
    "PostgreSQL Database Optimization & Administration",
    "Building REST APIs with Django REST Framework",
    "Cloud Architecture on AWS & Kubernetes",
    "Machine Learning & Deep Learning with PyTorch",
    "Figma UI/UX Prototyping for Designers",
    "Cyber Security Fundamentals & Ethical Hacking",
    "Docker & CI/CD Pipeline Automation",
    "Flutter Cross-Platform Mobile App Development",
    "Node.js Microservices Architecture"
]


def generate_fake_courses_data(count=15, include_duplicates=True):
    """
    Generates a list of dictionaries with fake course data using Faker.
    """
    courses_data = []

    for i in range(count):
        # Pick title from topic list or fake sentence
        if i < len(COURSE_TOPICS):
            title = COURSE_TOPICS[i]
        else:
            title = f"{fake.job()} Specialization in {fake.catch_phrase()}"

        instructor = fake.name()
        category = random.choice(CATEGORIES)
        description = fake.paragraph(nb_sentences=3)

        start_date = fake.date_between(start_date="-60d", end_date="+10d")
        end_date = start_date + datetime.timedelta(days=random.randint(15, 90))
        
        status = random.choice(STATUS_CHOICES)
        if status == "completed":
            progress = 100
        elif status == "not_started":
            progress = 0
        else:
            progress = random.randint(10, 95)

        courses_data.append({
            "Title": title,
            "Instructor": instructor,
            "Category": category,
            "Description": description,
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End Date": end_date.strftime("%Y-%m-%d"),
            "Progress (%)": progress,
            "Status": status,
        })

    # Add deliberate duplicate rows if requested
    if include_duplicates and len(courses_data) >= 3:
        # Duplicate row 0 with updated progress
        dup1 = courses_data[0].copy()
        dup1["Progress (%)"] = min(100, dup1["Progress (%)"] + 15)
        dup1["Description"] = f"[DUPLICATE ROW] {dup1['Description']}"
        courses_data.append(dup1)

        # Duplicate row 1
        dup2 = courses_data[1].copy()
        dup2["Description"] = f"[DUPLICATE ROW] {dup2['Description']}"
        courses_data.append(dup2)

    return courses_data


def seed_database(count=15, clear=False):
    """
    Populates Django database with fake Course and Task objects.
    """
    if clear:
        print("Clearing existing Course & Task database records...")
        Task.objects.all().delete()
        Course.objects.all().delete()

    print(f"Seeding database with {count} courses...")
    created_count = 0

    courses_data = generate_fake_courses_data(count=count, include_duplicates=False)
    
    for c_data in courses_data:
        course = Course.objects.create(
            title=c_data["Title"],
            instructor=c_data["Instructor"],
            category=c_data["Category"],
            description=c_data["Description"],
            start_date=c_data["Start Date"],
            end_date=c_data["End Date"],
            progress=c_data["Progress (%)"],
            status=c_data["Status"],
        )
        created_count += 1

        # Create 2-4 tasks per course
        task_count = random.randint(2, 4)
        for t_idx in range(1, task_count + 1):
            s_date = course.start_date
            if isinstance(s_date, str):
                s_date = datetime.datetime.strptime(s_date, "%Y-%m-%d").date()
            due_date = (s_date + datetime.timedelta(days=t_idx * 7)) if s_date else None
            Task.objects.create(
                course=course,
                title=f"Module {t_idx}: {fake.bs().title()}",
                description=fake.sentence(),
                due_date=due_date,
                completed=random.choice([True, False]),
            )


    print(f"Successfully seeded {created_count} courses and their tasks into the database!")


def create_excel_seed_file(filename="sample_import.xlsx", count=15):
    """
    Generates an Excel spreadsheet with mock course data and deliberate duplicate rows.
    """
    print(f"Generating fake Excel seed file: {filename} with intentional duplicates...")
    courses_data = generate_fake_courses_data(count=count, include_duplicates=True)
    
    df = pd.DataFrame(courses_data)
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"Created Excel file '{filename}' with {len(df)} rows (includes intentional duplicate rows for testing!).")


def main():
    parser = argparse.ArgumentParser(description="Seed script for Course Tracker app using Faker & Pandas.")
    parser.add_argument("--db", action="store_true", help="Populate PostgreSQL / Django database with fake courses.")
    parser.add_argument("--excel", type=str, nargs="?", const="sample_import.xlsx", help="Generate test Excel import file.")
    parser.add_argument("--count", type=int, default=15, help="Number of courses to generate (default: 15).")
    parser.add_argument("--clear", action="store_true", help="Clear existing DB data before seeding.")

    args = parser.parse_args()

    if not args.db and not args.excel:
        # Default behavior: run both if no flags specified
        seed_database(count=args.count, clear=args.clear)
        create_excel_seed_file(filename="sample_import.xlsx", count=args.count)
    else:
        if args.db:
            seed_database(count=args.count, clear=args.clear)
        if args.excel:
            create_excel_seed_file(filename=args.excel, count=args.count)


if __name__ == "__main__":
    main()
