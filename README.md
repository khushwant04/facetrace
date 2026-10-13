# FaceTrace

Multi-tenant face recognition backend for colleges: register student faces, then identify people
from a photo or a live camera stream and return who they are and which class they should be in
right now.

FaceTrace is a FastAPI service backed by PostgreSQL, Redis, Auth0 and AWS Rekognition, with a small
Next.js panel for Auth0 login.

## Features

- **Multi-tenant organizations** - every record is scoped to an organization. Users log in with
  Auth0 (JWTs validated against the tenant's JWKS) and the organization is resolved from the
  user's database record.
- **Role-based access** - `super_admin`, `org_admin`, `faculty` and `student` roles enforced per
  endpoint.
- **Onboarding** - invitations (single and bulk), organization join codes, and an approval queue
  for new members.
- **Academic structure** - academic years, departments, semesters, sections, lab groups, students
  (by USN), faculty, subjects and weekly timetable slots.
- **Face registration** - upload a student photo; the image is stored in S3 and the face is indexed
  in an AWS Rekognition collection. Includes quality validation and collection stats.
- **Face scanning** - identify one or many faces in an uploaded image, or stream base64 frames over
  a WebSocket; each match is returned with the person's profile and their current timetable slot.
- **Caching** - Redis caches hot lookups (organizations, students, faculty, academic data).

## Architecture

```
 Next.js panel (Auth0 login)        browser / camera client
            │                                │  REST + WebSocket
            └──────────────┬─────────────────┘
                           ▼
                 FastAPI backend (/api/v1)
        ┌──────────┬───────┴───────┬──────────────┐
        ▼          ▼               ▼              ▼
   PostgreSQL    Redis      AWS Rekognition     AWS S3
 (SQLAlchemy +  (cache)     (face index and   (face images)
   Alembic)                  search)
                           Auth0 (JWT via JWKS)
```

API routers (all under `/api/v1`): `auth`, `onboarding`, `organizations`, `users`, `academic`,
`students`, `faculty`, `subjects`, `timetable`, `faces`, `scan`. Interactive docs are served at
`/docs`.

## Project structure

```
facetrace/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, router registration, /health
│   │   ├── config.py         # pydantic-settings, reads environment / backend/.env
│   │   ├── database.py       # async SQLAlchemy engine and session
│   │   ├── api/v1/           # route modules (auth, faces, scan, students, ...)
│   │   ├── core/             # Auth0 JWT validation, role checks, tenant context, cache decorator
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic request/response models
│   │   └── services/         # Rekognition, S3 and Redis clients
│   ├── alembic/              # database migrations
│   ├── requirements.txt
│   ├── test_all_phases.py    # end-to-end endpoint script against a running server
│   └── test_quick.sh
├── panel/                    # Next.js 16 + Auth0 login panel
├── scripts/                  # one-off data setup helpers
├── index.html                # standalone camera demo page
├── Dockerfile                # backend image
└── Makefile
```

## Getting started

### Prerequisites

- Python 3.11
- PostgreSQL (the code was written against Neon) and Redis
- An Auth0 tenant with an API (audience) and Organizations enabled
- An AWS account with an S3 bucket and access to Rekognition

### Backend

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cp backend/.env.example backend/.env   # then fill in real values
cd backend
alembic upgrade head                   # create the schema
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`make backend` runs the same `uvicorn` command from the repository root using `.venv`.

Environment variables (read by `backend/app/config.py`):

| variable | required | notes |
|---|---|---|
| `DATABASE_URL` | yes | `postgresql+asyncpg://user:pass@host/db` |
| `AUTH0_DOMAIN`, `AUTH0_API_AUDIENCE` | yes | issuer defaults to `https://<domain>/` |
| `AUTH0_CLIENT_ID`, `AUTH0_CLIENT_SECRET` | no | defined in settings, not currently used by the API |
| `S3_BUCKET_NAME` | yes | bucket for face images |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | no | region defaults to `ap-south-1`; omit keys to use the default AWS credential chain |
| `REKOGNITION_COLLECTION_ID` | no | defaults to `student-faces-prod` |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME`, `REDIS_PASSWORD` | no | defaults to `localhost:6379` |
| `DEBUG`, `ENVIRONMENT` | no | `DEBUG` defaults to `True`; set it to `False` in production |

### Docker (backend)

```bash
docker build -t facetrace-backend .
docker run --env-file backend/.env -p 8000:8000 facetrace-backend
```

Set `WEB_CONCURRENCY` to change the number of Uvicorn workers (default 4). Run migrations
separately, for example `docker run --env-file backend/.env facetrace-backend alembic upgrade head`.

### Panel

```bash
cd panel
cp .env.example .env.local   # Auth0 application settings
npm install
npm install @auth0/nextjs-auth0   # imported by lib/auth0.ts but not yet listed in package.json
npm run dev                       # http://localhost:3000
```

The panel currently provides Auth0 login/logout, the user profile, and a `/token` page that shows
the session's access token for calling the API during development.

## Usage

Authenticated requests send an Auth0 access token; the organization comes from the user's record:

```bash
curl -H "Authorization: Bearer $TOKEN" \
     -F "file=@student.jpg" \
     http://localhost:8000/api/v1/faces/upload/1AB23CS001     # register a face by USN

curl -H "Authorization: Bearer $TOKEN" \
     -F "file=@classroom.jpg" \
     http://localhost:8000/api/v1/scan/face/multiple          # identify all faces in a photo
```

Real-time scanning: connect to `ws://localhost:8000/ws/{org_id}` and send
`{"frame": "<base64 image>", "mode": "single" | "multi"}`; each reply lists the matched people with
their current class.

## Deployment

The API is deployed at <https://facetrace-five.vercel.app> (the root returns the service name; see
`/docs` for the OpenAPI UI).
