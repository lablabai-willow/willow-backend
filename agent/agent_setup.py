# !pip install llama-index google-generativeai openai pypdf pillow python-dotenv

import os
import openai
import logging
import sys
from llama_index.tools import BaseTool, FunctionTool
from llama_index.multi_modal_llms.gemini import GeminiMultiModal
from llama_index.multi_modal_llms.generic_utils import load_image_urls
from typing import List
import os.path
from llama_index import (
  VectorStoreIndex,
  SimpleDirectoryReader,
  StorageContext,
  load_index_from_storage,
  )
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.agent import OpenAIAgent
from llama_index.llms import OpenAI
from dotenv import load_dotenv

load_dotenv()

def agent_setup():
    global agent
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)
    logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

    """### Vectorize Mindfulness Guides"""

    # Attempt to load embeddings
    try:
        storage_context = StorageContext.from_defaults(
            persist_dir="./agent/storage/challenging_child"
        )
        challenging_child_index = load_index_from_storage(storage_context)

        storage_context = StorageContext.from_defaults(
            persist_dir="./agent/storage/mindfulness_TB_50"
        )
        mindfulness_TB_50_index = load_index_from_storage(storage_context)

        storage_context = StorageContext.from_defaults(
            persist_dir="./agent/storage/mindfulness_TB_relationships"
        )
        mindfulness_TB_relationships_index = load_index_from_storage(storage_context)
    except:
        # Need to generate embeddings
        challenging_child_docs = SimpleDirectoryReader(
            input_files=["./agent/data/The_Challenging_Child_Toolbox.pdf"]
        ).load_data(show_progress=True)
        mindfulness_TB_50_docs = SimpleDirectoryReader(
            input_files=["./agent/data/The_Mindfulness_Toolbox__50_Practical_Tips_Tools.pdf"]
        ).load_data(show_progress=True)
        mindfulness_TB_relationships_docs = SimpleDirectoryReader(
            input_files=["./agent/data/The_Mindfulness_Toolbox_for_Relationships.pdf"]
        ).load_data(show_progress=True)

        # Build index
        challenging_child_index = VectorStoreIndex.from_documents(challenging_child_docs)
        mindfulness_TB_50_index = VectorStoreIndex.from_documents(mindfulness_TB_50_docs)
        mindfulness_TB_relationships_index = VectorStoreIndex.from_documents(mindfulness_TB_relationships_docs)

        # Persist
        challenging_child_index.storage_context.persist(persist_dir="./agent/storage/challenging_child")
        mindfulness_TB_50_index.storage_context.persist("./agent/storage/mindfulness_TB_50")
        mindfulness_TB_relationships_index.storage_context.persist(persist_dir="./agent/storage/mindfulness_TB_relationships")

    challenging_child_engine = challenging_child_index.as_query_engine()
    mindfulness_TB_50_engine = mindfulness_TB_50_index.as_query_engine()
    mindfulness_TB_relationships_engine = mindfulness_TB_relationships_index.as_query_engine()

    """### Test to make sure our data loaded"""

    # # The_Challenging_Child_Toolbox
    # query_engine = challenging_child_index.as_query_engine()
    # response = query_engine.query("What is the definition of a challenging child?")
    # print("**Response:**\n\n",response)

    # # The_Mindfulness_Toolbox__50_Practical_Tips_Tools
    # query_engine = mindfulness_TB_50_index.as_query_engine()
    # response = query_engine.query("What are the benefits of a mindfulness practice?")
    # print("**Response:**\n\n", response)

    # # The_Mindfulness_Toolbox_for_Relationships
    # query_engine = mindfulness_TB_relationships_index.as_query_engine()
    # response = query_engine.query("How does mindfulness relate to relationships?")
    # print("**Response:**\n\n",response)

    """## Define Agent Tools

    ### Analyze image tool
    """



    def analyze_image(img_urls: List[str]) -> str:
        """Calls our Gemini vision API to analyze the image and return a description of the text contained in the image.
            Returns: A string with a description of the image and the mood it conveys if any.

        Args:
            img_urls (List[str]): The URL of one or more images that convey the users mood
        """
        image_documents = load_image_urls(img_urls)

        gemini = GeminiMultiModal(model="models/gemini-pro-vision", api_key=os.environ.get("GOOGLE_API_KEY"))

        complete_response = gemini.complete(
            prompt="Identify what you see in the image and what mood it conveys if any",
            image_documents=image_documents,
        )

        return complete_response

    vision_tool = FunctionTool.from_defaults(fn=analyze_image)

    """### Save session tool"""

    def save_session(chat_summary: str) -> bool:
        """Persists a summary of the user's chat history. Use this tool when the user is happy with your recomendations and done with the session
            Returns: A boolean saying if the chat history was persisted

        Args:
            chat_summary (str): A summary of the chat history, including the users name if it was provided in the chat session
        """

        # Here is where we would persist the chat summary so we can retrive it when we start a new sessions

        return True

    save_tool = FunctionTool.from_defaults(fn=save_session)

    """### Mindfulness routine recomendation tool"""

    query_engine_tools = [
        QueryEngineTool(
            query_engine=challenging_child_engine,
            metadata=ToolMetadata(
                name="challenging_child",
                description=(
                    "The Challenging Child Toolbox 75 Mindfulness Based Practices Tools and Tips for Therapists"
                    "Use a detailed plain text question as input to the tool."
                ),
            ),
        ),
        QueryEngineTool(
            query_engine=mindfulness_TB_50_engine,
            metadata=ToolMetadata(
                name="mindfulness_TB_50",
                description=(
                    "The Mindfulness Toolbox 50 Practical Tips Tools Handouts for Anxiety Depression Stress and Pain"
                    "Use a detailed plain text question as input to the tool."
                ),
            ),
        ),
        QueryEngineTool(
            query_engine=mindfulness_TB_relationships_engine,
            metadata=ToolMetadata(
                name="mindfulness_TB_relationships",
                description=(
                    "The Mindfulness Toolbox for Relationships 50 Practical Tips Tools Handouts for Building Compassionate Connections"
                    "Use a detailed plain text question as input to the tool."
                ),
            ),
        ),
    ]

    tools = query_engine_tools + [vision_tool, save_tool]

    SYSTEM_PROMPT = """You are an emotional support assistant with the expertise of an experienced counselor. Your primary role is to assist the user by encouraging them to provide a drawing that conveys their mood.
    You offer professional, friendly, and helpful guidance based on current counseling and mindfulness practices. Once you receive the image, interpret it to discern what the user might be feeling and confirm with them if your observation is correct.
    If your interpretation does not align with their feelings, engage in a dialogue until you accurately understand their mood. Your knowledge is exclusively focused on understanding the user's emotions and recommending mindfulness routines using the tool, tailored to their mood.
    Thus, you will only provide responses related to these areas. If a question falls outside your area of expertise or if you lack the necessary information, you will inform the user by saying,
    'Sorry, I do not know the answer to your question.' and then prompt for more information related to their feelings. Once they confirm that you have correctly understood their feelings, your task is to recommend a suitable mindfulness routine using the tool."""

    llm = OpenAI(model="gpt-4-1106-preview") # Using GPT-4 Turbo (Beta)

    agent = OpenAIAgent.from_tools(
        tools,
        llm=llm,
        verbose=True,
        system_prompt=SYSTEM_PROMPT,
    )


    # response = agent.chat("hi I'm Ali")
    # print("**Response:**\n\n",response)
    # response = agent.chat("https://ih1.redbubble.net/image.3636044620.1142/bg,f8f8f8-flat,750x,075,f-pad,750x1000,f8f8f8.u5.jpg")
    # print("**Response:**\n\n",response)
    # print(agent)
    return agent

# print("Agent Setup",agent)