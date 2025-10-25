#!/usr/bin/env python3
"""
Generate test questions from chunks using LLM APIs.
This creates question candidates that will be manually reviewed and curated.

The script uses two approaches:
1. Extract existing interview questions from chunks (e.g., from interview-questions/ pages)
2. Generate synthetic questions for other chunks using LLM (Anthropic, OpenAI, or local models)

Supports multiple LLM providers:
- Anthropic (claude-3-5-haiku, claude-3-5-sonnet, etc.)
- OpenAI (gpt-4o, gpt-4o-mini, gpt-3.5-turbo, etc.)
- Local models via OpenAI-compatible API (LM Studio, Ollama, etc.)
"""

import os
import json
import yaml
import random
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from collections import defaultdict

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables only


def load_config(config_path: str = 'generate_qa.yaml') -> Optional[Dict[str, Any]]:
    """Load configuration from YAML file."""
    if not Path(config_path).exists():
        return None

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def load_chunk(chunk_path):
    """Load a chunk file and parse its frontmatter."""
    with open(chunk_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split frontmatter and content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return frontmatter, body
    return {}, content


def extract_interview_question(chunk_meta, chunk_body):
    """
    Extract interview questions from chunks that contain them.
    Returns (question, answer) tuple or None if not an interview question.
    """
    # Check if this is an interview question page
    url = chunk_meta.get('original_url', '')
    if 'interview-question' not in url:
        return None

    # Try to extract question from section_path (most reliable)
    section_path = chunk_meta.get('section_path', [])
    question = None

    # Look for question in section headers or title
    for section in section_path:
        if '?' in section or any(keyword in section.lower() for keyword in ['what', 'how', 'when', 'why', 'which', 'where']):
            question = section
            break

    # Also check h1 headers in content
    if not question:
        h1_match = re.search(r'^# (.+?)$', chunk_body, re.MULTILINE)
        if h1_match:
            potential_q = h1_match.group(1).strip()
            if '?' in potential_q or any(keyword in potential_q.lower() for keyword in ['what', 'how', 'when', 'why', 'which', 'where']):
                question = potential_q

    # If we found a question and have substantial content, this is valid
    if question and chunk_meta.get('word_count', 0) > 30:
        # Clean up the question
        question = re.sub(r'\s+', ' ', question)  # Normalize whitespace
        question = question.strip('`')  # Remove code backticks from question

        return question, chunk_body

    return None


def list_available_models(provider: str, config: Dict[str, Any]):
    """List available models from the specified provider."""

    print(f"\n{'='*60}")
    print(f"Available Models for {provider.upper()}")
    print(f"{'='*60}\n")

    if provider == 'anthropic':
        # Anthropic doesn't have a public models API, so list common models
        print("Common Anthropic Claude Models:")
        print("\nRecommended models:")
        print("  • claude-3-5-sonnet-20241022   - Latest Sonnet (best balance)")
        print("  • claude-3-5-haiku-20241022    - Fast and efficient")
        print("\nOther models:")
        print("  • claude-3-opus-20240229       - Most capable (slower)")
        print("  • claude-3-sonnet-20240229     - Previous Sonnet")
        print("  • claude-3-haiku-20240307      - Previous Haiku")

        print("\n✓ Configure in generate_qa.yaml under models.anthropic.model")
        print("📖 Docs: https://docs.anthropic.com/en/docs/models-overview")

    elif provider == 'openai':
        try:
            from openai import OpenAI

            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                print("✗ OPENAI_API_KEY not set. Cannot fetch models.")
                print("\nCommon OpenAI Models:")
                print("  • gpt-4o              - Latest GPT-4 Optimized")
                print("  • gpt-4o-mini         - Fast and affordable")
                print("  • gpt-4-turbo         - Previous GPT-4 Turbo")
                print("  • gpt-3.5-turbo       - Fast, cost-effective")
                return

            client = OpenAI(api_key=api_key)
            models = client.models.list()

            # Filter to relevant chat models
            chat_models = [m for m in models.data if 'gpt' in m.id.lower()]
            chat_models.sort(key=lambda x: x.id)

            print("Available chat models:")
            for model in chat_models:
                print(f"  • {model.id}")

            print(f"\n✓ Found {len(chat_models)} models")
            print("✓ Configure in generate_qa.yaml under models.openai.model")

        except ImportError:
            print("✗ openai package not installed. Install with: pip install openai")
        except Exception as e:
            print(f"✗ Error fetching models: {e}")

    elif provider == 'local':
        model_config = config.get('models', {}).get('local', {})
        base_url = model_config.get('base_url', 'http://localhost:1234/v1')

        try:
            from openai import OpenAI

            print(f"Querying local server at: {base_url}")
            client = OpenAI(
                base_url=base_url,
                api_key=model_config.get('api_key', 'not-needed')
            )

            models = client.models.list()

            if models.data:
                print("\nAvailable local models:")
                for model in models.data:
                    print(f"  • {model.id}")
                print(f"\n✓ Found {len(models.data)} models")
            else:
                print("\n⚠ No models found. Is your local server running?")
                print("\nFor LM Studio: http://localhost:1234/v1")
                print("For Ollama: http://localhost:11434/v1")

            print("\n✓ Configure in generate_qa.yaml under models.local.model")

        except ImportError:
            print("✗ openai package not installed. Install with: pip install openai")
        except Exception as e:
            print(f"✗ Error connecting to local server: {e}")
            print(f"\nMake sure your local server is running at: {base_url}")
            print("  • LM Studio: Start the local server")
            print("  • Ollama: Run 'ollama serve'")


def create_llm_client(provider: str, config: Dict[str, Any]):
    """Create appropriate LLM client based on provider."""

    if provider == 'anthropic':
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")

        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        return Anthropic(api_key=api_key), config.get('models', {}).get('anthropic', {})

    elif provider in ['openai', 'local']:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Install with: pip install openai")

        model_config = config.get('models', {}).get(provider, {})

        if provider == 'openai':
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            return OpenAI(api_key=api_key), model_config
        else:  # local
            base_url = model_config.get('base_url', 'http://localhost:1234/v1')
            api_key = model_config.get('api_key', 'not-needed')
            return OpenAI(base_url=base_url, api_key=api_key), model_config

    else:
        raise ValueError(f"Unknown provider: {provider}. Must be 'anthropic', 'openai', or 'local'")


def generate_questions_for_chunk_anthropic(client, model_config: Dict, chunk_path, chunk_meta, chunk_body, num_questions=3):
    """Generate questions using Anthropic API."""

    # Skip very short chunks
    if chunk_meta.get('word_count', 0) < 20:
        return []

    prompt = f"""Based on the following content chunk, generate {num_questions} test questions that this chunk would be the BEST answer for.

Content metadata:
- Source: {chunk_meta.get('original_url', 'Unknown')}
- Section: {' > '.join(chunk_meta.get('section_path', [])) if chunk_meta.get('section_path') else 'No section'}
- Title: {chunk_meta.get('title', 'Unknown')}

Chunk content:
{chunk_body}

Generate {num_questions} questions as a JSON array. Each question should:
1. Be specific and directly answerable by this chunk
2. Use natural language (how a real user would ask)
3. Not mention "this chunk" or "this content" - ask as if searching a knowledge base
4. Include different question types: factual, how-to, conceptual, troubleshooting

Return ONLY a JSON array of strings, nothing else. Example:
["How do I create a new Swift project?", "What is the difference between let and var?"]"""

    try:
        response = client.messages.create(
            model=model_config.get('model', 'claude-3-5-haiku-20241022'),
            max_tokens=model_config.get('max_tokens', 1000),
            temperature=model_config.get('temperature', 0.7),
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        text = response.content[0].text.strip()
        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()

        questions = json.loads(text)

        # Create question-chunk pairs
        results = []
        for q in questions:
            results.append({
                'question': q,
                'chunk_id': chunk_meta.get('chunk_id'),
                'chunk_path': str(chunk_path),
                'source_url': chunk_meta.get('original_url'),
                'section_path': chunk_meta.get('section_path', []),
                'confidence': 'auto-generated',
                'reviewed': False
            })
        return results

    except Exception as e:
        print(f"Error: {e}")
        return []


def save_qa_as_markdown(questions: List[Dict], output_dir: Path, provider: str, model_name: str):
    """
    Save QA pairs as individual markdown files with frontmatter.
    Groups questions by chunk file and numbers them sequentially.
    Body contains only the question text, all metadata in frontmatter.
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group questions by chunk file
    questions_by_chunk = defaultdict(list)
    for q in questions:
        chunk_path = Path(q['chunk_path'])
        # Get base name without extension and without chunk suffix (_0001, _0002, etc.)
        chunk_base = re.sub(r'_\d{4}\.md$', '', chunk_path.stem)
        questions_by_chunk[chunk_base].append(q)

    generation_date = datetime.now().strftime('%Y-%m-%d')
    total_saved = 0

    # Save each QA pair as a separate markdown file
    for chunk_base, chunk_questions in questions_by_chunk.items():
        for idx, q in enumerate(chunk_questions, 1):
            # Create filename: chunk_base_001.md, chunk_base_002.md, etc.
            qa_filename = f"{chunk_base}_{idx:03d}.md"
            qa_path = output_dir / qa_filename

            # Create frontmatter with all metadata
            frontmatter = {
                'chunk_file': q['chunk_path'],
                'chunk_id': q.get('chunk_id', 'N/A'),
                'source_url': q.get('source_url', 'N/A'),
                'generation_model': model_name,
                'generation_date': generation_date,
                'source_type': q.get('source_type', 'unknown'),
                'confidence': q.get('confidence', 'unknown')
            }

            # Add section_path only if present
            if q.get('section_path'):
                frontmatter['section_path'] = q['section_path']

            # Create markdown content - only the question in the body
            content = f"""---
{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True).strip()}
---

{q['question']}
"""

            # Write to file
            with open(qa_path, 'w', encoding='utf-8') as f:
                f.write(content)

            total_saved += 1

    return total_saved


def generate_questions_for_chunk_openai(client, model_config: Dict, chunk_path, chunk_meta, chunk_body, num_questions=3):
    """Generate questions using OpenAI or OpenAI-compatible API."""

    # Skip very short chunks
    if chunk_meta.get('word_count', 0) < 20:
        return []

    prompt = f"""Based on the following content chunk, generate {num_questions} test questions that this chunk would be the BEST answer for.

Content metadata:
- Source: {chunk_meta.get('original_url', 'Unknown')}
- Section: {' > '.join(chunk_meta.get('section_path', [])) if chunk_meta.get('section_path') else 'No section'}
- Title: {chunk_meta.get('title', 'Unknown')}

Chunk content:
{chunk_body}

Generate {num_questions} questions as a JSON array. Each question should:
1. Be specific and directly answerable by this chunk
2. Use natural language (how a real user would ask)
3. Not mention "this chunk" or "this content" - ask as if searching a knowledge base
4. Include different question types: factual, how-to, conceptual, troubleshooting

Return ONLY a JSON array of strings, nothing else. Example:
["How do I create a new Swift project?", "What is the difference between let and var?"]"""

    try:
        response = client.chat.completions.create(
            model=model_config.get('model', 'gpt-4o-mini'),
            max_tokens=model_config.get('max_tokens', 1000),
            temperature=model_config.get('temperature', 0.7),
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        text = response.choices[0].message.content.strip()
        # Remove markdown code blocks if present
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
            text = text.strip()

        questions = json.loads(text)

        # Create question-chunk pairs
        results = []
        for q in questions:
            results.append({
                'question': q,
                'chunk_id': chunk_meta.get('chunk_id'),
                'chunk_path': str(chunk_path),
                'source_url': chunk_meta.get('original_url'),
                'section_path': chunk_meta.get('section_path', []),
                'confidence': 'auto-generated',
                'reviewed': False
            })
        return results

    except Exception as e:
        print(f"Error: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Generate test questions from chunks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Configuration:
  Uses generate_qa.yaml if present, or command-line arguments.
  Command-line arguments override config file settings.

LLM Providers:
  anthropic: Requires ANTHROPIC_API_KEY environment variable
  openai:    Requires OPENAI_API_KEY environment variable
  local:     Uses OpenAI-compatible API (LM Studio, Ollama, etc.)

Examples:
  # List available models
  python3 generate_qa.py --list-models
  python3 generate_qa.py --list-models --provider openai
  python3 generate_qa.py --list-models --provider local

  # Extract only (no API needed)
  python3 generate_qa.py --extract-only

  # With config file (default)
  python3 generate_qa.py

  # Override provider
  python3 generate_qa.py --provider openai

  # Override all settings
  python3 generate_qa.py chunks/ -n 100 -q 5 --provider local
        """)
    parser.add_argument('chunks_dir', nargs='?',
                       help='Directory containing chunk files (default: from config or chunks/)')
    parser.add_argument('-n', '--num-chunks', type=int,
                       help='Number of chunks to sample for synthetic generation')
    parser.add_argument('-q', '--questions-per-chunk', type=int,
                       help='Questions to generate per chunk')
    parser.add_argument('-o', '--output',
                       help='Output JSON file')
    parser.add_argument('--pattern',
                       help='File pattern to match (default: *.md)')
    parser.add_argument('--extract-only', action='store_true',
                       help='Only extract existing interview questions, skip API generation')
    parser.add_argument('--random-seed', type=int,
                       help='Random seed for reproducible sampling')
    parser.add_argument('--provider', choices=['anthropic', 'openai', 'local'],
                       help='LLM provider to use (anthropic, openai, or local)')
    parser.add_argument('--config', default='generate_qa.yaml',
                       help='Config file path (default: generate_qa.yaml)')
    parser.add_argument('--list-models', action='store_true',
                       help='List available models for the selected provider and exit')

    args = parser.parse_args()

    # Load config file
    config = load_config(args.config)
    if config:
        if not args.list_models:
            print(f"✓ Loaded configuration from {args.config}")
    else:
        config = {}
        if not args.list_models:
            print(f"No config file found, using defaults and command-line args")

    # Handle --list-models
    if args.list_models:
        provider = args.provider or config.get('llm_provider', 'anthropic')
        list_available_models(provider, config)
        return 0

    # Merge config with command-line args (args take precedence)
    chunks_dir = Path(args.chunks_dir or config.get('chunks_dir', 'chunks'))
    num_chunks = args.num_chunks if args.num_chunks is not None else config.get('num_chunks', 50)
    questions_per_chunk = args.questions_per_chunk if args.questions_per_chunk is not None else config.get('questions_per_chunk', 3)

    # Support both output_dir (new) and output_file (legacy)
    if args.output:
        # Command-line arg provided - check if it's a directory or file
        output_path = Path(args.output)
        if output_path.suffix == '' or output_path.suffix == '.md':
            output_dir = output_path if output_path.suffix == '' else output_path.parent
            legacy_mode = False
        else:
            # Legacy JSON file mode
            output_file = output_path
            output_dir = None
            legacy_mode = True
    else:
        # Use config or default
        output_dir = Path(config.get('output_dir', 'qa'))
        output_file = config.get('output_file')  # May be None
        legacy_mode = False if not output_file else True

    pattern = args.pattern or config.get('pattern', '*.md')
    random_seed = args.random_seed if args.random_seed is not None else config.get('random_seed', 42)
    extract_only = args.extract_only or (num_chunks == 0)
    provider = args.provider or config.get('llm_provider', 'anthropic')

    # Find all chunks
    all_chunks = list(chunks_dir.glob(pattern))
    print(f"Found {len(all_chunks)} total chunks in {chunks_dir}")

    # Phase 1: Extract existing interview questions
    extract_interviews = config.get('extract_interview_questions', True)
    extracted_questions = []

    if extract_interviews:
        print("\n=== Phase 1: Extracting existing interview questions ===")
        interview_chunks = [c for c in all_chunks if 'interview-question' in str(c)]

        for i, chunk_path in enumerate(interview_chunks, 1):
            if i % 100 == 0:
                print(f"  Processed {i}/{len(interview_chunks)} interview chunks...")

            chunk_meta, chunk_body = load_chunk(chunk_path)
            result = extract_interview_question(chunk_meta, chunk_body)

            if result:
                question, answer = result
                extracted_questions.append({
                    'question': question,
                    'chunk_id': chunk_meta.get('chunk_id'),
                    'chunk_path': str(chunk_path),
                    'source_url': chunk_meta.get('original_url'),
                    'section_path': chunk_meta.get('section_path', []),
                    'confidence': 'extracted',
                    'reviewed': False,
                    'source_type': 'interview_question'
                })

        print(f"✓ Extracted {len(extracted_questions)} interview questions from {len(interview_chunks)} chunks")

    # Phase 2: Generate synthetic questions (if not extract-only)
    synthetic_questions = []
    if not extract_only and num_chunks > 0:
        print(f"\n=== Phase 2: Generating synthetic questions using {provider} ===")

        try:
            # Create LLM client
            client, model_config = create_llm_client(provider, config)
            model_name = model_config.get('model', 'unknown')
            print(f"✓ Using model: {model_name}")

            # Sample non-interview chunks for generation
            non_interview_chunks = [c for c in all_chunks if 'interview-question' not in str(c)]
            random.seed(random_seed)
            sampled_chunks = random.sample(non_interview_chunks, min(num_chunks, len(non_interview_chunks)))
            print(f"Sampling {len(sampled_chunks)} chunks for generation")

            # Select appropriate generation function
            if provider == 'anthropic':
                generate_fn = generate_questions_for_chunk_anthropic
            else:  # openai or local
                generate_fn = generate_questions_for_chunk_openai

            for i, chunk_path in enumerate(sampled_chunks, 1):
                print(f"[{i}/{len(sampled_chunks)}] {chunk_path.name}...", end=' ')

                chunk_meta, chunk_body = load_chunk(chunk_path)
                questions = generate_fn(
                    client, model_config, chunk_path, chunk_meta, chunk_body,
                    questions_per_chunk
                )

                # Mark as synthetic
                for q in questions:
                    q['source_type'] = 'synthetic'

                print(f"{len(questions)} questions")
                synthetic_questions.extend(questions)

            print(f"✓ Generated {len(synthetic_questions)} synthetic questions")

        except Exception as e:
            print(f"\n✗ Error setting up {provider} client: {e}")
            print(f"Skipping synthetic generation")

    # Combine all questions
    all_questions = extracted_questions + synthetic_questions

    # Determine model name for frontmatter
    if extract_only:
        model_name = 'extracted'
    else:
        model_config = config.get('models', {}).get(provider, {})
        model_name = model_config.get('model', provider)

    # Save results
    print(f"\n{'='*60}")
    if legacy_mode and output_file:
        # Legacy JSON mode
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'total_questions': len(all_questions),
                    'extracted_questions': len(extracted_questions),
                    'synthetic_questions': len(synthetic_questions),
                    'chunks_dir': str(chunks_dir),
                    'random_seed': random_seed,
                    'llm_provider': provider if not extract_only else 'none',
                    'config_file': args.config if config else None
                },
                'questions': all_questions
            }, f, indent=2, ensure_ascii=False)

        print(f"✓ Total questions: {len(all_questions)}")
        print(f"  - Extracted from interview pages: {len(extracted_questions)}")
        print(f"  - Synthetically generated: {len(synthetic_questions)}")
        print(f"✓ Saved to {output_file} (legacy JSON format)")
        print(f"\nNext steps:")
        print(f"  1. Review questions: python3 review_qa.py {output_file}")
        print(f"  2. Export curated set: python3 export_qa.py <curated_file>")
    else:
        # New markdown mode
        num_saved = save_qa_as_markdown(all_questions, output_dir, provider, model_name)

        print(f"✓ Total questions: {len(all_questions)}")
        print(f"  - Extracted from interview pages: {len(extracted_questions)}")
        print(f"  - Synthetically generated: {len(synthetic_questions)}")
        print(f"✓ Saved {num_saved} markdown files to {output_dir}/")
        print(f"\nEach QA pair is saved as: <chunk_base>_NNN.md")
        print(f"Example: hackingwithswift.com_interview-questions_001.md")

    return 0


if __name__ == '__main__':
    exit(main())
