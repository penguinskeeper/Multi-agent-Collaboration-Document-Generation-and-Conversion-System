# 定义一个网络搜索的工具！
# ======================== 导入核心依赖 ========================
# 类型注解：增强代码提示和静态检查能力
from typing import  Literal
# LangChain 工具装饰器：将普通函数转为 Agent 可调用的工具
from langchain_core.tools import tool
# Tavily 官方客户端：实现网络搜索核心功能
from tavily import TavilyClient

# 系统/第三方依赖
import os  # 系统路径/环境变量处理
import logging
from dotenv import load_dotenv  # 加载 .env 文件中的环境变量

# 自定义模块：工具调用埋点监控（需确保 api 模块可导入）
from api.monitor import monitor

logger = logging.getLogger(__name__)

# ======================== 初始化配置 ========================
# 加载项目根目录的 .env 文件，读取环境变量（如 TAVILY_API_KEY）
load_dotenv()


# 步骤1： TavilyClient 懒加载
# 不在模块导入时构造：key 缺失时 import 即崩会让整条导入链（subagents -> main_agent -> server）
# 直接挂掉，谈不上"优雅降级"。改为首次调用工具时才构造，并给出明确的反思提示。
tavily_client = None


def _get_tavily_client():
    global tavily_client
    if tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise RuntimeError("TAVILY_API_KEY 未配置，无法执行网络搜索")
        tavily_client = TavilyClient(api_key=api_key)
    return tavily_client

# 反思机制参数：单次工具调用内最多尝试次数
_MAX_SEARCH_ATTEMPTS = 3


def _simplify_query(query: str) -> str:
    """反思策略1：简化查询——去掉标点和口语化修饰，保留核心关键词"""
    for ch in "？?！!。；;，,、\"'“”‘’（）()[]{}《》<>":
        query = query.replace(ch, " ")
    return " ".join(query.split())


# 步骤2： 定义一个网络搜索工具
@tool
def internet_search(
        query: str,
        topic: Literal[ "news",  "finance",  "general"] = "general",
        max_results: int = 5,
        include_raw_content: bool = False
):
    """
    根据用户问题，进行网络信息搜！
    注意：主要搜索公开的网络信息！如果指定查询数据库或者rag不能使用此工具！
    内置反思重试：结果为空时自动简化关键词/调整类型重试；全部失败会返回反思提示，请根据提示换角度重新检索。
    :param query: 用户的查询信息
    :param topic: 查询的类型
    :param max_results: 返回的最大条数
    :param include_raw_content: 是否返回原内容 False 精简 True 详细
    :return:
    """
    # 每次调用工具，都都会向前端推进调用进度！
    # 参数1： 工具的名字  参数2： 就是调用工具的参数信息
    monitor.report_tool(tool_name="网络搜索工具",
                        args={"query": query, "topic": topic, "max_results": max_results,
                              "include_raw_content": include_raw_content})

    # 配置错误（key 缺失）不值得重试，直接返回反思提示
    try:
        client = _get_tavily_client()
    except Exception as e:
        logger.error("网络搜索工具不可用: %s", e)
        return {"results": [], "reflection": f"搜索服务不可用：{e}。请检查 .env 中 TAVILY_API_KEY 的配置。"}

    current_query, current_topic = query, topic
    for attempt in range(1, _MAX_SEARCH_ATTEMPTS + 1):
        try:
            response = client.search(query=current_query, topic=current_topic,
                                     max_results=max_results,
                                     include_raw_content=include_raw_content)
        except Exception as e:
            logger.warning("网络搜索第 %d 次调用异常: %s", attempt, e)
            response = None

        results = (response or {}).get("results", []) if isinstance(response, dict) \
            else getattr(response, "results", None)

        # 有结果：直接返回（重试后成功则在日志中记录反思过程）
        if results:
            if attempt > 1:
                logger.info("反思重试成功：第 %d 次检索命中（query=%s, topic=%s）",
                            attempt, current_query, current_topic)
            return response

        # 反思：本次无结果，按策略调整后重试
        logger.warning("网络搜索第 %d 次无结果，启用反思策略调整参数", attempt)
        if attempt == 1:
            # 策略1：简化查询关键词
            current_query = _simplify_query(current_query) or current_query
        elif attempt == 2 and current_topic != "general":
            # 策略2：topic 回退为通用类型
            current_topic = "general"
        elif attempt == 2:
            # 策略3：topic 已是 general，同时简化关键词
            current_query = _simplify_query(current_query) or current_query

    # 全部尝试失败：向模型返回反思提示（错误回喂，引导换角度重新检索）
    return {
        "results": [],
        "reflection": (f"已自动尝试 {_MAX_SEARCH_ATTEMPTS} 次检索均未命中（含简化关键词、调整检索类型）,"
                       f"最后使用的关键词为'{current_query}'。"
                       "请反思并更换角度：拆分问题、更换关键词、或改用英文关键词后重新调用本工具。")
    }














