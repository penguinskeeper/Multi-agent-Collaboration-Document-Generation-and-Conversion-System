#  get_assistant_list 获取聊天助手和知识库信息
#  create_ask_delete  创建提问和删除会话获取rag查询结果
import logging
from langchain_core.tools import tool
# 导入依赖
from ragflow_sdk import RAGFlow #链接rag服务的客户端

from api.monitor import monitor
from rawflow.rag_config import _load_ragflow_env

logger = logging.getLogger(__name__)

# RAGFlow 客户端懒加载缓存：缺失环境变量时返回 None（优雅降级），
# 保证 CI / 未配置 RAGFlow 的环境下模块可以正常 import，调用工具时才返回明确提示。
_ragflow_client = None

def _get_ragflow_client():
    global _ragflow_client
    if _ragflow_client is None:
        api_key, base_url = _load_ragflow_env()
        if not api_key or not base_url:
            return None
        try:
            _ragflow_client = RAGFlow(api_key=api_key, base_url=base_url)
        except Exception as e:
            logger.warning("RAGFlow 客户端初始化失败: %s", e)
            return None
    return _ragflow_client



# 1. 查询现在知识库中有哪些聊天助手和对应知识库的信息 （方便我们知道rag可以给我们提供哪些数据）
@tool
def get_assistant_list() -> str:
    """
    调用此工具，可以查询ragflow服务器中有哪些助手和助手关联的知识库信息！
    供模型参考，可以从哪个助手获取对应的内部文档信息！
    强调：想向某个助手提问，必须想要调用此工具查询助手的信息和名称
    返回结果： 有-> 名称:助手名称,助手描述：xxxx,关联的知识库：知识库的名、知识库的名字、
             没有 -> 没有任何可用助手
             异常 -> 查询助手信息异常，无可用助手
    :return:
    """

    # 埋点,调用工具了告诉前端哪个工具被调用了！！
    monitor.report_tool(tool_name="ragflow聊天助手列表查询工具：get_assistant_list")

    # 1. 创建ragflow客户端
    ragflow_client = _get_ragflow_client()
    if ragflow_client is None:
        return "RAGFlow 服务未配置或不可用（请检查 .env 中的 RAGFLOW_API_URL / RAGFLOW_API_KEY）"
    try:
        # 2. ragflow客户端查询所有的聊天助手 page: int = 1, page_size: int = 30
        chat_list = ragflow_client.list_chats()
        if not chat_list:
            return "没有任何可用助手"
        # 3. 查询聊天助手的知识库信息
        count_chat_info = "" #存储所有会话信息
        for chat in chat_list:
            dataset_names = []
            dataset_list = chat.datasets #当前聊天助手关联的知识库
            if dataset_list and isinstance(dataset_list,list):
                # 知识库的name
                for dataset in dataset_list:
                    # print(dataset)
                    dataset_names.append(dataset['name']) # 将一个助手的知识库的名字加入到列表中

            # 拼接下当前助手的信息 + 知识库信息
            # 法律资源小助手  xxxxxx  关联知识库：xx、xxx、xxx
            count_chat_info += f"助手名称:{chat.name};功能介绍：{chat.description}; 关联的知识库：{'、'.join(dataset_names)} \n"
        return count_chat_info
    except Exception as e:
        return f"查询助手信息异常，无可用助手,异常信息:{str(e)}"

# 2. 对某个助手进行提问（创建会话 -》 提问 -》 删除会话）
@tool
def create_ask_delete(chat_name,question)->str:
    """
    想某个助手，创建单次会话进行提问，提问完毕以后会关闭会话！
    主要查询ragflow中相关的信息！
    注意：调用此工具之前，必须先调用 get_assistant_list工具明确查询助手的名字和对应的问题
    :param chat_name: 助手的名字！上一个工具get_assistant_list告诉大模型的只有名字
    :param question: 本次提问的问题
    :return: 返回提问的结果
    """
    # 埋点,调用工具了告诉前端哪个工具被调用了！！
    monitor.report_tool(tool_name="ragflow提问助手工具：create_ask_delete",args={"chat_name":chat_name,"question":question})

    # 1. 创建ragflow客户端
    ragflow_client = _get_ragflow_client()
    if ragflow_client is None:
        return "RAGFlow 服务未配置或不可用（请检查 .env 中的 RAGFLOW_API_URL / RAGFLOW_API_KEY）"
    # 2. 查询对应name的chat
    try:
        chats = ragflow_client.list_chats(name=chat_name)
        use_chat = chats[0] #选中我们要使用的助手
        # 3. chat上创建一个会话
        session = use_chat.create_session(name="temp_session_ask")
        # 4. 使用会话进行提问
        # 返回的提问结果是流式
        response = session.ask(question = question,stream=True)
        # 接收总结果
        result = ""
        # 流的每一部分的对象 part
        for part in response:
            # 数据存在对象中content上！！
            # print(part.content)
            result = part.content
        # 5. 关闭提问的会话
        # chat -> 关闭 -》  session
        use_chat.delete_sessions(ids=[session.id])
        # 6. 反思检查：答案过短通常意味着问题超出了该助手知识库范围，
        #    回喂提示让模型换角度重新提问，而不是把无效答案传给下游。
        if not result or len(result.strip()) < 20:
            logger.warning("RAG 助手'%s'返回内容过短，启用反思提示", chat_name)
            return (f"助手'{chat_name}'对问题'{question}'的返回内容过短或为空，可能超出了该助手知识库的范围。"
                    "反思提示：请结合助手的描述信息，换一个更贴近其知识领域的角度重新提问。")
        # 7. 返回结果
        return result
    except Exception as e:
        return f"提问失败，错误原因：{str(e)}"

# if __name__ == '__main__':
#     # print(get_assistant_list())
#     print(create_ask_delete("药品知识助手", "感冒药的用法用量和注意事项！"))