import json
import logging
import os
import urllib.request
from django.conf import settings
from django.utils import timezone
from .models import Course, Task, UserProfile

logger = logging.getLogger(__name__)


def get_user_context(user):
    """
    Extracts structured database context for the given user, including
    profile attributes, active courses, task deadlines, and progress statistics.
    """
    # Profile context
    profile_data = {}
    try:
        profile = getattr(user, "profile", None)
        if profile:
            profile_data = {
                "institution": profile.institution or "Not specified",
                "occupation": profile.occupation or "Student",
                "learning_goal": profile.learning_goal or "Master coursework",
                "bio": profile.bio or ""
            }
    except Exception as e:
        logger.warning(f"Could not load user profile: {e}")

    # Courses context
    courses = Course.objects.filter(user=user)
    total_courses = courses.count()
    completed_courses = courses.filter(status="completed").count()
    in_progress_courses = courses.filter(status="in_progress").count()
    not_started_courses = courses.filter(status="not_started").count()

    course_list = []
    for c in courses[:10]:
        course_list.append({
            "title": c.title,
            "category": c.category or "General",
            "progress": c.progress,
            "status": c.get_status_display(),
            "instructor": c.instructor or "Unassigned"
        })

    # Tasks context
    pending_tasks = Task.objects.filter(course__user=user, completed=False)
    total_pending_tasks = pending_tasks.count()
    today = timezone.now().date()
    overdue_tasks = pending_tasks.filter(due_date__lt=today).count()
    due_today_tasks = pending_tasks.filter(due_date=today).count()

    task_list = []
    for t in pending_tasks.order_by("due_date", "-created_at")[:8]:
        task_list.append({
            "title": t.title,
            "course": t.course.title,
            "due_date": str(t.due_date) if t.due_date else "No due date",
            "completed": t.completed
        })

    return {
        "user_name": user.get_full_name() or user.username,
        "profile": profile_data,
        "courses_summary": {
            "total": total_courses,
            "completed": completed_courses,
            "in_progress": in_progress_courses,
            "not_started": not_started_courses,
            "list": course_list
        },
        "tasks_summary": {
            "pending_count": total_pending_tasks,
            "overdue_count": overdue_tasks,
            "due_today_count": due_today_tasks,
            "list": task_list
        }
    }


def call_gemini_api(api_key, system_prompt, user_prompt):
    """
    Calls Google Gemini REST API (gemini-1.5-flash model).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"{system_prompt}\n\nUser Prompt: {user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            candidates = res_body.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None


def call_openai_api(api_key, system_prompt, user_prompt):
    """
    Calls OpenAI Chat Completions REST API (gpt-3.5-turbo / gpt-4o-mini).
    """
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 800,
        "temperature": 0.7
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            choices = res_body.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None


def fallback_assistant_response(context, prompt):
    """
    Intelligent local fallback assistant that fulfills the 5 AI Responsibilities
    using real database context when no external API key is configured.
    Handles course-specific context when a user asks about a specific course.
    """
    prompt_lower = prompt.lower()
    user_name = context["user_name"]
    c_summary = context["courses_summary"]
    t_summary = context["tasks_summary"]
    profile = context["profile"]
    goal = profile.get("learning_goal", "Master coursework")

    # Detect if prompt refers to a specific course
    matched_course = None
    if c_summary["list"]:
        for c in c_summary["list"]:
            if c["title"].lower() in prompt_lower or prompt_lower.endswith(c["title"].lower()):
                matched_course = c
                break

    # 1. Summary / Progress tracking responsibility
    if any(k in prompt_lower for k in ["summar", "progress", "stat", "overview", "report", "how am i doing", "key topics"]):
        if matched_course:
            return (
                f"### 💡 Key Topics & Overview: **{matched_course['title']}**\n\n"
                f"- **Category**: `{matched_course['category']}`\n"
                f"- **Instructor**: {matched_course['instructor']}\n"
                f"- **Current Progress**: **{matched_course['progress']}%** ({matched_course['status']})\n\n"
                f"#### Core Learning Modules & Objectives:\n"
                f"1. **Foundations**: Master key concepts in {matched_course['category']}.\n"
                f"2. **Practical Applications**: Build projects & complete assignments under guidance of {matched_course['instructor']}.\n"
                f"3. **Milestone Goal**: Finish remaining course tasks to reach 100% completion!\n"
            )

        lines = [
            f"### 📊 Learning Progress Summary for **{user_name}**\n",
            f"- **Goal**: *{goal}*",
            f"- **Total Courses**: {c_summary['total']} ({c_summary['completed']} Completed, {c_summary['in_progress']} In Progress, {c_summary['not_started']} Not Started)",
            f"- **Pending Tasks**: {t_summary['pending_count']} total ({t_summary['overdue_count']} overdue, {t_summary['due_today_count']} due today)\n",
        ]
        if c_summary["list"]:
            lines.append("#### Active Courses & Progress:")
            for c in c_summary["list"]:
                lines.append(f"- **{c['title']}** (`{c['category']}`): {c['progress']}% complete ({c['status']})")
        else:
            lines.append("💡 *No active courses found. Start by creating a new course!*")
            
        return "\n".join(lines)

    # 2. Tasks / Deadlines responsibility
    elif any(k in prompt_lower for k in ["task", "due", "deadline", "todo", "urgent", "overdue"]):
        lines = [f"### ⏰ Task & Deadline Analysis for **{user_name}**\n"]
        if t_summary["overdue_count"] > 0:
            lines.append(f"⚠️ **Warning**: You have **{t_summary['overdue_count']} overdue task(s)** that need immediate attention!\n")
        
        if t_summary["list"]:
            lines.append("#### Pending Tasks Prioritized by Due Date:")
            for idx, t in enumerate(t_summary["list"], 1):
                due = t["due_date"]
                lines.append(f"{idx}. **{t['title']}** (Course: *{t['course']}*) - Due: `{due}`")
        else:
            lines.append("🎉 **Great job!** You have no pending tasks right now.")
            
        return "\n".join(lines)

    # 3. Study Plan responsibility
    elif any(k in prompt_lower for k in ["study plan", "schedule", "routine", "plan", "timetable", "roadmap"]):
        target_title = matched_course["title"] if matched_course else (c_summary["list"][0]["title"] if c_summary["list"] else "Core Subject")
        cat = matched_course["category"] if matched_course else "General"

        lines = [
            f"### 🗓️ Customized 7-Day Study Plan for **{target_title}**\n",
            f"- **Category**: `{cat}` | **Goal**: *{goal}*\n",
            "| Day | Focus Activity & Milestones | Estimated Time |",
            "| :--- | :--- | :--- |",
            f"| **Day 1** | Core Concept Review: *{target_title}* fundamentals | 45 Mins |",
            f"| **Day 2** | Practice Tasks & Assignments ({t_summary['pending_count']} pending tasks) | 60 Mins |",
            "| **Day 3** | Hands-on Coding / Applied Exercises | 60 Mins |",
            "| **Day 4** | Intermediate Modules & Notes Summary | 45 Mins |",
            "| **Day 5** | AI Practice Quiz & Knowledge Check | 30 Mins |",
            "| **Day 6** | Code Review & Completion Check | 40 Mins |",
            "| **Day 7** | Rest & Set Goals for Next Week | 20 Mins |",
        ]
        return "\n".join(lines)

    # 4. Quiz / Concept practice responsibility
    elif any(k in prompt_lower for k in ["quiz", "test", "practice", "question", "explain", "concept"]):
        target_title = matched_course["title"] if matched_course else (c_summary["list"][0]["title"] if c_summary["list"] else "Software Engineering")
        cat = matched_course["category"] if matched_course else "General"

        return (
            f"### 🧩 AI Practice Quiz: **{target_title}** (`{cat}`)\n\n"
            f"**Question 1**: What is the most effective approach when structuring a project in {cat}?\n"
            f"- A) Write all code in a single file\n"
            f"- B) Separate logic into modular components, views, and data models\n"
            f"- C) Avoid using version control\n\n"
            f"**Question 2**: In software development, how does tracking task completion percentages aid project management?\n"
            f"- A) It provides transparent progress metrics & prevents deadline bottlenecks\n"
            f"- B) It automatically deletes uncompleted tasks\n\n"
            f"**Question 3**: Why is error logging and performance monitoring critical in production systems?\n"
            f"- A) To increase server CPU load\n"
            f"- B) To diagnose runtime bottlenecks and maintain system health\n\n"
            f"*(Tip: Reply with your chosen options A, B, or C to check your answers!)*"
        )

    # 5. General motivation & advisor response
    else:
        return (
            f"### 🤖 Hello **{user_name}**!\n\n"
            f"I am your **AI Learning Assistant**. I am monitoring your **{c_summary['total']} courses** and **{t_summary['pending_count']} pending tasks** to help you succeed.\n\n"
            f"**Here are things you can ask me to do:**\n"
            f"- 📊 *'Summarize my progress'* — Get a detailed breakdown of your active courses.\n"
            f"- ⏰ *'What tasks are due soon?'* — View prioritized upcoming deadlines.\n"
            f"- 🗓️ *'Generate a 7-day study plan for [Course Name]'* — Get a custom timetable.\n"
            f"- 🧩 *'Quiz me on [Course Name]'* — Test your knowledge with practice questions.\n"
            f"- 💡 *Ask any custom learning or technical question!*"
        )


def generate_assistant_response(user, prompt):
    """
    Main entrypoint to process AI user prompts with database context.
    Attempts Gemini/OpenAI API calls if keys are present; falls back seamlessly to local engine.
    """
    context = get_user_context(user)
    
    gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    openai_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

    system_prompt = (
        f"You are an AI Learning Assistant for AI Course Tracker.\n"
        f"User Name: {context['user_name']}\n"
        f"User Learning Goal: {context['profile'].get('learning_goal', 'Master coursework')}\n"
        f"Context:\n{json.dumps(context, indent=2)}\n\n"
        f"Instructions:\n"
        f"- Provide helpful, clear, and structured answers in GitHub-style Markdown.\n"
        f"- Fulfill the assistant's responsibilities: course progress tracking, deadline prioritizing, study planning, concept quizzes, and study tips."
    )

    # Attempt Gemini API first if configured
    if gemini_key:
        reply = call_gemini_api(gemini_key, system_prompt, prompt)
        if reply:
            return reply

    # Attempt OpenAI API if configured
    if openai_key:
        reply = call_openai_api(openai_key, system_prompt, prompt)
        if reply:
            return reply

    # Fallback to local intelligent engine
    return fallback_assistant_response(context, prompt)
