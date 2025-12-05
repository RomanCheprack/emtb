import os
import json
import asyncio
import threading
from typing import Any, Dict, List, Optional

try:
    import aiohttp  # type: ignore
except Exception:
    aiohttp = None
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

async def _search_with_openai_web(bike_query: str) -> Optional[Dict[str, Any]]:
    """Use OpenAI Responses web_search tool for a single query.

    Returns a dict with 'query' and 'answer' text if successful, else None.
    """
    try:
        resp = await asyncio.to_thread(
            client.responses.create,
            model="gpt-4.1-mini",
            input=(
                f"בצע חיפוש אינטרנט קצר ומדויק על הדגם הבא: {bike_query}. "
                "החזר סיכום קצר בעברית עם 3-5 נקודות עיקריות ומקורות."),
            tools=[{"type": "web_search"}],
        )
        text = getattr(resp, "output_text", None)
        if text:
            return {"query": bike_query, "answer": text}
        return None
    except Exception:
        return None


async def _search_with_ddg(session: "aiohttp.ClientSession", bike_query: str) -> Optional[Dict[str, Any]]:
    """DuckDuckGo Instant Answer API as a lightweight fallback."""
    try:
        params = {"q": bike_query, "format": "json", "no_html": 1, "t": "emtb_site"}
        async with session.get("https://api.duckduckgo.com/", params=params, timeout=aiohttp.ClientTimeout(total=12)) as r:
            if r.status != 200:
                return None
            data = await r.json(content_type=None)
            abstract = data.get("AbstractText") or data.get("Heading") or ""
            related = []
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict):
                    txt = topic.get("Text")
                    if txt:
                        related.append(txt)
            combined = (abstract + "\n" + "\n".join(related)).strip()
            if combined:
                return {"query": bike_query, "answer": combined}
            return None
    except Exception:
        return None


async def _gather_bikes_research(bikes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run per-bike research concurrently. Try OpenAI web_search first, then DDG fallback."""
    queries: List[str] = []
    for bike in bikes:
        firm = bike.get("firm", "")
        model = bike.get("model", "")
        year = bike.get("year", "")
        q = " ".join([str(x) for x in [firm, model, year] if x])
        queries.append(q.strip() or "אופניים חשמליים דגם לא ידוע")

    # First try OpenAI web search concurrently (in threadpool since SDK is sync)
    async def _openai_task(q: str) -> Optional[Dict[str, Any]]:
        return await _search_with_openai_web(q)

    openai_results = await asyncio.gather(*[_openai_task(q) for q in queries])

    # For any missing results, fill via DDG concurrently
    results: List[Optional[Dict[str, Any]]] = list(openai_results)
    http_session: Optional["aiohttp.ClientSession"] = None
    if aiohttp is None:
        # aiohttp not available
        ddg_results = [None for _ in results]
    else:
        http_session = aiohttp.ClientSession(headers={"User-Agent": "emtb_site/1.0"})
    if http_session is not None:
        async with http_session as http_session_ctx:
            ddg_tasks = []
            for idx, res in enumerate(results):
                if res is None:
                    ddg_tasks.append(_search_with_ddg(http_session_ctx, queries[idx]))
                else:
                    ddg_tasks.append(asyncio.sleep(0, result=None))
            ddg_results = await asyncio.gather(*ddg_tasks)
    else:
        ddg_results = [None for _ in results]
    for idx, res in enumerate(results):
        if res is None and ddg_results[idx] is not None:
            results[idx] = ddg_results[idx]

    # Build final list aligned with bikes
    final: List[Dict[str, Any]] = []
    for idx, bike in enumerate(bikes):
        final.append({
            "bike": {
                "firm": bike.get("firm"),
                "model": bike.get("model"),
                "year": bike.get("year"),
                "motor": bike.get("motor"),
                "battery": bike.get("battery"),
                "price": bike.get("price"),
                "disc_price": bike.get("disc_price"),
            },
            "research": results[idx] or {"query": None, "answer": ""}
        })
    return final


def _build_comparison_prompt(bikes: List[Dict[str, Any]], research: List[Dict[str, Any]]) -> str:
    """Compose concise Hebrew prompt combining specs and web research."""
    lines: List[str] = []
    for i, item in enumerate(research, 1):
        b = item["bike"]
        r = item["research"]
        specs = (
            f"דגם: {b.get('model','N/A')}\n"
            f"חברה: {b.get('firm','N/A')}\n"
            f"שנה: {b.get('year','N/A')}\n"
            f"מנוע: {b.get('motor','N/A')}\n"
            f"סוללה: {b.get('battery','N/A')}\n"
            f"מחיר: {b.get('price','N/A')} (מבצע: {b.get('disc_price','N/A')})\n"
        )
        web = f"תוצאות חיפוש מקוצרות: {r.get('answer','').strip()}" if r.get('answer') else "אין תוצאות חיפוש."
        lines.append(f"אופניים {i}:\n{specs}\n{web}")
    return "\n\n".join(lines)


def _run_coroutine_blocking(coro: Any) -> Any:
    """Run an async coroutine from sync code safely across environments.

    Handles cases where an event loop is already running by delegating to a new thread.
    """
    try:
        return asyncio.run(coro)
    except RuntimeError as e:
        # If there's already a running loop (e.g., in some servers/notebooks)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            result_container: Dict[str, Any] = {}
            error_container: Dict[str, BaseException] = {}

            def _runner() -> None:
                try:
                    local_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(local_loop)
                    result = local_loop.run_until_complete(coro)
                    result_container["result"] = result
                except BaseException as exc:  # capture to raise after join
                    error_container["exc"] = exc
                finally:
                    try:
                        local_loop.close()
                    except Exception:
                        pass

            thread = threading.Thread(target=_runner, daemon=True)
            thread.start()
            thread.join()
            if "exc" in error_container:
                raise error_container["exc"]
            return result_container.get("result")
        # No running loop: create one and run
        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


def generate_comparison_with_ai_from_bikes(bikes_to_compare: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Public entry: run async research per bike, then call Responses API for structured JSON output.

    Returns dict with intro, recommendation, bikes[], expert_tip. On error returns {"error": ...}.
    """
    try:
        research: List[Dict[str, Any]] = _run_coroutine_blocking(_gather_bikes_research(bikes_to_compare))
    except Exception as e:
        return {"error": f"Async research error: {str(e)}"}

    prompt = _build_comparison_prompt(bikes_to_compare, research)

    try:
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=(
                "אתה כתב מגזין מומחה לאופני הרים חשמליים. "
                "תן סקירה בעברית תקינה, קלילה וקולחת, בסגנון מגזין כמו Bikepanel. "
                "שים דגש על חווית רכיבה, יתרונות, חסרונות והמלצה ברורה. "
                "החזר JSON בלבד במבנה: { 'intro': str, 'recommendation': str, 'bikes': [ { 'name': str, 'pros': [str], 'cons': [str], 'best_for': str } ], 'expert_tip': str }.\n\n" 
                + prompt
            ),
            response_format={"type": "json_object"},
            temperature=0.6,
            timeout=30,
        )
        # Prefer parsed JSON if available
        parsed = getattr(resp, "output_parsed", None)
        if parsed:
            return parsed  # already a dict
        text = getattr(resp, "output_text", None)
        if text:
            return json.loads(text)
        # As a last resort, attempt to stringify the model output
        try:
            content_items = getattr(resp, "output", [])
            if content_items:
                maybe_texts = []
                for item in content_items:
                    # item may have a .content list with .text fields
                    try:
                        for sub in getattr(item, "content", []) or []:
                            t = getattr(sub, "text", None)
                            if t:
                                maybe_texts.append(t)
                    except Exception:
                        pass
                joined = "\n".join(maybe_texts).strip()
                if joined:
                    return json.loads(joined)
        except Exception:
            pass
        return {"error": "Empty response from model"}
    except Exception as e:
        # Fallback to Chat Completions with best-effort JSON parsing
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "אתה כתב מגזין מומחה לאופני הרים חשמליים. "
                            "תן סקירה בעברית תקינה, קלילה וקולחת, בסגנון מגזין כמו Bikepanel. "
                            "שים דגש על חווית רכיבה, יתרונות, חסרונות והמלצה ברורה. "
                            "החזר JSON בלבד במבנה: { 'intro': str, 'recommendation': str, 'bikes': [ { 'name': str, 'pros': [str], 'cons': [str], 'best_for': str } ], 'expert_tip': str }."),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=1000,
            )
            content = completion.choices[0].message.content.strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
            return {"error": "Could not parse JSON from fallback"}
        except Exception as e2:
            return {"error": f"OpenAI Responses error: {str(e)}; fallback error: {str(e2)}"}
