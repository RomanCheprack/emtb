import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_ai_prompt(bikes_to_compare):
    """Create a compact prompt with only bike specs"""
    prompt = []
    for i, bike in enumerate(bikes_to_compare, 1):
        specs = f"""
        דגם: {bike.get('model','N/A')}
        חברה: {bike.get('firm','N/A')}
        שנה: {bike.get('year','N/A')}
        מנוע: {bike.get('motor','N/A')}
        סוללה: {bike.get('battery','N/A')}
        שלדה: {bike.get('frame','N/A')}
        מזלג: {bike.get('fork','N/A')}
        בולם אחורי: {bike.get('rear_shock','N/A')}
        קטגוריה: {bike.get('sub_category','N/A')}
        קיבולת סוללה (Wh): {bike.get('wh','N/A')}
        מהלך מזלג (mm): {bike.get('fork_length','N/A')}
        מחיר: {bike.get('price','N/A')} (מבצע: {bike.get('disc_price','N/A')})
        """
        prompt.append(f"אופניים {i}:\n{specs}")
    return "\n\n".join(prompt)

def generate_comparison_with_ai(prompt):
    """Generate Hebrew bike comparison with OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "אתה כתב מגזין מומחה לאופני הרים חשמליים. "
                        "תן סקירה בעברית תקינה, קלילה וקולחת, בסגנון מגזין כמו Bikepanel. "
                        "שים דגש על חווית רכיבה, יתרונות, חסרונות והמלצה ברורה. "
                        "החזר תשובה בפורמט JSON בלבד לפי המבנה: "
                        "{'intro': str, 'recommendation': str, 'bikes':[{'name': str, 'pros':[str], 'cons':[str], 'best_for': str}], 'expert_tip': str}"
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1000
        )

        result = response.choices[0].message.content.strip()

        # Try JSON parsing
        start = result.find('{')
        end = result.rfind('}') + 1
        if start != -1 and end != 0:
            return json.loads(result[start:end])
        return {"error": "Could not parse JSON", "raw_response": result}

    except Exception as e:
        return {"error": f"OpenAI API error: {str(e)}"}
