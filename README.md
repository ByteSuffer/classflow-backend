# ClassFlow Backend

Flask + MySQL REST API for ClassFlow. Fully updated to match the ClassFlow frontend.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create MySQL database
```sql
CREATE DATABASE classflow;
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your MySQL credentials and secret keys
```

### 4. Seed the database
```bash
python seed.py
```

### 5. Run the server
```bash
python app.py
# Server starts at http://localhost:5000
```

---

## Connect the frontend

In your `classflow-mobile` folder:

**Step 1** — Copy `api.js` and `api-bridge.js` into `classflow-mobile/`

**Step 2** — In `index.html`, replace this line:
```html
<script src="data.js"></script>
```
With these three lines:
```html
<script src="api.js"></script>
<script src="api-bridge.js"></script>
```
*(Keep `script.js` and `submission.js` — they handle the UI unchanged.)*

**Step 3** — In `api.js`, set your backend URL:
```js
const API_URL = 'http://localhost:5000';  // local
// or your Render URL in production
```

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login, get JWT token |
| GET  | `/api/auth/me` | Get current user |

### Subjects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/subjects` | List enrolled subjects |
| POST | `/api/subjects` | Create subject (teacher) |
| POST | `/api/subjects/join` | Join subject by code (student) |
| GET  | `/api/subjects/:id/students` | List enrolled students |

### Assignments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/assignments` | List assignments |
| GET  | `/api/assignments?subject_id=X` | Filter by subject |
| POST | `/api/assignments` | Create assignment (teacher) |

### Submissions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | `/api/submissions` | Submit assignment (student) |
| GET    | `/api/submissions/:assignId/mine` | My submission for an assignment |
| DELETE | `/api/submissions/:subId/unsubmit` | Recall submission |
| GET    | `/api/submissions/:assignId` | All submissions (teacher) |
| POST   | `/api/submissions/grade` | Grade and return (teacher) |
| GET    | `/api/grades` | Student grade summary |

### Private Comments
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/submissions/:subId/private-comments` | Get private comments |
| POST | `/api/submissions/:subId/private-comments` | Add private comment |

### Announcements
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET  | `/api/announcements` | List announcements |
| GET  | `/api/announcements?subject_id=X` | Filter by subject |
| POST | `/api/announcements` | Post announcement (teacher) |
| POST | `/api/announcements/:id/comments` | Add stream comment |

### Dashboards
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/student` | Student dashboard data |
| GET | `/api/dashboard/teacher` | Teacher dashboard data |
| GET | `/api/notifications` | Student notifications |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Check server is running |

---

## Demo credentials (after seeding)
| Role | Email | Password |
|------|-------|----------|
| Student | priya@student.du.ac.in | password123 |
| Teacher | kumar@faculty.du.ac.in | password123 |

Subject join codes: `OS`, `DBMS`, `CN`, `MATHS`, `SE`, `HCI`

---

## Deploy on Render (free)

1. Push to GitHub
2. Create a new **Web Service** on render.com
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add environment variables from `.env`
6. Create a **MySQL** database on Render and paste the connection URL into `DATABASE_URL`
7. After deploy, visit `https://your-app.onrender.com/api/health` to verify
