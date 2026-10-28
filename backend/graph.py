"""LangGraph 旅游规划工作流"""
import json
import os
import re
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph


def _query_city_images(city: str) -> list[dict]:
    """从 MySQL city_images 表读取某城市已入库的风景图,失败则回退为空"""
    try:
        from database import SessionLocal
        from models import CityImage

        db = SessionLocal()
        rows = (
            db.query(CityImage)
            .filter(CityImage.city == city)
            .order_by(CityImage.sort.asc(), CityImage.id.asc())
            .all()
        )
        db.close()
        return [
            {
                "spot": r.spot,
                "filename": r.filename,
                "description": r.description or "",
            }
            for r in rows
        ]
    except Exception:
        return []

MODEL_NAME = os.getenv("MODEL_NAME", "qwen-flash")
FAST_MODEL_NAME = os.getenv("FAST_MODEL_NAME", "qwen-flash")
BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=BASE_URL,
    temperature=0.7,
)

# 轻量任务(需求解析)用快模型,显著降低首节点延迟
llm_fast = ChatOpenAI(
    model=FAST_MODEL_NAME,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=BASE_URL,
    temperature=0,
)

# 快模型被限流/不可用时自动降级到主模型
extract_llm = llm_fast.with_fallbacks([llm])


class PlanState(TypedDict):
    user_input: str
    history_text: str
    destination: str
    days: int
    budget: str
    preferences: str
    itinerary: str
    budget_advice: str
    final_plan: str
    spots: list


def _parse_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON 对象"""
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def extract_info(state: PlanState) -> dict:
    """节点1:解析用户需求"""
    prompt = f"""你是旅游需求解析助手。从用户输入中提取旅行规划信息,只输出 JSON,不要输出其他任何内容。

字段说明:
- destination: 目的地(字符串,未知填"待定")
- days: 旅行天数(整数,未知填 3)
- budget: 预算(字符串,未知填"中等")
- preferences: 偏好(字符串,如美食、亲子、摄影、穷游等,未知填"无特殊偏好")
- spots: 目的地 3 个最具代表性的景点名称(字符串数组,无法确定填 [])

历史对话:
{state["history_text"] or "(无)"}

用户输入:{state["user_input"]}
"""
    resp = extract_llm.invoke(prompt)
    data = _parse_json(resp.content)
    days = data.get("days")
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = 3
    spots = data.get("spots")
    if not isinstance(spots, list):
        spots = []
    spots = [str(s) for s in spots][:3]
    return {
        "destination": str(data.get("destination") or "待定"),
        "days": days,
        "budget": str(data.get("budget") or "中等"),
        "preferences": str(data.get("preferences") or "无特殊偏好"),
        "spots": spots,
    }


def _itinerary_prompt(state: PlanState) -> str:
    return f"""你是资深旅行规划师。请为以下需求制定详细的逐日行程,使用 Markdown 格式。

目的地:{state["destination"]}
天数:{state["days"]} 天
预算:{state["budget"]}
偏好:{state["preferences"]}

要求:
1. 按"第 1 天 / 第 2 天..."逐天安排,每天包含上午、下午、晚上的具体安排
2. 推荐当地特色美食
3. 标注景点大致门票价格
4. 合理安排城际与市内交通,行程松紧适度
"""


def generate_itinerary(state: PlanState) -> dict:
    """节点2:生成逐日行程"""
    resp = llm.invoke(_itinerary_prompt(state))
    return {"itinerary": resp.content}


def _budget_prompt(state: PlanState) -> str:
    return f"""你是旅行顾问。针对以下行程给出预算明细与实用贴士,使用 Markdown 格式。

目的地:{state["destination"]},天数:{state["days"]} 天,预算:{state["budget"]},偏好:{state["preferences"]}

包含:
1. 预算明细表(交通/住宿/餐饮/门票/其他,给出估算金额)
2. 最佳旅行时间与天气提示
3. 必备物品清单
4. 注意事项与避坑建议
"""


def generate_budget_advice(state: PlanState) -> dict:
    """节点3:生成预算明细与实用建议"""
    resp = llm.invoke(_budget_prompt(state))
    return {"budget_advice": resp.content}


SCENERY_DIR = Path(__file__).parent.parent / "frontend" / "public" / "scenery"


def _build_gallery(state: PlanState) -> str:
    """构建配图画廊 Markdown,无图返回空串"""
    city = state.get("destination") or ""

    # 优先用 DB 里已入库的图片元数据(更完整、支持分类与描述)
    gallery_imgs = _query_city_images(city)

    # DB 没命中时回退到旧逻辑:扫描已存在的 spot 本地图片
    if not gallery_imgs:
        fallback = [
            s for s in state.get("spots", [])
            if (SCENERY_DIR / f"{s}.jpg").exists()
        ]
        gallery_imgs = [
            {"spot": s, "filename": f"{s}.jpg", "description": ""}
            for s in fallback
        ]

    if not gallery_imgs:
        return ""
    # 三图一组,每组用空格分隔(Markdown 同行)
    md_rows = []
    for i in range(0, len(gallery_imgs), 3):
        chunk = gallery_imgs[i : i + 3]
        row = " ".join(
            f'![{g["spot"]}](/scenery/{quote(g["filename"])})' for g in chunk
        )
        md_rows.append(row)
    caption = " · ".join(g["spot"] for g in gallery_imgs)
    return f"\n{chr(10).join(md_rows)}\n\n*配图:{caption}(AI 生成风景图库)*\n"


def _build_header(state: PlanState) -> str:
    """方案头部:标题 + 预算偏好 + 图库画廊"""
    return f"""# {state["destination"]} {state["days"]} 日游旅行方案

> 预算:{state["budget"]} | 偏好:{state["preferences"]}
{_build_gallery(state)}
## 行程安排

"""


def assemble(state: PlanState) -> dict:
    """节点4:汇总最终方案"""
    final = (
        _build_header(state)
        + state["itinerary"]
        + "\n\n## 预算与实用贴士\n\n"
        + state["budget_advice"]
        + "\n"
    )
    return {"final_plan": final}


builder = StateGraph(PlanState)
builder.add_node("extract", extract_info)
builder.add_node("itinerary", generate_itinerary)
builder.add_node("budget", generate_budget_advice)
builder.add_node("assemble", assemble)
builder.set_entry_point("extract")
# itinerary 与 budget 互不依赖,并行执行,总耗时≈较慢的一个
builder.add_edge("extract", "itinerary")
builder.add_edge("extract", "budget")
builder.add_edge("itinerary", "assemble")
builder.add_edge("budget", "assemble")
builder.add_edge("assemble", END)

travel_graph = builder.compile()


def run_planner(user_input: str, history_text: str = "") -> dict:
    """运行一次完整规划流程"""
    return travel_graph.invoke(
        {
            "user_input": user_input,
            "history_text": history_text,
            "destination": "",
            "days": 0,
            "budget": "",
            "preferences": "",
            "itinerary": "",
            "budget_advice": "",
            "final_plan": "",
            "spots": [],
        }
    )


def stream_planner(user_input: str, history_text: str = ""):
    """流式规划生成器:逐 token 产出 Markdown,供 SSE 推送给前端

    事件格式:
      {"type": "meta",  "destination": ..., "days": ..., "content": 方案头部}
      {"type": "token", "content": ...}      逐 token 的正文
      {"type": "done",  "plan": 完整方案, "destination": ..., "days": ...}
    """
    base_state: PlanState = {
        "user_input": user_input,
        "history_text": history_text,
        "destination": "",
        "days": 0,
        "budget": "",
        "preferences": "",
        "itinerary": "",
        "budget_advice": "",
        "final_plan": "",
        "spots": [],
    }
    # 1) 需求解析(快模型,非流式,通常 <3s)
    base_state.update(extract_info(base_state))

    # 2) 先吐出方案头部(标题/预算/画廊),前端立即可见
    header = _build_header(base_state)
    yield {
        "type": "meta",
        "destination": base_state["destination"],
        "days": base_state["days"],
        "content": header,
    }
    parts = [header]

    # 3) 流式生成逐日行程
    itinerary = ""
    for chunk in llm.stream(_itinerary_prompt(base_state)):
        if chunk.content:
            itinerary += chunk.content
            yield {"type": "token", "content": chunk.content}
    parts.append(itinerary)

    # 4) 流式生成预算与贴士
    divider = "\n\n## 预算与实用贴士\n\n"
    yield {"type": "token", "content": divider}
    parts.append(divider)

    budget_text = ""
    for chunk in llm.stream(_budget_prompt(base_state)):
        if chunk.content:
            budget_text += chunk.content
            yield {"type": "token", "content": chunk.content}
    parts.append(budget_text + "\n")

    yield {
        "type": "done",
        "plan": "".join(parts),
        "destination": base_state["destination"],
        "days": base_state["days"],
    }
