# Maze Architect

An interactive web application where you design mazes and watch AI models solve them in real-time using function calling. A reverse Turing test: instead of AI generating content for humans, humans create challenges for AI.

![Maze Architect](https://img.shields.io/badge/React-19-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green) ![Python](https://img.shields.io/badge/Python-3.10+-yellow) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)

## Features

### Maze Builder
- **Visual canvas editor** - Click and drag to draw walls between dots
- **Multiple grid sizes** - 10x10, 15x15, 20x20, 25x25
- **Auto-generate** perfect mazes using recursive backtracking algorithm
- **Custom start/end positions** - Right-click to set goal location
- **Visual themes** - Limbo (purple), Hotel (gold Art Deco), Snow Fortress (cold brutalist)

### AI Maze Solver
- **Real-time visualization** via Server-Sent Events (SSE)
- **Tool/function calling** - AI navigates using `move_up`, `move_down`, `move_left`, `move_right`, `get_available_moves`, `check_goal`
- **Multiple model support** via OpenRouter (Llama, Mistral, GPT, Claude, Gemini, and more)
- **Free models work without API key** - Try free tier models anonymously
- **Step-by-step logging** - Observe AI decision-making in real-time

### Challenges
Take on 6 pre-defined challenges with varying difficulty:

| Challenge | Grid Size | Time Limit | Target Model |
|-----------|-----------|------------|--------------|
| Llama's Playground | 10x10 | 2 min | Llama 3.1 8B |
| Mistral's Maze | 15x15 | 3 min | Mistral Small |
| GPT's Gauntlet | 15x15 | 2 min | GPT-4o-mini |
| Claude's Conundrum | 20x20 | 4 min | Claude 3.5 Haiku |
| The Abyss | 25x25 | 5 min | Any model |
| Free Agent Frenzy | 15x15 | 3 min | Any free model |

### MazeBench Leaderboard
Compare LLM performance across all mazes with our normalized scoring system:
- **Geometric mean scoring** - Fair comparison across mazes of varying difficulty
- **Medal system** - Earn medals based on time relative to best:
  - 🥇 Gold: Within 10% of best time
  - 🥈 Silver: Within 15% of best time
  - 🥉 Bronze: Within 20% of best time
- **Challenge solutions** - View past successful solutions for each challenge

### User Features
- **Authentication** via Clerk (Google, GitHub, email)
- **Save/load mazes** to personal library
- **Attempt history** with success/failure tracking
- **API usage monitoring** - Track tokens, costs, latency

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19, Vite 7, React Router 7, Clerk Auth |
| Backend | FastAPI, SQLAlchemy (async), Pydantic |
| Database | PostgreSQL 15 |
| LLM Gateway | OpenRouter API |
| Infrastructure | Docker Compose |

## Prerequisites

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Clerk account (free tier works)
- OpenRouter API key (optional - free models work without one)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Antonio7098/inception-maze-game.git
cd inception-maze-game
```

### 2. Start PostgreSQL

```bash
cd frontend
docker-compose up -d
cd ..
```

### 3. Configure Environment

```bash
# Backend environment
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```bash
DATABASE_URL=postgresql://maze:maze_secret@localhost:5432/maze_game
CLERK_SECRET_KEY=sk_test_your_clerk_secret_key
CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
OPENROUTER_API_KEY=sk-or-v1-your_key  # Optional for free models
DEFAULT_MODEL=mistralai/ministral-3b-2410
APP_URL=http://localhost:5173
```

### 4. Run the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 5. Run the Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```bash
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

```bash
npm run dev
```

Open http://localhost:5173 in your browser.

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/me` | Get current user info |
| POST | `/api/auth/api-key` | Update user's OpenRouter API key |

### Models
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List available AI models (tool-capable) |

### Challenges
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/challenges` | List all challenges |
| GET | `/api/challenges/{id}` | Get specific challenge |
| GET | `/api/challenges/{id}/solutions` | Get successful solutions |
| GET | `/api/challenges/stats` | Get best times per challenge |

### Mazes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/mazes` | List user's saved mazes |
| POST | `/api/mazes` | Create a new maze |
| GET | `/api/mazes/{id}` | Get specific maze |
| DELETE | `/api/mazes/{id}` | Delete a maze |
| GET | `/api/mazes/{id}/attempts` | Get solve attempts |
| GET | `/api/mazes/{id}/stats` | Get maze statistics |

### MazeBench
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/mazebench` | Get LLM leaderboard |

### Attempts
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/attempts` | Start solving (SSE stream) |
| GET | `/api/attempts/{id}` | Get attempt details |

### Monitoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/monitoring/api-calls` | List API calls |
| GET | `/api/monitoring/stats` | Get usage statistics |

## Project Structure

```
maze-game/
├── backend/
│   ├── main.py                 # FastAPI app & routes
│   ├── requirements.txt        # Python dependencies
│   ├── db/
│   │   ├── session.py          # Database connection
│   │   └── models.py           # SQLAlchemy models
│   ├── models/
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/
│   │   ├── auth.py             # Clerk authentication
│   │   ├── challenges.py       # Challenge definitions
│   │   ├── openrouter.py       # Model fetching
│   │   ├── maze_agent.py       # AI agent service
│   │   └── leaderboard.py      # MazeBench scoring & rankings
│   └── tests/
│       ├── test_unit.py
│       └── test_integration.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── docker-compose.yml      # PostgreSQL container
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   └── backend.js      # API client
│       ├── maze/
│       │   ├── mazeLogic.js    # Maze generation/logic
│       │   └── agent.js        # AI solver agent
│       └── pages/
│           ├── Challenges.jsx
│           ├── Leaderboard.jsx
│           ├── Builder.jsx
│           ├── MyMazes.jsx
│           └── Settings.jsx
└── .env.example
```

## Testing

### Backend Tests
```bash
cd backend
pip install -r requirements-test.txt
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## How It Works

### Maze Wall Model
Walls are stored as connections between grid dots (not cells), using the format `"x1,y1-x2,y2"`. This allows for precise wall placement and intuitive visual editing.

### AI Solving Architecture
1. Maze is converted to ASCII art and wall data
2. System prompt is generated with full maze context
3. AI uses OpenAI-compatible function calling to navigate
4. Each tool call is logged as an event in the database
5. Position updates are streamed to frontend via SSE

### Authentication Flow
1. Frontend uses Clerk for user authentication
2. Clerk JWT token sent to backend in Authorization header
3. Backend verifies token with Clerk's JWKS endpoint
4. User auto-created in database on first request

## Environment Variables

### Backend (.env)
| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `CLERK_SECRET_KEY` | Clerk backend secret key | Yes |
| `CLERK_PUBLISHABLE_KEY` | Clerk frontend publishable key | Yes |
| `OPENROUTER_API_KEY` | OpenRouter API key | No (free models work) |
| `DEFAULT_MODEL` | Default AI model ID | No |
| `APP_URL` | Frontend URL for CORS | No |

### Frontend (.env.local)
| Variable | Description | Required |
|----------|-------------|----------|
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk publishable key | Yes |

## Getting API Keys

### Clerk (Authentication)
1. Go to [clerk.com](https://clerk.com) and create a free account
2. Create a new application
3. Copy the **Publishable Key** and **Secret Key** from the dashboard

### OpenRouter (LLM Gateway)
1. Go to [openrouter.ai](https://openrouter.ai)
2. Create an account and get your API key from [openrouter.ai/keys](https://openrouter.ai/keys)
3. Add credits or use free tier models

**Note:** Free models (like `meta-llama/llama-3.1-8b-instruct:free`) work without an API key!

## License

MIT License - feel free to use this project for your own purposes.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
