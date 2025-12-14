from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_classic.memory import ConversationBufferMemory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_community.document_loaders import WebBaseLoader
from typing import Literal, Optional, List
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import GithubFileLoader
from sqlalchemy.orm import Session
from datetime import timedelta

import time
import os
import tempfile
import logging
import queue
import threading
from dotenv import load_dotenv

from .database import get_db, Base, engine
from .models import User, Chat, Message
from .auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables (only if database is available)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.warning(f"Could not create database tables. Database may not be available: {e}")
    logger.warning("Server will start but database operations will fail until database is configured.")

# Initialize embedding model (only if API key is available)
embedding_model = None
try:
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    logger.info("Embedding model initialized successfully")
except Exception as e:
    logger.warning(f"Could not initialize embedding model. GOOGLE_API_KEY may not be set: {e}")
    logger.warning("Server will start but RAG operations will fail until API key is configured.")

# Initialize FastAPI app
app = FastAPI(title="RAG ChatBot API", version="2.0.0")

# CORS middleware
# Get allowed origins from environment variable or use defaults
cors_origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://13.49.120.11:3000")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== CONVERSATION MEMORY STORE ==========
# Store ConversationBufferMemory instances per user for normal chats
user_memories: dict[str, ConversationBufferMemory] = {}

SYSTEM_MSG = SystemMessage(content="""
You are an assistant whose top priorities are accuracy, clarity, and user safety. 
Always verify facts before presenting them; when a fact could be time-sensitive or uncertain, explicitly say "I don't know" / "I'm not sure" instead of guessing. 
If the user's question is ambiguous, ask one short clarifying question. 
Cite sources for non-common-knowledge claims. 
If asked for instructions that could be harmful, refuse and provide a safe alternative. 
Keep answers concise, show the final answer first, and then provide a short explanation and sources.
""")

# ========== PYDANTIC MODELS ==========
class UserSignup(BaseModel):
    email: EmailStr
    password: str

class UserSignin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ChatRequest(BaseModel):
    chat_id: int
    message: str
    chat_type: Literal['normal_chat', 'yt_chat', 'pdf_chat', 'web_chat', 'git_chat']
    vector_db_collection_id: Optional[str] = None

class ChatCreate(BaseModel):
    title: str
    type: str  # Frontend format: "Normal", "YouTube", etc.
    vector_db_collection_id: Optional[str] = None

class ChatResponse(BaseModel):
    id: int
    title: str
    type: str
    vector_db_collection_id: Optional[str]
    created_at: str

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str

class RAGRequest(BaseModel):
    url: str

# ========== UTILITY FUNCTIONS ==========
def map_frontend_to_backend_chat_type(frontend_type: str) -> str:
    """Map frontend chat type to backend chat type"""
    mapping = {
        "Normal": "normal_chat",
        "YouTube": "yt_chat",
        "Web": "web_chat",
        "Git": "git_chat",
        "PDF": "pdf_chat"
    }
    return mapping.get(frontend_type, "normal_chat")

def map_backend_to_frontend_chat_type(backend_type: str) -> str:
    """Map backend chat type to frontend chat type"""
    mapping = {
        "normal_chat": "Normal",
        "yt_chat": "YouTube",
        "web_chat": "Web",
        "git_chat": "Git",
        "pdf_chat": "PDF"
    }
    return mapping.get(backend_type, "Normal")

def extract_text_from_content(content):
    """Extract text from various content formats returned by LangChain/Gemini"""
    if content is None:
        return ""
    
    # If it's a string, return it directly
    if isinstance(content, str):
        return content
    
    # If it's a list, process each item
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                # Handle dictionary format like {'type': 'text', 'text': '...', 'index': 0}
                if 'text' in item:
                    texts.append(str(item['text']))
                elif 'content' in item:
                    texts.append(str(item['content']))
                else:
                    # Try to extract any string value
                    for key, value in item.items():
                        if isinstance(value, str) and key not in ['type', 'index', 'extras']:
                            texts.append(value)
            elif isinstance(item, str):
                texts.append(item)
            else:
                texts.append(str(item))
        return "".join(texts)
    
    # If it's a dictionary, extract text field
    if isinstance(content, dict):
        if 'text' in content:
            return str(content['text'])
        elif 'content' in content:
            return str(content['content'])
        else:
            # Try to find any string value
            for key, value in content.items():
                if isinstance(value, str) and key not in ['type', 'index', 'extras']:
                    return value
            # Fallback: convert to string
            return str(content)
    
    # Fallback: convert to string
    return str(content)

def generate_title(user_query: str) -> str:
    """Generate a concise title (max 5 words) based on user query"""
    try:
        logger.info("Generating title for user query")
        mistralai = HuggingFaceEndpoint(
            repo_id="meta-llama/Llama-3.1-8B-Instruct",
            task="conversational",
            temperature=0.3,
            streaming=True,
            huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        )

        model = ChatHuggingFace(llm=mistralai)
        
        title_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Generate a concise title (maximum 5 words) for a chat conversation based on this user query: "{query}"

Title (max 5 words, no quotes, no punctuation at end):"""
        )
        
        chain = title_prompt | model
        response = chain.invoke({"query": user_query})
        title = extract_text_from_content(response.content).strip()
        
        # Clean up title - remove quotes, limit to 5 words
        title = title.strip('"\'')
        words = title.split()[:5]
        title = " ".join(words)
        
        logger.info(f"Generated title: {title}")
        return title if title else "New Chat"
    except Exception as e:
        logger.error(f"Error generating title: {str(e)}", exc_info=True)
        return "New Chat"

def generate_title_parallel(user_query: str, title_queue: queue.Queue):
    """Generate title in parallel thread for RunnableParallel execution"""
    try:
        mistralai = HuggingFaceEndpoint(
    		repo_id="meta-llama/Llama-3.1-8B-Instruct",
    		task="conversational",
    		temperature=0.3,     # same as before
    		streaming=True,
    		huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
	)
        title_model = ChatHuggingFace(llm=mistralai)
        title_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Generate a concise title (maximum 5 words) for a chat conversation based on this user query: "{query}"

Title (max 5 words, no quotes, no punctuation at end):"""
        )
        title_chain = title_prompt | title_model
        
        title_result = title_chain.invoke({"query": user_query})
        title = extract_text_from_content(title_result.content).strip()
        title = title.strip('"\'')
        words = title.split()[:5]
        title = " ".join(words) if words else "New Chat"
        title_queue.put(title)
        logger.info(f"Title generated in parallel: {title}")
    except Exception as e:
        logger.error(f"Error generating title in parallel: {e}")
        title_queue.put("New Chat")

def stream_answer(memory: ConversationBufferMemory):
    """Streams the assistant's reply token by token using ConversationBufferMemory"""
    try:
        logger.info("Initializing ChatGoogleGenerativeAI model")
        mistralai = HuggingFaceEndpoint(
   		repo_id="meta-llama/Llama-3.1-8B-Instruct",
    		task="conversational",
    		temperature=0.3,     # same as before
    		streaming=True,
    		huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
	)
        model = ChatHuggingFace(llm=mistralai)
        logger.info("Starting model stream with ConversationBufferMemory")
        
        # Get the conversation history from memory
        history = memory.chat_memory.messages
        # Ensure system message is at the beginning if not present
        if not history or not isinstance(history[0], SystemMessage):
            history = [SYSTEM_MSG] + history
        
        logger.info(f"History length: {len(history)}")
        stream = model.stream(history)
        full_response = ""
        token_count = 0
        for chunk in stream:
            # Extract text from chunk content
            content = chunk.content if hasattr(chunk, 'content') else chunk
            token = extract_text_from_content(content)
            
            if token:  # Only yield non-empty tokens
                full_response += token
                token_count += 1
                # Yield immediately for real-time streaming
                yield token
                # Small flush to ensure immediate transmission
                import sys
                sys.stdout.flush()
        
        logger.info(f"Model stream completed. Tokens received: {token_count}, Response length: {len(full_response)}")
        
        # Save the AI response to memory using AIMessage
        if full_response:
            memory.chat_memory.add_ai_message(AIMessage(content=full_response))
            logger.info("AI response saved to ConversationBufferMemory")
    except Exception as e:
        logger.error(f"Error in stream_answer: {str(e)}", exc_info=True)
        raise

def get_dynamic_chunk_size(text: str):
    """Dynamically decide chunk_size and chunk_overlap based on document length"""
    length = len(text)
    if length < 1000:
        chunk_size = length/2
        chunk_overlap = 20
    elif length < 5000:
        chunk_size = length/5
        chunk_overlap = 50
    elif length < 20000:
        chunk_size = length/20
        chunk_overlap = 100
    elif length < 100000:
        chunk_size = length/80
        chunk_overlap = 200
    elif length < 300000:
        chunk_size = length/200
        chunk_overlap = 400
    else:
        chunk_size = 6000
        chunk_overlap = 600
    return int(chunk_size), int(chunk_overlap)

def youtube_loader(url: str):
    """Load YouTube transcript"""
    video_id = url.split("v=")[1].split("&")[0]
    ytt_api = YouTubeTranscriptApi()
    transcript_list = ytt_api.fetch(video_id)
    transcript = " ".join(chunk.text for chunk in transcript_list)
    return transcript

def load_pdf(file_path: str):
    """Lazy loads a PDF"""
    loader = PyPDFLoader(file_path)
    return loader.lazy_load()

def github_loader(repo_url, branch="main"):
    """Load GitHub repository files"""
    repo_id = convert_github_url_to_repo_id(repo_url)
    loader = GithubFileLoader(
        repo=repo_id,
        branch=branch,
        file_filter=lambda file_path: file_path.endswith((
            ".txt", ".md", ".html", ".css", ".xml", ".json", ".yaml", ".yml", 
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".kt", ".kts", ".scala", 
            ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".swift", ".m", ".php", 
            ".rb", ".pl", ".pm", ".lua", ".sh", ".bash", ".r", ".jl", ".asm", 
            ".s", ".dart", ".cs", ".ipynb"
    )),
        access_token=os.environ.get("GITHUB_ACCESS_TOKEN"),
    )
    docs = loader.load()
    full_text = ""
    for i, doc in enumerate(docs, start=1):
        file_name = doc.metadata.get("source", f"file_{i}")
        full_text += f"\n\n===== FILE {i}: {file_name} =====\n"
        full_text += doc.page_content
    return full_text

def convert_github_url_to_repo_id(github_url: str) -> str:
    """Converts any GitHub URL into owner/repo format"""
    cleaned = github_url.replace("https://", "").replace("http://", "")
    parts = cleaned.split("/")
    if len(parts) < 3:
        raise ValueError("Invalid GitHub URL format")
    owner = parts[1]
    repo = parts[2]
    return f"{owner}/{repo}"

def web_loader(url: str):
    """Loads webpage and returns text as string"""
    loader = WebBaseLoader(url)
    docs = loader.load()
    if not docs:
        return ""
    return "\n\n".join([d.page_content for d in docs])

def split_text(text: str, chunk_size=None, chunk_overlap=None):
    """Split raw text into smaller chunks"""
    if chunk_size is None or chunk_overlap is None:
        chunk_size, chunk_overlap = get_dynamic_chunk_size(text)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = splitter.split_text(text)
    return chunks

def create_vector_store(chunks, collection_name: str, persist_dir: str):
    """Create a Chroma vector store from chunks"""
    docs = [Document(page_content=chunk) for chunk in chunks]
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=persist_dir
    )
    vector_store.add_documents(docs)
    vector_store.persist()
    return vector_store

def load_vector_store(collection_name: str, persist_dir: str):
    """Load an existing Chroma vector store"""
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embedding_model,
        persist_directory=persist_dir
    )
    return vector_store

def get_rag_prompt():
    """Get RAG prompt template"""
    prompt = PromptTemplate.from_template(
        """
    You are an advanced Retrieval-Augmented Generation (RAG) AI assistant.
    Your job is to generate answers that are:

    - **Fully grounded in the provided context**
    - **Factual and concise unless user requests more detail**
    - **Explanatory enough that a beginner can understand**
    - **Non-hallucinatory: never invent facts not found in the context**
    - **Helpful and structured**
    - **Adaptive in length:**
        - If the user specifies a length → follow it.
        - If not, give a detailed but concise explanation.

    =========================
    STRICT RULES:
    =========================

    1️⃣ **Grounded Answers Only**  
    Use ONLY the provided context to answer.  
    If the context does NOT contain enough information, say:

    "I don't have enough information to answer that from the provided data."

    Do NOT guess. Do NOT create facts.

    2️⃣ **Use Context Examples if Available**  
    If the context includes examples:  
    → Explain them clearly and deeply.

    3️⃣ **If No Examples Are Provided**  
    Generate **relevant, realistic, real-life** examples that match the topic.

    4️⃣ **Explain Step-by-Step When Needed**  
    If the question requires reasoning or understanding, use clear steps or bullet points.

    5️⃣ **No unnecessary repetition**  
    Do not repeat entire context or question.  
    Summaries must be natural and focused.

    =========================
    CONTEXT:
    {context}
    =========================

    QUESTION:
    {question}

    --------------------------
    Now produce the BEST POSSIBLE grounded answer.
    """
    )
    return prompt


# ========== AUTHENTICATION ENDPOINTS ==========
@app.post("/auth/signup", response_model=Token)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """User registration"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        new_user = User(email=user_data.email, password_hash=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(new_user.id)}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@app.post("/auth/signin", response_model=Token)
def signin(user_data: UserSignin, db: Session = Depends(get_db)):
    """User login"""
    try:
        user = db.query(User).filter(User.email == user_data.email).first()
        if not user or not verify_password(user_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to authenticate: {str(e)}"
        )

@app.get("/auth/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    try:
        return {
            "id": current_user.id,
            "email": current_user.email
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )

# ========== CHAT MANAGEMENT ENDPOINTS ==========
@app.get("/chats", response_model=List[ChatResponse])
def get_chats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all chats for current user"""
    try:
        chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.created_at.desc()).all()
        return [
            ChatResponse(
                id=chat.id,
                title=chat.title,
                type=map_backend_to_frontend_chat_type(chat.type),
                vector_db_collection_id=chat.vector_db_collection_id,
                created_at=chat.created_at.isoformat()
            )
            for chat in chats
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get chats: {str(e)}"
        )

@app.post("/chats", response_model=ChatResponse)
def create_chat(chat_data: ChatCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new chat"""
    try:
        backend_type = map_frontend_to_backend_chat_type(chat_data.type)
        new_chat = Chat(
            user_id=current_user.id,
            title=chat_data.title,
            type=backend_type,
            vector_db_collection_id=chat_data.vector_db_collection_id
        )
        db.add(new_chat)
        db.commit()
        db.refresh(new_chat)
        
        return ChatResponse(
            id=new_chat.id,
            title=new_chat.title,
            type=map_backend_to_frontend_chat_type(new_chat.type),
            vector_db_collection_id=new_chat.vector_db_collection_id,
            created_at=new_chat.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}"
        )

@app.get("/chats/{chat_id}/messages", response_model=List[MessageResponse])
def get_chat_messages(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get messages for a specific chat"""
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
        return [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at.isoformat()
            )
            for msg in messages
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get messages: {str(e)}"
        )

@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete a chat"""
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == current_user.id).first()
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
        
        db.delete(chat)
        db.commit()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}"
        )

# ========== CHAT STREAMING ENDPOINT ==========
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Streaming chat endpoint"""
    logger.info(f"Received chat stream request: chat_id={request.chat_id}, chat_type={request.chat_type}, user_id={current_user.id}")
    try:
        # Verify chat belongs to user
        chat = db.query(Chat).filter(Chat.id == request.chat_id, Chat.user_id == current_user.id).first()
        if not chat:
            logger.warning(f"Chat not found: chat_id={request.chat_id}, user_id={current_user.id}")
            raise HTTPException(status_code=404, detail="Chat not found")
        
        logger.info(f"Chat found: {chat.title}")
        
        # Check if this is the first message in the chat (before saving user message)
        existing_messages = db.query(Message).filter(Message.chat_id == request.chat_id).count()
        is_first_message = existing_messages == 0
        logger.info(f"Is first message: {is_first_message}, existing messages: {existing_messages}")
        
        # Save user message (if database is available)
        try:
            user_message = Message(chat_id=request.chat_id, role="user", content=request.message)
            db.add(user_message)
            db.commit()
            logger.info(f"User message saved: {request.message[:50]}...")
        except Exception as e:
            db.rollback()
            logger.warning(f"Could not save user message to database: {e}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat request: {str(e)}"
        )
    
    if request.chat_type == "normal_chat":
        # Memory-based chat using ConversationBufferMemory
        logger.info("Processing normal_chat request with ConversationBufferMemory")
        user_id_str = str(current_user.id)
        
        # is_first_message is already determined above before saving user message
        
        # Get or create ConversationBufferMemory for this user
        if user_id_str not in user_memories:
            user_memories[user_id_str] = ConversationBufferMemory(
                return_messages=True,
                memory_key="chat_memory"
            )
            # Add system message to memory as SystemMessage
            user_memories[user_id_str].chat_memory.add_message(SYSTEM_MSG)
            logger.info(f"Initialized ConversationBufferMemory for user: {user_id_str}")

        memory = user_memories[user_id_str]
        
        # Add user message to memory using HumanMessage
        memory.chat_memory.add_user_message(HumanMessage(content=request.message))
        logger.info(f"Added user message to memory. Total messages: {len(memory.chat_memory.messages)}")

        def generate():
            full_response = ""
            generated_title = None
            
            try:
                if is_first_message:
                    # Use RunnableParallel for first message: generate response and title in parallel
                    logger.info("First message detected - using RunnableParallel for response and title generation")
                    
                    # Queue to store title result
                    title_queue = queue.Queue()
                    
                    # Start title generation in background thread using module-level function
                    title_thread = threading.Thread(target=generate_title_parallel, args=(request.message, title_queue))
                    title_thread.start()
                    
                    # Stream response while title is being generated in parallel
                    logger.info("Starting stream_answer generator with ConversationBufferMemory")
                    token_count = 0
                    for token in stream_answer(memory):
                        if token:
                            full_response += token
                            token_count += 1
                            yield token
                    
                    # Wait for title generation to complete (with timeout)
                    title_thread.join(timeout=10)
                    if not title_queue.empty():
                        generated_title = title_queue.get()
                    else:
                        # Fallback if title generation failed or timed out
                        generated_title = generate_title(request.message)
                        logger.warning("Title generation timed out or failed, using fallback")
                    
                    logger.info(f"Generated title: {generated_title}")
                    
                    # Send title update immediately after streaming completes (before saving message)
                    if generated_title:
                        try:
                            # Refresh chat object to ensure we have the latest data
                            db.refresh(chat)
                            chat.title = generated_title
                            db.commit()
                            logger.info(f"Chat title updated to: {generated_title}")
                            # Send title update as special marker (frontend will parse this)
                            title_marker = f"<!-- TITLE_UPDATE:{generated_title} -->"
                            yield title_marker
                            logger.info(f"Title update marker sent: {title_marker}")
                        except Exception as e:
                            db.rollback()
                            logger.warning(f"Could not update chat title: {e}")
                else:
                    # Regular streaming for subsequent messages
                    logger.info("Starting stream_answer generator with ConversationBufferMemory")
                    token_count = 0
                    for token in stream_answer(memory):
                        if token:
                            full_response += token
                            token_count += 1
                            yield token
                
                logger.info(f"Stream completed. Response length: {len(full_response)}")
                
                # Save assistant message to database
                try:
                    assistant_message = Message(chat_id=request.chat_id, role="assistant", content=full_response)
                    db.add(assistant_message)
                    db.commit()
                    logger.info("Assistant message saved to database")
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Could not save assistant message to database: {e}")
            except Exception as e:
                logger.error(f"Error in stream generator: {str(e)}", exc_info=True)
                error_msg = f"\n\nError: {str(e)}"
                yield error_msg
                # Try to save error message
                try:
                    assistant_message = Message(chat_id=request.chat_id, role="assistant", content=error_msg)
                    db.add(assistant_message)
                    db.commit()
                except:
                    db.rollback()
        
        return StreamingResponse(
            generate(), 
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
    
    elif request.chat_type in ["yt_chat", "pdf_chat", "web_chat", "git_chat"]:
        # RAG-based chat
        logger.info(f"Processing RAG chat: type={request.chat_type}, collection={request.vector_db_collection_id}")
        if not request.vector_db_collection_id:
            logger.warning("vector_db_collection_id required for RAG chats")
            raise HTTPException(status_code=400, detail="vector_db_collection_id required for RAG chats")
        
        # Check if this is the first message in the chat (same check as normal_chat)
        # is_first_message is already determined above before saving user message
        
        current_dir = os.getcwd()
        try:
            logger.info(f"Loading vector store: {request.vector_db_collection_id}")
            vector_store = load_vector_store(
                collection_name=request.vector_db_collection_id,
                persist_dir=current_dir
            )
            logger.info("Vector store loaded successfully")
        except Exception as e:
            logger.error(f"Vector store not found: {e}", exc_info=True)
            raise HTTPException(status_code=404, detail=f"Vector store not found: {e}")

        logger.info("Creating retriever and retrieving context")
        retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 5})
        context_docs = retriever.invoke(request.message)
        context_text = "\n".join(doc.page_content for doc in context_docs)
        logger.info(f"Retrieved {len(context_docs)} context documents, total length: {len(context_text)}")

        rag_prompt = get_rag_prompt()
        logger.info("Initializing ChatGoogleGenerativeAI for RAG")
        mistralai = HuggingFaceEndpoint(
    		repo_id="meta-llama/Llama-3.1-8B-Instruct",
    		task="conversational",
    		temperature=0.3,     # same as before
    		streaming=True,
    		huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
	)
        llm = ChatHuggingFace(llm=mistralai)
        
        chain = rag_prompt | llm
        prompt_input = {'context': context_text, 'question': request.message}
        
        def generate():
            full_response = ""
            generated_title = None
            
            try:
                if is_first_message:
                    # Use RunnableParallel for first message: generate response and title in parallel
                    logger.info("First message detected in RAG chat - using RunnableParallel for response and title generation")
                    
                    import threading
                    import queue
                    
                    # Queue to store title result
                    title_queue = queue.Queue()
                    
                    # Start title generation in background thread
                    title_thread = threading.Thread(target=generate_title_parallel, args=(request.message, title_queue))
                    title_thread.start()
                    
                    # Stream RAG response while title is being generated in parallel
                    logger.info("Starting RAG chain stream with parallel title generation")
                    token_count = 0
                    for token in chain.stream(prompt_input):
                        # Extract text from token content
                        content = token.content if hasattr(token, 'content') else token
                        token_content = extract_text_from_content(content)
                        
                        if token_content:
                            full_response += token_content
                            token_count += 1
                            yield token_content
                    
                    # Wait for title generation to complete (with timeout)
                    title_thread.join(timeout=10)
                    if not title_queue.empty():
                        generated_title = title_queue.get()
                    else:
                        # Fallback if title generation failed or timed out
                        generated_title = generate_title(request.message)
                        logger.warning("Title generation timed out or failed, using fallback")
                    
                    logger.info(f"Generated title for RAG chat: {generated_title}")
                    
                    # Send title update immediately after streaming completes (before saving message)
                    if generated_title:
                        try:
                            # Refresh chat object to ensure we have the latest data
                            db.refresh(chat)
                            chat.title = generated_title
                            db.commit()
                            logger.info(f"RAG chat title updated to: {generated_title}")
                            # Send title update as special marker (frontend will parse this)
                            title_marker = f"<!-- TITLE_UPDATE:{generated_title} -->"
                            yield title_marker
                            logger.info(f"Title update marker sent for RAG chat: {title_marker}")
                        except Exception as e:
                            db.rollback()
                            logger.warning(f"Could not update RAG chat title: {e}")
                else:
                    # Regular streaming for subsequent messages
                    logger.info("Starting RAG chain stream")
                    token_count = 0
                    for token in chain.stream(prompt_input):
                        # Extract text from token content
                        content = token.content if hasattr(token, 'content') else token
                        token_content = extract_text_from_content(content)
                        
                        if token_content:
                            full_response += token_content
                            token_count += 1
                            yield token_content
                
                logger.info(f"RAG stream completed. Response length: {len(full_response)}")
                
                # Save assistant message (if database is available)
                try:
                    assistant_message = Message(chat_id=request.chat_id, role="assistant", content=full_response)
                    db.add(assistant_message)
                    db.commit()
                    logger.info("RAG assistant message saved to database")
                except Exception as e:
                    db.rollback()
                    logger.warning(f"Could not save assistant message to database: {e}")
            except Exception as e:
                logger.error(f"Error in RAG stream generator: {str(e)}", exc_info=True)
                error_msg = f"\n\nError: {str(e)}"
                yield error_msg
                # Try to save error message
                try:
                    assistant_message = Message(chat_id=request.chat_id, role="assistant", content=error_msg)
                    db.add(assistant_message)
                    db.commit()
                except:
                    db.rollback()
        
        return StreamingResponse(
            generate(), 
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid chat_type")

# ========== RAG ENDPOINTS ==========
@app.post("/yt_rag")
def create_youtube_rag(request: RAGRequest, current_user: User = Depends(get_current_user)):
    """Create RAG vector store from YouTube video"""
    try:
        logger.info(f"Creating YouTube RAG for user {current_user.id}, URL: {request.url}")
        transcript = youtube_loader(request.url)
        if not transcript or transcript.strip() == "":
            logger.warning(f"Empty transcript extracted from YouTube URL: {request.url}")
            raise HTTPException(status_code=400, detail="Could not extract transcript from YouTube video. Please check if the video has captions enabled.")
        
        chunk_size, chunk_overlap = get_dynamic_chunk_size(transcript)
        split_documents = split_text(transcript, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        current_millis = int(time.time() * 1000)
        collection_name = f"{current_user.id}_{current_millis}"
        current_dir = os.getcwd()
        create_vector_store(split_documents, collection_name=collection_name, persist_dir=current_dir)
        logger.info(f"Successfully created YouTube RAG collection: {collection_name}")
        return {"collection_name": collection_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating YouTube RAG: {str(e)}", exc_info=True)
        error_message = str(e)
        if "transcript" in error_message.lower() or "caption" in error_message.lower():
            raise HTTPException(status_code=400, detail="Could not extract transcript from YouTube video. Please ensure the video has captions enabled.")
        raise HTTPException(status_code=500, detail=f"Failed to process YouTube video: {error_message}")

@app.post("/git_rag")
def create_github_rag(request: RAGRequest, current_user: User = Depends(get_current_user)):
    """Create RAG vector store from GitHub repository"""
    try:
        logger.info(f"Creating Git RAG for user {current_user.id}, URL: {request.url}")
        file_list = github_loader(request.url)
        if not file_list or len(file_list) == 0:
            logger.warning(f"No files found in Git repository: {request.url}")
            raise HTTPException(status_code=400, detail="Could not access Git repository or repository is empty. Please check the URL and ensure the repository is public or accessible.")
        
        chunk_size, chunk_overlap = get_dynamic_chunk_size(file_list)
        split_documents = split_text(file_list, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        current_millis = int(time.time() * 1000)
        collection_name = f"{current_user.id}_{current_millis}"
        current_dir = os.getcwd()
        create_vector_store(split_documents, collection_name=collection_name, persist_dir=current_dir)
        logger.info(f"Successfully created Git RAG collection: {collection_name}")
        return {"collection_name": collection_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Git RAG: {str(e)}", exc_info=True)
        error_message = str(e)
        if "not found" in error_message.lower() or "404" in error_message.lower():
            raise HTTPException(status_code=404, detail="Git repository not found. Please check the URL and ensure the repository exists and is accessible.")
        if "private" in error_message.lower() or "access" in error_message.lower():
            raise HTTPException(status_code=403, detail="Cannot access private repository. Please ensure the repository is public or provide proper authentication.")
        raise HTTPException(status_code=500, detail=f"Failed to process Git repository: {error_message}")

@app.post("/pdf_rag")
async def create_pdf_rag(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Create RAG vector store from PDF file"""
    temp_path = None
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_path = tmp_file.name

        pdf_docs = list(load_pdf(temp_path))
        if not pdf_docs:
            raise HTTPException(status_code=400, detail="Could not load or parse PDF")

        full_text = "\n".join([doc.page_content for doc in pdf_docs])
        chunk_size, chunk_overlap = get_dynamic_chunk_size(full_text)
        split_documents = split_text(
            full_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        current_millis = int(time.time() * 1000)
        collection_name = f"{current_user.id}_{current_millis}"
        current_dir = os.getcwd()
        create_vector_store(split_documents, collection_name=collection_name, persist_dir=current_dir)

        return {"collection_name": collection_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

@app.post("/web_rag")
def create_web_rag(request: RAGRequest, current_user: User = Depends(get_current_user)):
    """Create RAG vector store from webpage"""
    try:
        logger.info(f"Creating Web RAG for user {current_user.id}, URL: {request.url}")
        webpage_text = web_loader(request.url)
        if not webpage_text or webpage_text.strip() == "":
            logger.warning(f"Empty content extracted from webpage: {request.url}")
            raise HTTPException(status_code=400, detail="Could not extract text from webpage. The page may be empty, require JavaScript, or be inaccessible.")

        chunk_size, chunk_overlap = get_dynamic_chunk_size(webpage_text)
        split_documents = split_text(
            webpage_text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        current_millis = int(time.time() * 1000)
        collection_name = f"{current_user.id}_{current_millis}"
        current_dir = os.getcwd()
        create_vector_store(split_documents, collection_name=collection_name, persist_dir=current_dir)
        logger.info(f"Successfully created Web RAG collection: {collection_name}")
        return {"collection_name": collection_name}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Web RAG: {str(e)}", exc_info=True)
        error_message = str(e)
        if "not found" in error_message.lower() or "404" in error_message.lower():
            raise HTTPException(status_code=404, detail="Webpage not found. Please check the URL and ensure it's accessible.")
        if "timeout" in error_message.lower() or "connection" in error_message.lower():
            raise HTTPException(status_code=408, detail="Connection timeout. The webpage may be slow or inaccessible.")
        raise HTTPException(status_code=500, detail=f"Failed to process webpage: {error_message}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ========== HOME ROUTE ==========
@app.get("/")
def home():
    return {
        "message": "Welcome to the Streaming ChatBot API!",
        "version": "2.0.0"
    }
