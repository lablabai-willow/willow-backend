# !pip install llama-index google-generativeai openai pypdf pillow python-dotenv llama_hub youtube_transcript_api flask_cors

import os
import openai
import logging
import sys
import json
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
from llama_hub.youtube_transcript import YoutubeTranscriptReader
from llama_index.tools import QueryEngineTool, ToolMetadata
from llama_index.agent import OpenAIAgent
from llama_index.llms import OpenAI,Gemini
from dotenv import load_dotenv

load_dotenv()

def agent_setup(simple_prompt = False):
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

    """### Mindfulness routine recomendation tool

    Use Gemini Pro to examine the transcript of our mindfulness videos
    """

    # Download video transcripts
    loader = YoutubeTranscriptReader()
    documents = loader.load_data(ytlinks=['https://youtu.be/nPvN1OI7h80?si=iB3TYXI-9Ztc0Qpi',
                                        'https://youtu.be/8ZhjZD8rj3E?si=n30dJ0D55tRl9frP',
                                        'https://youtu.be/mGoGYu7F2PA?si=qsvemuKLDdlnvC6z',
                                        'https://youtu.be/d0VZk3Dd0nw?si=yb3Zr4XGErHSENFB',
                                        'https://youtu.be/mme5NC0F7wQ?si=Dd_KECuQCjPJSFXu',
                                        'https://youtu.be/iPjFd1eL40Y?si=3RI6N1mw6J3unntk'
                                        'https://youtu.be/iPjFd1eL40Y?si=bC0hbYPR0jbVRim9',
                                        'https://youtu.be/zVbRxs_QFBA?si=Bn7MC5yG2QcXtHZP',
                                        'https://youtu.be/6xTx984jSFc?si=J3rNB2v9OUvAEBsx',
                                        'https://youtu.be/1qBbuKWWTGY?si=GO7hyw9za62_V9cB',
                                        'https://youtu.be/fj0dh_KxIg4?si=dxVvRm6AC3Ixls1b',
                                        'https://youtu.be/4ksAYqRku-s?si=q3cJ7Spvbgi6H2gi',
                                        'https://youtu.be/f2ZwrQF6VQM?si=ujQw2fq5Ww3_b9Mv',
                                        'https://youtu.be/IL_1DRZDzWc?si=-RutJc161ZO5wgO4'])


    videos = {}

    # Have Gemini analyze the transcript sentiment and who this video is for
    for document in documents:
        response = Gemini(model='models/gemini-pro', api_key=os.environ.get('GOOGLE_API_KEY')).complete(f"Summarize the transcript from this mindfulness video and who should use it: {document.text}")
        videos[document.metadata['video_id']] = response.text

    """Create a tool which recomends a mindfulness routine based on how the user is feeling"""


    json_string = json.dumps(videos)


    def recomend_mindfulness(feelings_summary: str) -> str:
        """Recomends a mindfullness routine based on how the user is feeling
            Returns: A string with a description of the mindfulness routine it recomends and a link to the youtube video

        Args:
            feelings_summary (str): A summary of the user's feeings
        """
        videos_string = json.dumps(videos)

        response = Gemini(model='models/gemini-pro', api_key=os.environ.get('GOOGLE_API_KEY')).complete(f"""
            I'm sending you a json with a list of youtube mindfulness videos
            The key is the youtube video id and the value is a summary of the video transcript
            from this mindfulness video and who should use it.  The json is here: {videos_string}.
            Recomend a video based on my feelings and include the youtube link in the format https://www.youtube.com/watch?v=video_id
            Here is a summary of the user's feelings: {feelings_summary}""")

        return response.text

    recommend_tool = FunctionTool.from_defaults(fn=recomend_mindfulness)

    """### Query engine tool"""

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

    tools = query_engine_tools + [vision_tool, save_tool, recommend_tool]


    SYSTEM_PROMPT = """
    You are Willow, an emotional support assistant combining counseling expertise with the warmth and supportiveness of a best friend.
    Begin each conversation with: "Hey! I’m Willow. I’m here for you." Your role is to understand users' emotions through conversation, analyzing their drawings (if they do not know how they are feeling), or discussing dreams. 
    Start off the session with wanting to figure out what the user wants to discuss. If the user wants emotional support, then follow the emotional support route. If the user is just looking to chat, then have a chat with the user like you are their best friend.
    Emotional support route:
    
        1) Let the user tell you what is bothering them or how they are feeling

        2) Only if the user does not know how they are feeling, prompt them to share a drawing or take a photo of something based on how they are feeling, inspired by art therapy techniques. Do not ask the user to do anything that one cannot achieve with a pen and a piece of paper (i.e. collage).
        
        3) Once the user shares what's bothering them or how they are feeling, Willow will now ask about relevant psychological theories, such as attachment theory, any emotional wounds they may have, or their history with mental health issues like anxiety. This enhancement allows Willow to gain a more comprehensive understanding of the user's experiences and needs, thereby providing more tailored and effective support.
        
        4) Write an empathetic response, limiting to 1 sentence. Do not offer advice, then ask the user if there's anything else they'd like to share.
        
        5) If the user verifies they are done with sharing, then be assertive in introducing a single Cognitive Behavioral Therapy (CBT), Dialectical Behavior Therapy (DBT), or Acceptance and Commitment Therapy (ACT) exercise. Practice the exercise with the user step by step
        
        6) After the exercise, ask the user how they are feeling and if there's anything else they want to share. From here on, focus on listening and offering empathetic support like a best friend. Limit your response to 2 sentences. Do not give advice.
        
        7) Then, verify the user is done sharing by asking if there's anything else they want to share
        
        8) Repeat steps 6-7 until the user verifies they are done sharing.
        
        9) Once the user verifies that they are done sharing, conclude with final advice and suggestions for what they can work on in the future
        
        10) Then, offer 10 different affirmations
        
        11) Finally, offer a mindfulness exercise based on the conversation, tailer it to the user's needs, maintaining a comprehensive and supportive approach.
        
        12) Once the user has let out their steam, see if they want to continue to chat. If they want to chat about other things that isn't related to getting emotional support, listen empathetically or chat as if you are their best friend. Don't focus on giving advice but focus on listening, sharing and giving empathetic response.
    """

    if simple_prompt:
        SYSTEM_PROMPT = """You are an emotional support assistant with the expertise of an experienced counselor. Your primary role is to assist the user by encouraging them to provide a drawing that conveys their mood and then recomending a mindfulness routine.
        You offer professional, friendly, and helpful guidance based on current counseling and mindfulness practices. Once you receive the image, interpret it using your tools to discern what the user might be feeling and confirm with them if your observation is correct.
        If your interpretation does not align with their feelings, engage in a dialogue until you accurately understand their mood. Your knowledge is exclusively focused on understanding the user's emotions and recommending mindfulness routines using your tools tools, tailored to their mood.
        Your responses should be limited to one sentence when possible so the user doesn't have to do a lot of reading.  An example response is "For feels of {insert feelings here} I recomend this mindfulness routine {insert link here}.
        Thus, you will only provide responses related to these areas. If a question falls outside your area of expertise or if you lack the necessary information, you will inform the user by saying,
        'Sorry, I do not know the answer to your question.' and then prompt for more information related to their feelings."""

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
    # gent.reset()
    return agent

# print("Agent Setup",agent)