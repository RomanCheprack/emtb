import os
from openai import OpenAI

def create_ai_prompt(bikes_to_compare):
    """Create a prompt for AI comparison"""
    prompt = """אתה מומחה לאופני הרים חשמליים (eMTB). אני רוצה שתעשה השוואה מפורטת בין האופניים הבאים:

"""
    
    for i, bike in enumerate(bikes_to_compare, 1):
        prompt += f"""
אופניים {i}:
- דגם: {bike.get('model', 'N/A')}
- חברה: {bike.get('firm', 'N/A')}
- שנה: {bike.get('year', 'N/A')}
- מחיר: {bike.get('price', 'N/A')}
- מחיר מבצע: {bike.get('disc_price', 'N/A')}
- מנוע: {bike.get('motor', 'N/A')}
- סוללה: {bike.get('battery', 'N/A')}
- שלדה: {bike.get('frame', 'N/A')}
- מזלג: {bike.get('fork', 'N/A')}
- בולם זעזועים אחורי: {bike.get('rear_shock', 'N/A')}
- קטגוריה: {bike.get('sub_category', 'N/A')}
- קיבולת סוללה (Wh): {bike.get('wh', 'N/A')}
- אורך מזלג (mm): {bike.get('fork_length', 'N/A')}

"""
    
    prompt += """
אנא עשה השוואה מפורטת בעברית שתכלול:

1. פתיח ידידותי שמציג את הדגמים
2. השוואה מפורטת של כל דגם עם:
   - יתרונות (pros)
   - חסרונות (cons) 
   - למי מתאים הדגם (best_for)
3. המלצה ברורה על הדגם המומלץ עם הסבר מפורט
4. טיפ מומחה מעניין ומצחיק

החזר את התשובה בפורמט JSON עם המבנה הבא:
{
  "intro": "פתיח ידידותי בעברית...",
  "recommendation": "הסבר בהרחבה מהו הדגם המומלץ...",
  "bikes": [
    {
      "name": "שם הדגם",
      "pros": ["יתרון 1", "יתרון 2"],
      "cons": ["חסרון 1", "חסרון 2"],
      "best_for": "הסבר בהרחבה מיהו הרוכב..."
    }
  ],
  "expert_tip": "טיפ מעניין, מצחיק, חשוב..."
}

שים דגש על:
- שפה ידידותית ונגישה
- הסברים מפורטים
- המלצות מעשיות
- טיפים שימושיים
"""
    
    return prompt

def generate_comparison_with_ai(prompt):
    """Generate comparison using OpenAI API"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "אתה מומחה לאופני הרים חשמליים עם ידע מעמיק בתחום. תן תשובות מפורטות ומקצועיות בעברית."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse the JSON response
        import json
        result = response.choices[0].message.content.strip()
        
        # Try to extract JSON from the response
        try:
            # Find JSON in the response
            start = result.find('{')
            end = result.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = result[start:end]
                return json.loads(json_str)
            else:
                # Fallback: return as text
                return {"error": "Could not parse JSON response", "raw_response": result}
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return {"error": "Invalid JSON response", "raw_response": result}
            
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return {"error": f"OpenAI API error: {str(e)}"}
