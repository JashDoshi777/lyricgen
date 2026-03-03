"""
AI lyric explanation using Groq.
Sends lyric lines to Groq LLM and returns meaning/emotion/explanation.
"""

import json
from groq import Groq
from config import Config
from cache.chroma_cache import get_cache


def explain_lyric(lyric_line, title='', artist='', context_lines=None):
    """
    Get an AI explanation for a lyric line.

    Args:
        lyric_line: The lyric line to explain.
        title: Song title for context.
        artist: Artist name for context.
        context_lines: Surrounding lyric lines for better context.

    Returns:
        dict: {meaning, emotion, explanation} or error dict.
    """
    if not Config.GROQ_API_KEY:
        return {
            'meaning': 'AI explanations require a Groq API key.',
            'emotion': 'N/A',
            'explanation': 'Set GROQ_API_KEY in your .env file to enable this feature.'
        }

    # Check cache first
    cache = get_cache()
    cached = cache.get_explanation(title, artist, lyric_line)
    if cached:
        return cached

    try:
        client = Groq(api_key=Config.GROQ_API_KEY)

        # Build context
        context = f'Song: "{title}" by {artist}\n' if title else ''
        if context_lines:
            context += f'Surrounding lyrics:\n'
            for line in context_lines:
                context += f'  {line}\n'

        prompt = f"""{context}
Analyze this specific lyric line: "{lyric_line}"

Provide a JSON response with exactly these three fields:
1. "meaning": What this lyric line literally and figuratively means (2-3 sentences)
2. "emotion": The primary emotion or theme (1-3 words, e.g., "Longing", "Defiance", "Bittersweet Love")
3. "explanation": A simple, conversational explanation a casual listener would appreciate (2-3 sentences)

Respond ONLY with valid JSON, no markdown formatting."""

        completion = client.chat.completions.create(
            model=Config.GROQ_MODEL,
            messages=[
                {
                    'role': 'system',
                    'content': 'You are a music analyst and lyric interpreter. You provide insightful, concise explanations of song lyrics. Always respond with valid JSON only.'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            temperature=0.7,
            max_tokens=500,
            top_p=1,
        )

        response_text = completion.choices[0].message.content.strip()

        # Parse JSON response
        # Handle potential markdown code block wrapping
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
            response_text = response_text.strip()

        result = json.loads(response_text)

        # Ensure all fields exist
        explanation = {
            'meaning': result.get('meaning', ''),
            'emotion': result.get('emotion', ''),
            'explanation': result.get('explanation', '')
        }

        # Cache the result
        cache.set_explanation(title, artist, lyric_line, explanation)

        return explanation

    except json.JSONDecodeError as e:
        print(f"[Groq] Failed to parse JSON response: {e}")
        return {
            'meaning': response_text if 'response_text' in dir() else 'Error parsing response',
            'emotion': 'Unknown',
            'explanation': 'The AI response could not be parsed properly.'
        }
    except Exception as e:
        print(f"[Groq] Error: {e}")
        return {
            'meaning': f'Error: {str(e)}',
            'emotion': 'Error',
            'explanation': 'An error occurred while generating the explanation.'
        }
