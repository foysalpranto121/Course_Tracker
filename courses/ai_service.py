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
    courses = Course.objects.all()
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
    pending_tasks = Task.objects.filter(completed=False)
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
    """
    prompt_lower = prompt.lower()
    user_name = context["user_name"]
    c_summary = context["courses_summary"]
    t_summary = context["tasks_summary"]
    profile = context["profile"]
    goal = profile.get("learning_goal", "Master coursework")

    # 1. Summary / Progress tracking responsibility
    if any(k in prompt_lower for k in ["summar", "progress", "stat", "overview", "report", "how am i doing"]):
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
        lines = [
            f"### 🗓️ Recommended 7-Day Study Schedule\n",
            f"Tailored for your goal: **{goal}**\n",
            "| Day | Action Plan & Focus | Estimated Time |",
            "| :--- | :--- | :--- |",
            f"| **Day 1** | Review lowest progress course: *{c_summary['list'][0]['title'] if c_summary['list'] else 'Core Subject'}* | 45 Mins |",
            f"| **Day 2** | Tackle urgent tasks ({t_summary['pending_count']} pending) | 60 Mins |",
            "| **Day 3** | Deep dive into key concepts & take notes | 45 Mins |",
            "| **Day 4** | Complete practical tasks & coding exercises | 60 Mins |",
            "| **Day 5** | Quiz yourself on recent module topics | 30 Mins |",
            "| **Day 6** | Update course progress metrics & review completed items | 30 Mins |",
            "| **Day 7** | Rest, consolidate notes & set goals for next week | 20 Mins |",
        ]
        return "\n".join(lines)

    # 4. Quiz / Concept practice responsibility
    elif any(k in prompt_lower for k in ["quiz", "test", "practice", "question", "explain", "concept"]):
        if c_summary["list"]:
            top_course = c_summary["list"][0]["title"]
            cat = c_summary["list"][0]["category"]
        else:
            top_course = "Software Development"
            cat = "General"

        return (
            f"### 🧩 Quick Practice Quiz: **{top_course}** (`{cat}`)\n\n"
            f"**Question 1**: What is the primary benefit of modularizing code into separate components or views?\n"
            f"- A) Makes files larger\n- B) Improves reusability, testability, and code organization\n- C) Disables caching\n\n"
            f"**Question 2**: In project management, how does tracking task due dates help prevent project bottlenecks?\n"
            f"- A) It prioritizes critical path activities before deadlines pass\n- B) It deletes uncompleted tasks automatically\n\n"
            f"*(Tip: Reply with your answers to test your knowledge!)*"
        )

    # 5. General motivation & advisor response
    else:
        return (
            f"### 🤖 Hello **{user_name}**!\n\n"
            f"I am your **AI Learning Assistant**. I am monitoring your **{c_summary['total']} courses** and **{t_summary['pending_count']} pending tasks** to help you succeed.\n\n"
            f"**Here are things you can ask me to do:**\n"
            f"- 📊 *'Summarize my progress'* — Get a detailed breakdown of your active courses.\n"
            f"- ⏰ *'What tasks are due soon?'* — View prioritized upcoming deadlines.\n"
            f"- 🗓️ *'Generate a 7-day study plan'* — Get a structured learning timetable.\n"
            f"- 🧩 *'Quiz me on my courses'* — Test your knowledge with interactive questions.\n"
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
        f"You are an AI Learning Assistant for Course Tracker.\n"
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
