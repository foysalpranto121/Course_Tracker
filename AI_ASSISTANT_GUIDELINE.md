# 🤖 AI Tutor Assistant — Implementation Guideline & Architecture

Welcome to the technical implementation guide for the **AI Tutor Assistant** in **AI Course Tracker**. This document provides an architectural breakdown of how the AI feature was designed, constructed, and integrated into the Django web application.

---

## 📌 1. Technology Stack Added to Django

The AI Assistant is built using a modern, decoupled architecture combining Django backend controllers, ORM context extraction, third-party generative AI REST APIs, and a sleek client-side UI:

| Layer | Component / Technology | Function & Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3.10+ / Django 5+ CBVs | `AIAssistantView` in `courses/views.py` processes AJAX prompts. |
| **AI Context Engine** | Django ORM (`courses/ai_service.py`) | Extracts live database context (courses, tasks, progress %, user goals). |
| **Primary AI API** | Google Gemini REST API (`gemini-1.5-flash`) | Queries Gemini models via `urllib.request` using `GEMINI_API_KEY`. |
| **Secondary AI API** | OpenAI REST API (`gpt-4o-mini`) | Fallback API support via `OPENAI_API_KEY`. |
| **Local AI Engine** | Intelligent Fallback Service | Provides real-time context-aware answers, quizzes, and study plans when offline or without API keys. |
| **Environment Secrets** | `python-dotenv` | Loads sensitive keys (`GEMINI_API_KEY`, `SECRET_KEY`, DB credentials) securely from `.env`. |
| **Frontend UI** | Bootstrap 5.3 Offcanvas + Custom CSS3 | Sleek ocean cyan/indigo theme, glassmorphic card, and animated 3D AI avatar. |
| **Async Client Logic** | Vanilla JavaScript (Fetch API) | Non-blocking AJAX prompt submission, Markdown rendering, auto-scrolling, and typing animation. |

---

## 🏗️ 2. High-Level AI System Architecture

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        🤖 AI TUTOR ASSISTANT SYSTEM ARCHITECTURE                      │
└────────────────────────────────────────────────────────────────────────────────────────┘

  [ 🌐 CLIENT BROWSER ]
    ├── Floating 3D AI Tutor Avatar FAB Button (Fixed z-index: 99999)
    ├── Offcanvas Drawer with Suggestion Pills & Input Form
    └── Fetch API (POST /ai-assistant/ with CSRF Token & JSON payload)
             │
             ▼ (HTTP JSON Request)
  [ ⚙️ DJANGO BACKEND ]
    ├── URL Router: courses/urls.py (path("ai-assistant/", AIAssistantView.as_view()))
    ├── View Controller: AIAssistantView (LoginRequiredMixin / Guest Handling)
    └── Service Engine: courses/ai_service.py
             │
             ├──► 1. Extract DB Context (Course.objects, Task.objects, UserProfile.objects)
             ├──► 2. Check API Keys (GEMINI_API_KEY / OPENAI_API_KEY in .env)
             │        ├── IF Key Present: Query Gemini REST API (gemini-1.5-flash)
             │        └── IF Key Missing / Fails: Execute Local Database Context Engine
             │
             ▼ (JSON Response)
  [ 🎨 RENDERED OUTPUT ]
    └── Markdown Format Parser ──► Appends Assistant Bubble in Chat Drawer
```

---

## 🚀 3. Step-by-Step Implementation Guide

### Step 1: Secure Environment Setup (`.env` & `settings.py`)
Install `python-dotenv` and store API keys in a secret `.env` file excluded by `.gitignore`:

**`.env`**:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
SECRET_KEY=django-insecure-your-secret-key
```

**`todo_project/settings.py`**:
```python
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
```

---

### Step 2: ORM Context & AI Service ([courses/ai_service.py](file:///m:/Todo%20APP%20using%20Django/courses/ai_service.py))
`courses/ai_service.py` is responsible for:
1. `get_user_context(user)`: Gathers user profile goals, active courses, progress rates, pending tasks, and overdue deadlines into a JSON dictionary.
2. `call_gemini_api(api_key, system_prompt, user_prompt)`: Connects to Google's REST API.
3. `fallback_assistant_response(context, prompt)`: A rule-based local assistant fulfilling 5 core responsibilities when API keys are absent.

```python
def generate_assistant_response(user, prompt):
    context = get_user_context(user)
    gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")

    system_prompt = (
        f"You are an AI Learning Assistant for AI Course Tracker.\n"
        f"User Context:\n{json.dumps(context, indent=2)}\n"
    )

    if gemini_key:
        reply = call_gemini_api(gemini_key, system_prompt, prompt)
        if reply:
            return reply

    return fallback_assistant_response(context, prompt)
```

---

### Step 3: AJAX Class-Based View ([courses/views.py](file:///m:/Todo%20APP%20using%20Django/courses/views.py#L432-L462))
Implement `AIAssistantView` to parse JSON POST prompts and return `JsonResponse`:

```python
class AIAssistantView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        from .ai_service import generate_assistant_response
        body = json.loads(request.body.decode("utf-8")) if request.body else {}
        prompt = body.get("prompt", "").strip()

        if not prompt:
            return JsonResponse({"status": "error", "message": "Prompt cannot be empty."}, status=400)

        reply = generate_assistant_response(request.user, prompt)
        return JsonResponse({"status": "success", "reply": reply})
```

---

### Step 4: URL Dispatcher ([courses/urls.py](file:///m:/Todo%20APP%20using%20Django/courses/urls.py#L33-L34))
Register route for the AJAX endpoint:

```python
path("ai-assistant/", views.AIAssistantView.as_view(), name="ai_assistant"),
```

---

### Step 5: Frontend UI Drawer & 3D Avatar ([base.html](file:///m:/Todo%20APP%20using%20Django/courses/templates/courses/base.html#L152-L355))
Add the 3D Avatar floating action button, Offcanvas sidebar, and asynchronous JavaScript message handler:

```html
<!-- Floating 3D AI Tutor FAB -->
<button id="aiFabBtn" class="btn ai-fab-btn shadow-lg d-flex align-items-center justify-content-center p-0" type="button" data-bs-toggle="offcanvas" data-bs-target="#aiAssistantOffcanvas">
    <img src="{% static 'courses/images/ai_avatar.png' %}?v=2.5" alt="AI Tutor Avatar" class="rounded-circle" style="width: 58px; height: 58px; object-fit: cover;">
</button>
```

---

### Step 6: Course-Specific Suite Integration ([course_detail.html](file:///m:/Todo%20APP%20using%20Django/courses/templates/courses/course_detail.html#L50-L80))
Render quick AI prompt buttons directly inside individual course pages so users can request quizzes, study plans, or summaries specifically for that course:

```html
<button type="button" class="btn btn-sm pill-prompt" data-prompt="Generate a 7-day study plan for {{ course.title }}">
    🗓️ Course Study Plan
</button>
```

---

## 🎯 5 Core AI Responsibilities

1. 📊 **Course & Progress Tracking**: Summarizes enrolled courses, completion rates, and progress metrics.
2. ⏰ **Task & Deadline Management**: Identifies overdue/pending tasks and prioritizes upcoming deadlines.
3. 🗓️ **Personalized Study Plan Generator**: Crafts 7-day study timetables tailored to user goals and course categories.
4. 🧩 **Interactive Practice Quizzes**: Generates 3-question multiple choice quizzes based on course subjects.
5. 💡 **Motivational & Technical Guidance**: Provides study tips and answers learning queries.

---

## 🧪 Automated Testing

Unit tests in [courses/tests.py](file:///m:/Todo%20APP%20using%20Django/courses/tests.py#L111-L150) verify:
- URL Resolution (`reverse('courses:ai_assistant') == '/ai-assistant/'`).
- Authentication protection (`302` redirect for unauthenticated GET/POST).
- JSON payload processing and valid status responses.
- Empty prompt validation (`400` status code).

Run tests using:
```bash
python manage.py test
```
