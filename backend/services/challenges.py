from typing import List, Dict, Any

CHALLENGES = [
    {
        "id": "challenge-1",
        "name": "Llama's Playground",
        "description": "Create a 10x10 maze that Llama 3.3 8B can solve in under 2 minutes",
        "model": "meta-llama/llama-3.3-8b-instruct:free",
        "time_limit_minutes": 2,
        "grid_size": 10,
        "difficulty": 1,
    },
    {
        "id": "challenge-2",
        "name": "Mistral's Maze",
        "description": "Design a 15x15 maze that Mistral can solve in under 3 minutes",
        "model": "mistralai/ministral-3b-2410",
        "time_limit_minutes": 3,
        "grid_size": 15,
        "difficulty": 2,
    },
    {
        "id": "challenge-3",
        "name": "GPT's Gauntlet",
        "description": "Build a 15x15 maze that GPT-4o Mini can solve in under 2 minutes",
        "model": "openai/gpt-4o-mini",
        "time_limit_minutes": 2,
        "grid_size": 15,
        "difficulty": 2,
    },
    {
        "id": "challenge-4",
        "name": "Claude's Conundrum",
        "description": "Create a 20x20 maze that Claude 3.5 Haiku can solve in under 4 minutes",
        "model": "anthropic/claude-3.5-haiku",
        "time_limit_minutes": 4,
        "grid_size": 20,
        "difficulty": 3,
    },
    {
        "id": "challenge-5",
        "name": "The Abyss",
        "description": "Design a 25x25 maze that GPT-4o can solve in under 5 minutes",
        "model": "openai/gpt-4o",
        "time_limit_minutes": 5,
        "grid_size": 25,
        "difficulty": 4,
    },
    {
        "id": "challenge-6",
        "name": "Free Agent Frenzy",
        "description": "Create a maze that any free model can solve in 3 minutes",
        "model": "any-free",
        "time_limit_minutes": 3,
        "grid_size": 15,
        "difficulty": 2,
    },
]


def get_challenges() -> List[Dict[str, Any]]:
    """Get all challenges"""
    return CHALLENGES


def get_challenge_by_id(challenge_id: str) -> Dict[str, Any] | None:
    """Get a specific challenge by ID"""
    for challenge in CHALLENGES:
        if challenge["id"] == challenge_id:
            return challenge
    return None
