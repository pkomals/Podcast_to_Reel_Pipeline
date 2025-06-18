import openai
import os
import json
from dotenv import load_dotenv

def get_llm_suggestions(transcript_text):
    load_dotenv() 
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set.")

    client = openai.OpenAI(api_key=api_key)

    system_message = (
        "You are an expert podcast summarizer and keyword extractor. "
        "Your task is to analyze the provided podcast transcript, summarize its main content, "
        "and then identify key themes. For each key theme, provide a concise list of "
        "closely related keywords that appear in that context. "
        "Your response MUST be in JSON format, with keys 'summary' (string) and 'key_topics' (list of objects). "
        "Each object in 'key_topics' must have 'theme' (string) and 'keywords' (list of strings)."
    )

    user_message = (
        f"Please analyze the following podcast transcript and provide a summary and grouped keywords as described:\n\nTranscript:\n\"\"\"{transcript_text}\"\"\"\n\nProvide your response in JSON format only." 
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125", 
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            response_format={ "type": "json_object" }
        )
        
        llm_output = response.choices[0].message.content
        suggestions = json.loads(llm_output)
        
        
        if not isinstance(suggestions, dict) or 'summary' not in suggestions or 'key_topics' not in suggestions:
            raise ValueError("LLM did not return expected JSON format.")
        
        return suggestions

    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        print("Please check your API key, network connection, and OpenAI service status.")
        return None
    except json.JSONDecodeError:
        print("Error: LLM response was not valid JSON. Please check the prompt or try again.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during LLM call: {e}")
        return None

if __name__ == "__main__":
    
    # Set your own OPENAI_API_KEY environment variable before running
    sample_transcript = """
    Today we talked about the challenges in education, specifically how poverty impacts student learning. 
    We also discussed new employment opportunities emerging from the green energy sector and how retraining 
    programs can help bridge the skills gap. Climate change was also briefly mentioned.
    """
    print("Testing LLM keyword suggester...")
    suggestions = get_llm_suggestions(sample_transcript)
    if suggestions:
        print("Summary:", suggestions['summary'])
        print("Key Topics:")
        for topic in suggestions['key_topics']:
            print(f"  - {topic['theme']}: {', '.join(topic['keywords'])}")
    else:
        print("Failed to get suggestions.") 