# Tutorial Implementasi Agentic RAG dengan LangGraph

## Daftar Isi
1. [Pendahuluan](#pendahuluan)
2. [Setup dan Instalasi](#setup-dan-instalasi)
3. [Preprocessing Dokumen](#preprocessing-dokumen)
4. [Membuat Retriever Tool](#membuat-retriever-tool)
5. [Node Generate Query](#node-generate-query)
6. [Node Grade Documents](#node-grade-documents)
7. [Node Rewrite Question](#node-rewrite-question)
8. [Node Generate Answer](#node-generate-answer)
9. [Merakit Graph](#merakit-graph)
10. [Menjalankan Agentic RAG](#menjalankan-agentic-rag)

## Pendahuluan

**Agentic RAG** adalah sistem Retrieval-Augmented Generation yang menggunakan agent untuk membuat keputusan cerdas tentang:
- Kapan menggunakan retrieval dari vectorstore
- Kapan merespons langsung kepada user
- Bagaimana mengevaluasi relevansi dokumen
- Kapan perlu menulis ulang pertanyaan

Sistem ini menggunakan **LangGraph** untuk mengatur workflow dengan node dan edge yang menentukan alur eksekusi berdasarkan kondisi tertentu.

## Setup dan Instalasi

### 1. Install Dependencies

```bash
pip install -U langgraph "langchain[openai]" langchain-community langchain-text-splitters
```

### 2. Setup API Keys

```python
import getpass
import os

def _set_env(key: str):
    if key not in os.environ:
        os.environ[key] = getpass.getpass(f"{key}:")

_set_env("OPENAI_API_KEY")
```

## Preprocessing Dokumen

### 1. Fetch Dokumen dari Web

```python
from langchain_community.document_loaders import WebBaseLoader

# URLs yang akan digunakan sebagai knowledge base
urls = [
    "https://lilianweng.github.io/posts/2024-11-28-reward-hacking/",
    "https://lilianweng.github.io/posts/2024-07-07-hallucination/",
    "https://lilianweng.github.io/posts/2024-04-12-diffusion-video/",
]

# Load dokumen dari URLs
docs = [WebBaseLoader(url).load() for url in urls]
```

### 2. Split Dokumen menjadi Chunks

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Flatten list dokumen
docs_list = [item for sublist in docs for item in sublist]

# Split dengan RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size=100, 
    chunk_overlap=50
)
doc_splits = text_splitter.split_documents(docs_list)
```

## Membuat Retriever Tool

### 1. Buat Vector Store dan Retriever

```python
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

# Buat vector store dengan OpenAI embeddings
vectorstore = InMemoryVectorStore.from_documents(
    documents=doc_splits, 
    embedding=OpenAIEmbeddings()
)
retriever = vectorstore.as_retriever()
```

### 2. Buat Retriever Tool

```python
from langchain.tools.retriever import create_retriever_tool

retriever_tool = create_retriever_tool(
    retriever,
    "retrieve_blog_posts",
    "Search and return information about Lilian Weng blog posts.",
)
```

### 3. Test Retriever Tool

```python
# Test tool dengan query
result = retriever_tool.invoke({"query": "types of reward hacking"})
print(result)
```

## Node Generate Query

Node ini adalah entry point yang memutuskan apakah perlu melakukan retrieval atau merespons langsung.

```python
from langgraph.graph import MessagesState
from langchain.chat_models import init_chat_model

# Initialize model dengan tools
response_model = init_chat_model("openai:gpt-4.1", temperature=0)

def generate_query_or_respond(state: MessagesState):
    """
    Call model untuk generate response berdasarkan state saat ini.
    Memutuskan apakah perlu retrieve menggunakan retriever tool,
    atau merespons langsung kepada user.
    """
    response = (
        response_model
        .bind_tools([retriever_tool])
        .invoke(state["messages"])
    )
    
    return {"messages": [response]}
```

### Test Node

```python
# Test dengan input sederhana
input = {"messages": [{"role": "user", "content": "hello!"}]}
result = generate_query_or_respond(input)["messages"][-1]
print(result.pretty_print())

# Test dengan pertanyaan yang memerlukan retrieval
input = {
    "messages": [{
        "role": "user",
        "content": "What does Lilian Weng say about types of reward hacking?"
    }]
}
result = generate_query_or_respond(input)["messages"][-1]
print(result.pretty_print())
```

## Node Grade Documents

Node ini mengevaluasi apakah dokumen yang di-retrieve relevan dengan pertanyaan user.

```python
from pydantic import BaseModel, Field
from typing import Literal

# Prompt untuk grading
GRADE_PROMPT = (
    "You are a grader assessing relevance of a retrieved document to a user question. \n "
    "Here is the retrieved document: \n\n {context} \n\n"
    "Here is the user question: {question} \n"
    "If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n"
    "Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."
)

class GradeDocuments(BaseModel):
    """Grade documents using binary score for relevance check."""
    
    binary_score: str = Field(
        description="Relevance score: 'yes' if relevant, or 'no' if not relevant"
    )

grader_model = init_chat_model("openai:gpt-4.1", temperature=0)

def grade_documents(
    state: MessagesState,
) -> Literal["generate_answer", "rewrite_question"]:
    """
    Menentukan apakah retrieved documents relevan dengan pertanyaan.
    Return: 'generate_answer' jika relevan, 'rewrite_question' jika tidak.
    """
    question = state["messages"][0].content
    context = state["messages"][-1].content
    
    prompt = GRADE_PROMPT.format(question=question, context=context)
    response = (
        grader_model
        .with_structured_output(GradeDocuments)
        .invoke([{"role": "user", "content": prompt}])
    )
    
    score = response.binary_score
    
    if score == "yes":
        return "generate_answer"
    else:
        return "rewrite_question"
```

### Test Grade Documents

```python
from langchain_core.messages import convert_to_messages

# Test dengan dokumen tidak relevan
input = {
    "messages": convert_to_messages([
        {
            "role": "user",
            "content": "What does Lilian Weng say about types of reward hacking?",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "1",
                "name": "retrieve_blog_posts",
                "args": {"query": "types of reward hacking"},
            }],
        },
        {"role": "tool", "content": "meow", "tool_call_id": "1"},
    ])
}

result = grade_documents(input)
print(result)  # Output: 'rewrite_question'

# Test dengan dokumen relevan
input["messages"][-1]["content"] = "reward hacking can be categorized into two types: environment or goal misspecification, and reward tampering"
result = grade_documents(input)
print(result)  # Output: 'generate_answer'
```

## Node Rewrite Question

Node ini menulis ulang pertanyaan user jika dokumen yang di-retrieve tidak relevan.

```python
REWRITE_PROMPT = (
    "Look at the input and try to reason about the underlying semantic intent / meaning.\n"
    "Here is the initial question:"
    "\n ------- \n"
    "{question}"
    "\n ------- \n"
    "Formulate an improved question:"
)

def rewrite_question(state: MessagesState):
    """Rewrite pertanyaan user yang asli untuk meningkatkan hasil retrieval."""
    messages = state["messages"]
    question = messages[0].content
    
    prompt = REWRITE_PROMPT.format(question=question)
    response = response_model.invoke([{"role": "user", "content": prompt}])
    
    return {"messages": [{"role": "user", "content": response.content}]}
```

### Test Rewrite Question

```python
input = {
    "messages": convert_to_messages([
        {
            "role": "user",
            "content": "What does Lilian Weng say about types of reward hacking?",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "1",
                "name": "retrieve_blog_posts",
                "args": {"query": "types of reward hacking"},
            }],
        },
        {"role": "tool", "content": "meow", "tool_call_id": "1"},
    ])
}

response = rewrite_question(input)
print(response["messages"][-1]["content"])
# Output: "What are the different types of reward hacking described by Lilian Weng, and how does she explain them?"
```

## Node Generate Answer

Node ini menghasilkan jawaban final berdasarkan pertanyaan dan konteks yang relevan.

```python
GENERATE_PROMPT = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer the question. "
    "If you don't know the answer, just say that you don't know. "
    "Use three sentences maximum and keep the answer concise.\n"
    "Question: {question} \n"
    "Context: {context}"
)

def generate_answer(state: MessagesState):
    """Generate jawaban final berdasarkan konteks yang relevan."""
    question = state["messages"][0].content
    context = state["messages"][-1].content
    
    prompt = GENERATE_PROMPT.format(question=question, context=context)
    response = response_model.invoke([{"role": "user", "content": prompt}])
    
    return {"messages": [response]}
```

### Test Generate Answer

```python
input = {
    "messages": convert_to_messages([
        {
            "role": "user",
            "content": "What does Lilian Weng say about types of reward hacking?",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "1",
                "name": "retrieve_blog_posts",
                "args": {"query": "types of reward hacking"},
            }],
        },
        {
            "role": "tool",
            "content": "reward hacking can be categorized into two types: environment or goal misspecification, and reward tampering",
            "tool_call_id": "1",
        },
    ])
}

response = generate_answer(input)
response["messages"][-1].pretty_print()
```

## Merakit Graph

Sekarang kita merakit semua node menjadi sebuah graph dengan LangGraph.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

# Initialize StateGraph
workflow = StateGraph(MessagesState)

# Tambahkan semua node
workflow.add_node(generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node(rewrite_question)
workflow.add_node(generate_answer)

# Set starting point
workflow.add_edge(START, "generate_query_or_respond")

# Conditional edge: apakah perlu retrieve?
workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,
    {
        "tools": "retrieve",  # Jika ada tool_calls, pergi ke retrieve
        END: END,             # Jika tidak ada tool_calls, selesai
    },
)

# Conditional edge: apakah dokumen relevan?
workflow.add_conditional_edges(
    "retrieve",
    grade_documents,
    # grade_documents akan return "generate_answer" atau "rewrite_question"
)

# Edge dari generate_answer ke END
workflow.add_edge("generate_answer", END)

# Edge dari rewrite_question kembali ke generate_query_or_respond
workflow.add_edge("rewrite_question", "generate_query_or_respond")

# Compile graph
graph = workflow.compile()
```

### Visualisasi Graph

```python
from IPython.display import Image, display

# Visualisasi graph (jika menggunakan Jupyter)
display(Image(graph.get_graph().draw_mermaid_png()))
```

## Menjalankan Agentic RAG

### Contoh Penggunaan

```python
# Stream execution untuk melihat setiap step
for chunk in graph.stream(
    {
        "messages": [
            {
                "role": "user",
                "content": "What does Lilian Weng say about types of reward hacking?",
            }
        ]
    }
):
    for node, update in chunk.items():
        print(f"Update from node: {node}")
        update["messages"][-1].pretty_print()
        print("\n" + "="*50 + "\n")
```

### Output yang Diharapkan

```
Update from node: generate_query_or_respond
================================== Ai Message ==================================
Tool Calls:
  retrieve_blog_posts (call_NYu2vq4km9nNNEFqJwefWKu1)
  Call ID: call_NYu2vq4km9nNNEFqJwefWKu1
  Args:
    query: types of reward hacking

==================================================

Update from node: retrieve
================================= Tool Message ==================================
Name: retrieve_blog_posts

At a high level, reward hacking can be categorized into two types: environment or goal misspecification, and reward tampering.
...

==================================================

Update from node: generate_answer
================================== Ai Message ==================================

Lilian Weng categorizes reward hacking into two types: environment or goal misspecification, and reward tampering. She considers reward hacking as a broad concept that includes both of these categories. Reward hacking occurs when an agent exploits flaws or ambiguities in the reward function to achieve high rewards without performing the intended behaviors.

==================================================
```

## Arsitektur dan Alur Kerja

### Flow Diagram
```
START → generate_query_or_respond 
           ↓ (has tool_calls)     ↓ (no tool_calls)
         retrieve                 END
           ↓
       grade_documents
    ↓ (not relevant)    ↓ (relevant)
  rewrite_question    generate_answer
      ↓                   ↓
  generate_query_or_respond → END
```

### Penjelasan Alur:

1. **START**: User mengirim pertanyaan
2. **generate_query_or_respond**: Model memutuskan apakah perlu retrieval atau langsung menjawab
3. **retrieve**: Jika perlu, lakukan semantic search di vectorstore
4. **grade_documents**: Evaluasi relevansi dokumen yang ditemukan
5. **generate_answer**: Jika relevan, buat jawaban final
6. **rewrite_question**: Jika tidak relevan, tulis ulang pertanyaan dan kembali ke step 2
7. **END**: Selesai

## Keunggulan Agentic RAG

### 1. **Adaptive Decision Making**
- Tidak selalu melakukan retrieval untuk setiap pertanyaan
- Model bisa menjawab langsung untuk pertanyaan sederhana

### 2. **Quality Control**
- Evaluasi relevansi dokumen sebelum menggunakan untuk generate jawaban
- Automatic query improvement jika retrieval gagal

### 3. **Scalable Architecture**
- Mudah menambah node baru untuk functionality tambahan
- Conditional routing yang fleksibel

### 4. **Observability**
- Dapat melacak setiap step dalam workflow
- Debugging yang mudah dengan stream execution

## Customization dan Extension

### 1. **Custom Grading Logic**
```python
def custom_grade_documents(state: MessagesState) -> Literal["generate_answer", "rewrite_question", "retrieve_more"]:
    # Custom logic untuk grading yang lebih kompleks
    # Bisa menambah route "retrieve_more" untuk re-retrieval
    pass
```

### 2. **Multiple Retrievers**
```python
# Tambahkan retriever untuk domain berbeda
academic_retriever = create_retriever_tool(academic_vectorstore, "academic_search", "Search academic papers")
web_retriever = create_retriever_tool(web_vectorstore, "web_search", "Search web content")

# Bind multiple tools
response_model.bind_tools([academic_retriever, web_retriever])
```

### 3. **Advanced Query Processing**
```python
def query_analyzer(state: MessagesState):
    """Analyze query type dan route ke retriever yang sesuai"""
    # Implementation untuk query classification
    pass
```

## Best Practices

### 1. **Chunking Strategy**
- Eksperimen dengan `chunk_size` dan `chunk_overlap`
- Pertimbangkan semantic chunking untuk dokumen yang kompleks

### 2. **Prompt Engineering**
- Tuning prompt untuk grading agar lebih akurat
- Contextual prompt berdasarkan domain knowledge

### 3. **Monitoring**
- Track metrics: retrieval accuracy, response quality, user satisfaction
- A/B testing untuk different configurations

### 4. **Error Handling**
```python
def safe_generate_answer(state: MessagesState):
    try:
        return generate_answer(state)
    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Sorry, I encountered an error: {str(e)}"}]}
```

## Troubleshooting

### 1. **Low Retrieval Quality**
- Periksa embedding model compatibility
- Adjust chunk size dan overlap
- Improve document preprocessing

### 2. **Infinite Rewrite Loop**
- Set maximum rewrite attempts
- Improve rewrite prompt quality
- Add fallback mechanism

### 3. **Slow Response Time**
- Optimize vectorstore (use Pinecone/Weaviate untuk production)
- Cache common queries
- Parallel processing untuk multiple retrievers

## Kesimpulan

Agentic RAG dengan LangGraph memberikan framework yang powerful dan fleksibel untuk building intelligent retrieval systems. Dengan kombinasi decision-making, quality control, dan adaptive behavior, sistem ini dapat memberikan user experience yang superior dibanding traditional RAG implementations.

Key advantages:
- **Intelligent routing** berdasarkan query type
- **Quality assurance** dengan document grading
- **Self-improvement** melalui query rewriting
- **Scalable architecture** untuk enterprise applications

Sistem ini ideal untuk use cases yang membutuhkan high-quality, contextual responses dengan ability untuk adapt terhadap different types of user queries.